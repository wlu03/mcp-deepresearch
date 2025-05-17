#!/usr/bin/env python3

"""
Authentication script for Google Drive.
Run this script to pre-authenticate your Google Drive connector.
"""

import asyncio
import aiohttp
from deepresearch.connectors import GoogleDriveConnector

async def main():
    # Create a session and connector
    session = aiohttp.ClientSession()
    try:
        drive_connector = GoogleDriveConnector(session)
        
        print("Authenticating with Google Drive...")
        print("A browser window should open. Please authorize the application.")
        
        # This will start the authentication flow
        await drive_connector.ensure_authenticated()
        
        print("Authentication successful!")
        print("The token has been saved to 'src/deepresearch_token.json'")
        print("You can now use the Google Drive connector with Claude.")
        
        # Test creating a folder
        folder_name = "Deep Research Test"
        folder_id = await drive_connector.find_or_create_folder(folder_name)
        print(f"Test folder '{folder_name}' created or found with ID: {folder_id}")
        
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main()) 