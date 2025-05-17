import asyncio
import os
import sys
import logging
from pathlib import Path
import aiohttp
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("drive_connector_test")

# Add the parent directory to the path so we can import deepresearch modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from deepresearch.connectors import GoogleDriveConnector

# Create test directory
TEST_DIR = Path("test_files")
TEST_DIR.mkdir(exist_ok=True)

# Create downloads directory
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Path to credentials file
CREDENTIALS_FILE = os.environ.get(
    "GOOGLE_CREDENTIALS_FILE", 
    os.path.join("credentials", "client_secret_395039126310-8ovj91u9ef31o0pehta2n957bjqtaimp.apps.googleusercontent.com.json")
)

async def create_test_file(filename="test_document.txt", content="This is a test file created by Deep Research"):
    """Create a test file to upload to Google Drive"""
    filepath = TEST_DIR / filename
    with open(filepath, "w") as f:
        f.write(content)
    logger.info(f"Created test file: {filepath}")
    return filepath

async def test_drive_connector():
    """Test Google Drive connector functionality"""
    logger.info("=== Testing Google Drive Connector ===")
    
    # Check if credentials file exists
    if not os.path.exists(CREDENTIALS_FILE):
        logger.error(f"Credentials file not found: {CREDENTIALS_FILE}")
        logger.error("Please follow the instructions to set up Google Drive API credentials")
        return
    
    logger.info(f"Using credentials file: {CREDENTIALS_FILE}")
    
    try:
        # Create session
        async with aiohttp.ClientSession() as session:
            # Initialize connector
            connector = GoogleDriveConnector(session)
            
            # Set up authentication 
            logger.info("Setting up authentication...")
            try:
                # Load credentials
                with open(CREDENTIALS_FILE, 'r') as f:
                    credentials_data = json.load(f)
                
                # Check if client_id and client_secret are in environment variables
                client_id = os.environ.get("GOOGLE_CLIENT_ID", credentials_data.get("installed", {}).get("client_id"))
                client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", credentials_data.get("installed", {}).get("client_secret"))
                
                if not client_id or not client_secret:
                    logger.error("Client ID or Client Secret not found in credentials file or environment variables")
                    return
                
                # Set credentials
                os.environ["GOOGLE_CLIENT_ID"] = client_id
                os.environ["GOOGLE_CLIENT_SECRET"] = client_secret
                
                # Initialize the connector (this will trigger authentication flow if not authenticated)
                await connector.authenticate()
                logger.info("Authentication successful")
                
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                return
            
            # Test listing files
            logger.info("\nListing files from Google Drive...")
            try:
                files = await connector.list_documents()
                logger.info(f"Found {len(files)} files")
                for i, file in enumerate(files[:5], 1):  # Show up to 5 files
                    logger.info(f"{i}. {file.name} (ID: {file.document_id})")
            except Exception as e:
                logger.error(f"Error listing files: {e}")
            
            # Test creating a folder
            folder_name = "DeepResearch_Test"
            logger.info(f"\nCreating a test folder: {folder_name}")
            try:
                folder_id = await connector.create_folder(folder_name)
                logger.info(f"Created folder with ID: {folder_id}")
                
                # Test uploading a file
                logger.info("\nUploading a test file...")
                test_filepath = await create_test_file()
                
                with open(test_filepath, "rb") as f:
                    file_content = f.read()
                
                upload_result = await connector.store_document(
                    content=file_content,
                    filename="test_document.txt",
                    mime_type="text/plain",
                    folder_id=folder_id
                )
                
                file_id = upload_result.document_id
                logger.info(f"Uploaded file with ID: {file_id}")
                
                # Test downloading the file
                logger.info("\nDownloading the uploaded file...")
                download_path = DOWNLOAD_DIR / "downloaded_test_document.txt"
                
                file_content = await connector.download_document(file_id)
                
                with open(download_path, "wb") as f:
                    f.write(file_content)
                    
                logger.info(f"Downloaded file to: {download_path}")
                
                # Verify the content
                with open(download_path, "r") as f:
                    content = f.read()
                
                logger.info(f"File content: {content}")
                
                # Test deleting the file
                logger.info("\nCleaning up test files...")
                try:
                    # Not implemented yet - use custom API call
                    logger.info("Leaving test files in place - delete manually if desired")
                except Exception as e:
                    logger.error(f"Error deleting files: {e}")
                
            except Exception as e:
                logger.error(f"Error in file operations: {e}")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_drive_connector()

if __name__ == "__main__":
    asyncio.run(main()) 