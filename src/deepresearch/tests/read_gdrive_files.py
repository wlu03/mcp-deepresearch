import asyncio
import os
import sys
import logging
from pathlib import Path
import aiohttp
import json
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gdrive_reader")

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from deepresearch.connectors import GoogleDriveConnector
from deepresearch.connectors.drive import SCOPES

# Create downloads directory
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Path to credentials file
CREDENTIALS_FILE = os.path.join("credentials", "client_secret_395039126310-8ovj91u9ef31o0pehta2n957bjqtaimp.apps.googleusercontent.com.json")
ROOT_CREDENTIALS_FILE = os.path.join("..", CREDENTIALS_FILE)

# Modify the SCOPES to see all files
# This requires a new token, so we'll delete the existing one if it exists
TOKEN_FILE = 'deepresearch_token.json'
if os.path.exists(TOKEN_FILE):
    logger.info(f"Removing existing token file to get broader access")
    os.remove(TOKEN_FILE)

async def list_and_read_files():
    """List files from Google Drive and allow the user to download them"""
    logger.info("=== Google Drive File Reader ===")
    
    # Copy credentials file to the expected location
    if os.path.exists(ROOT_CREDENTIALS_FILE):
        logger.info("Using credentials from root directory")
        # Copy to current working directory
        shutil.copy(ROOT_CREDENTIALS_FILE, "deepresearch_credentials.json")
    elif os.path.exists(CREDENTIALS_FILE):
        logger.info("Using credentials from credentials directory")
        shutil.copy(CREDENTIALS_FILE, "deepresearch_credentials.json")
    else:
        logger.error(f"Credentials file not found at {CREDENTIALS_FILE} or {ROOT_CREDENTIALS_FILE}")
        return
    
    async with aiohttp.ClientSession() as session:
        # Initialize connector
        connector = GoogleDriveConnector(session)
        
        # Patch the connector's SCOPES to allow reading all files
        # This is a hacky way to modify the connector's behavior
        import deepresearch.connectors.drive
        deepresearch.connectors.drive.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        
        # Authenticate
        logger.info("Authenticating with Google Drive (read-only access)...")
        auth_success = await connector.authenticate()
        
        if not auth_success:
            logger.error("Authentication failed")
            return
            
        logger.info("Authentication successful")
        
        # Use the direct drive API to list files since our connector might be limited
        await list_all_files_direct(connector)
            
async def list_all_files_direct(connector):
    """List all files using direct Drive API access"""
    logger.info("\nListing all files from Google Drive...")
    
    try:
        # Make sure we're authenticated
        await connector.ensure_authenticated()
        
        # Use the Drive API directly
        loop = asyncio.get_running_loop()
        
        # Make the list query with no folder restriction
        response = await loop.run_in_executor(
            None,
            lambda: connector._drive_service.files().list(
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, createdTime, webViewLink)",
                q="trashed = false"
            ).execute()
        )
        
        files = response.get('files', [])
        
        if not files:
            logger.info("No files found in your Google Drive")
            return
            
        logger.info(f"Found {len(files)} files")
        
        # Display files with index
        for i, file in enumerate(files, 1):
            file_type = file.get('mimeType', 'unknown')
            file_id = file.get('id')
            file_name = file.get('name')
            logger.info(f"{i}. {file_name} ({file_type}) - ID: {file_id}")
        
        # Ask user which file to download
        try:
            file_index = int(input("\nEnter the number of the file to download (0 to exit): "))
            
            if file_index == 0:
                logger.info("Exiting")
                return
                
            if file_index < 1 or file_index > len(files):
                logger.error(f"Invalid selection. Please choose a number between 1 and {len(files)}")
                return
            
            selected_file = files[file_index - 1]
            file_id = selected_file.get('id')
            file_name = selected_file.get('name')
            file_type = selected_file.get('mimeType')
            
            logger.info(f"Downloading: {file_name}")
            
            # For folders, we can't download
            if file_type == 'application/vnd.google-apps.folder':
                logger.info("This is a folder, listing contents...")
                await list_folder_contents(connector, file_id, file_name)
                return
                
            # For Google Docs/Sheets, we need special handling
            if file_type.startswith('application/vnd.google-apps.'):
                logger.info(f"This is a Google Docs file ({file_type}), can't download directly.")
                logger.info(f"View online at: {selected_file.get('webViewLink')}")
                return
            
            # Download regular files
            try:
                # Use the connector's download method
                file_content = await connector.download_document(file_id)
                
                # Save to downloads directory with original name
                safe_name = ''.join(c if c.isalnum() or c in [' ', '.', '-', '_'] else '_' for c in file_name)
                download_path = DOWNLOAD_DIR / safe_name
                
                with open(download_path, "wb") as f:
                    f.write(file_content)
                
                logger.info(f"Downloaded {len(file_content)} bytes to {download_path}")
                
                # If it's a text file, show the content
                if file_type in ['text/plain', 'application/json', 'text/markdown', 'text/csv']:
                    try:
                        text_content = file_content.decode('utf-8')
                        print("\n=== File Content ===")
                        print(text_content[:2000] + "..." if len(text_content) > 2000 else text_content)
                        print("=" * 20)
                    except UnicodeDecodeError:
                        logger.error("Could not decode file as text")
            except Exception as e:
                logger.error(f"Error downloading file: {e}")
            
        except ValueError:
            logger.error("Please enter a valid number")
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        import traceback
        traceback.print_exc()

async def list_folder_contents(connector, folder_id, folder_name):
    """List the contents of a specific folder"""
    logger.info(f"\nListing contents of folder: {folder_name}")
    
    try:
        # Use the Drive API directly
        loop = asyncio.get_running_loop()
        
        # Query for files in this folder
        response = await loop.run_in_executor(
            None,
            lambda: connector._drive_service.files().list(
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, createdTime, webViewLink)",
                q=f"'{folder_id}' in parents and trashed = false"
            ).execute()
        )
        
        files = response.get('files', [])
        
        if not files:
            logger.info(f"No files found in folder '{folder_name}'")
            return
            
        logger.info(f"Found {len(files)} files in folder '{folder_name}'")
        
        # Display files with index
        for i, file in enumerate(files, 1):
            file_type = file.get('mimeType', 'unknown')
            file_id = file.get('id')
            file_name = file.get('name')
            logger.info(f"{i}. {file_name} ({file_type}) - ID: {file_id}")
    
    except Exception as e:
        logger.error(f"Error listing folder contents: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(list_and_read_files()) 