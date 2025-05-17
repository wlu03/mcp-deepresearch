from typing import List, Dict, Any, Optional, Union
import aiohttp
import asyncio
import os
import io
from datetime import datetime
import json
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from ..models import DriveDocument, Paper, PaperSummary
from .base import BaseConnector

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file deepresearch_token.json
SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = 'deepresearch_token.json'
CREDENTIALS_FILE = 'deepresearch_credentials.json'

class GoogleDriveConnector(BaseConnector):
    """Connector for Google Drive to store and retrieve research documents."""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        super().__init__(session)
        self._drive_service = None
        
    async def authenticate(self) -> bool:
        """Authenticate with Google Drive."""
        loop = asyncio.get_running_loop()
        
        creds = None
        # The file deepresearch_token.json stores the user's access and refresh tokens
        if os.path.exists(TOKEN_FILE):
            try:
                creds = await loop.run_in_executor(
                    None, lambda: Credentials.from_authorized_user_info(
                        json.load(open(TOKEN_FILE))
                    )
                )
            except Exception as e:
                logger.warning(f"Error loading credentials: {e}")
                
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    await loop.run_in_executor(
                        None, lambda: creds.refresh(Request())
                    )
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    creds = None
                    
            if not creds:
                if not os.path.exists(CREDENTIALS_FILE):
                    logger.error(f"Credentials file {CREDENTIALS_FILE} not found")
                    return False
                    
                try:
                    flow = await loop.run_in_executor(
                        None, 
                        lambda: InstalledAppFlow.from_client_secrets_file(
                            CREDENTIALS_FILE, SCOPES
                        )
                    )
                    creds = await loop.run_in_executor(
                        None, lambda: flow.run_local_server(port=0)
                    )
                except Exception as e:
                    logger.error(f"Error during OAuth flow: {e}")
                    return False
                    
            # Save the credentials for the next run
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
                
        # Create the Drive API client
        self._drive_service = await loop.run_in_executor(
            None, lambda: build('drive', 'v3', credentials=creds)
        )
        return True
        
    async def ensure_authenticated(self):
        """Ensure we are authenticated to Google Drive."""
        if self._drive_service is None:
            success = await self.authenticate()
            if not success:
                raise ValueError("Failed to authenticate with Google Drive")
                
    async def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """Create a folder in Google Drive."""
        await self.ensure_authenticated()
        loop = asyncio.get_running_loop()
        
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            folder_metadata['parents'] = [parent_id]
            
        try:
            folder = await loop.run_in_executor(
                None,
                lambda: self._drive_service.files().create(
                    body=folder_metadata,
                    fields='id,name,webViewLink,createdTime'
                ).execute()
            )
            
            return folder['id']
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            raise ValueError(f"Failed to create folder: {str(e)}")
            
    async def find_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """Find a folder by name or create it if it doesn't exist."""
        await self.ensure_authenticated()
        loop = asyncio.get_running_loop()
        
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
            
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name)'
                ).execute()
            )
            
            files = response.get('files', [])
            if files:
                return files[0]['id']
            else:
                return await self.create_folder(folder_name, parent_id)
        except Exception as e:
            logger.error(f"Error finding folder: {e}")
            raise ValueError(f"Failed to find or create folder: {str(e)}")
            
    async def store_document(
        self, 
        content: Union[bytes, str], 
        filename: str,
        mime_type: str,
        folder_id: Optional[str] = None
    ) -> DriveDocument:
        """Store a document in Google Drive."""
        await self.ensure_authenticated()
        loop = asyncio.get_running_loop()
        
        # Prepare file metadata
        file_metadata = {'name': filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        # Prepare media content
        if isinstance(content, str):
            content = content.encode('utf-8')
            
        # Create a media upload object
        fh = io.BytesIO(content)
        media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)
        
        try:
            file = await loop.run_in_executor(
                None,
                lambda: self._drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,name,mimeType,webViewLink,createdTime'
                ).execute()
            )
            
            # Parse the created time
            created_time = datetime.fromisoformat(file['createdTime'].replace('Z', '+00:00'))
            
            return DriveDocument(
                document_id=file['id'],
                name=file['name'],
                mime_type=file['mimeType'],
                web_view_link=file['webViewLink'],
                created_time=created_time
            )
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise ValueError(f"Failed to upload file: {str(e)}")
            
    async def store_paper(self, paper: Paper, pdf_content: bytes, folder_name: str = "Research Papers") -> DriveDocument:
        """Store a research paper PDF in Google Drive."""
        # Create a sanitized filename
        safe_title = ''.join(c if c.isalnum() or c in [' ', '.', '-', '_'] else '_' for c in paper.title)
        filename = f"{safe_title}.pdf"
        
        # Find or create the research papers folder
        folder_id = await self.find_or_create_folder(folder_name)
        
        # Create a subfolder for the paper
        paper_folder_id = await self.find_or_create_folder(safe_title, folder_id)
        
        # Store the PDF
        return await self.store_document(
            content=pdf_content,
            filename=filename,
            mime_type="application/pdf",
            folder_id=paper_folder_id
        )
        
    async def store_paper_summary(self, paper: Paper, summary: PaperSummary, folder_name: str = "Research Papers") -> DriveDocument:
        """Store a summary of a research paper in Google Drive."""
        # Create a sanitized filename
        safe_title = ''.join(c if c.isalnum() or c in [' ', '.', '-', '_'] else '_' for c in paper.title)
        filename = f"{safe_title} - Summary.txt"
        
        # Find or create the research papers folder
        folder_id = await self.find_or_create_folder(folder_name)
        
        # Find the paper subfolder
        paper_folder_id = await self.find_or_create_folder(safe_title, folder_id)
        
        # Format the summary content
        content = f"# Summary of: {paper.title}\n\n"
        content += f"## Paper ID: {paper.paper_id}\n"
        content += f"## Authors: {', '.join(a.name for a in paper.authors)}\n"
        if paper.publication_date:
            content += f"## Publication Date: {paper.publication_date.strftime('%Y-%m-%d')}\n"
        content += f"## Source: {paper.source}\n\n"
        content += f"### Background\n{summary.background}\n\n"
        content += f"### Methods\n{summary.methods}\n\n"
        content += f"### Results\n{summary.results}\n\n"
        content += f"### Conclusions\n{summary.conclusions}\n"
        
        # Store the summary
        return await self.store_document(
            content=content,
            filename=filename,
            mime_type="text/plain",
            folder_id=paper_folder_id
        )
        
    async def list_documents(self, folder_id: Optional[str] = None, query: Optional[str] = None) -> List[DriveDocument]:
        """List documents in Google Drive, optionally filtered by folder and query."""
        await self.ensure_authenticated()
        loop = asyncio.get_running_loop()
        
        q_parts = ["trashed = false"]
        
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
            
        if query:
            q_parts.append(f"name contains '{query}'")
            
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._drive_service.files().list(
                    q=" and ".join(q_parts),
                    spaces='drive',
                    fields='files(id, name, mimeType, webViewLink, createdTime)'
                ).execute()
            )
            
            files = response.get('files', [])
            result = []
            
            for file in files:
                created_time = datetime.fromisoformat(file['createdTime'].replace('Z', '+00:00'))
                doc = DriveDocument(
                    document_id=file['id'],
                    name=file['name'],
                    mime_type=file['mimeType'],
                    web_view_link=file['webViewLink'],
                    created_time=created_time
                )
                result.append(doc)
                
            return result
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            raise ValueError(f"Failed to list documents: {str(e)}")
            
    async def download_document(self, document_id: str) -> bytes:
        """Download a document from Google Drive."""
        await self.ensure_authenticated()
        loop = asyncio.get_running_loop()
        
        try:
            request = self._drive_service.files().get_media(fileId=document_id)
            
            # Create an in-memory bytes buffer
            fh = io.BytesIO()
            
            # Execute the request and write to the buffer
            downloader = await loop.run_in_executor(
                None,
                lambda: request.execute(num_retries=3)
            )
            
            fh.write(downloader)
            fh.seek(0)
            return fh.read()
        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            raise ValueError(f"Failed to download document: {str(e)}")
    
    # BaseConnector abstract method implementations
    # These are placeholders as the Drive connector doesn't search papers directly
    
    async def search(self, query: Any) -> List[Any]:
        """This connector doesn't search papers directly."""
        raise NotImplementedError("GoogleDriveConnector doesn't implement paper search")
        
    async def get_paper_metadata(self, paper_id: str) -> Any:
        """This connector doesn't fetch paper metadata directly."""
        raise NotImplementedError("GoogleDriveConnector doesn't implement paper metadata retrieval")
        
    async def download_fulltext(self, paper_id: str) -> bytes:
        """This connector doesn't download papers directly."""
        raise NotImplementedError("GoogleDriveConnector doesn't implement paper download")
        
    @staticmethod
    def parse_paper_id(external_id: str) -> str:
        """This connector doesn't parse paper IDs."""
        raise NotImplementedError("GoogleDriveConnector doesn't implement paper ID parsing") 