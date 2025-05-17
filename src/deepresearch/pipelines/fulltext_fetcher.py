from typing import Dict, Any, Optional, Union, List, Tuple
import asyncio
import aiohttp
import io
import PyPDF2
import logging
import re
from ..models import Paper
from ..connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class FullTextFetcher:
    """Pipeline for fetching and extracting full text from scholarly papers."""
    
    def __init__(self, connectors: Dict[str, BaseConnector]):
        """Initialize with a dictionary of connectors keyed by source name."""
        self.connectors = connectors
        
    async def _ensure_aiohttp_session(self):
        """Create an aiohttp session if none exists."""
        if not hasattr(self, '_session') or self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        
    async def close(self):
        """Close resources owned by this fetcher."""
        if hasattr(self, '_session') and self._session and getattr(self, '_owns_session', False):
            await self._session.close()
            self._session = None
            self._owns_session = False
            
    async def download_pdf(self, paper: Paper) -> Optional[bytes]:
        """
        Download PDF for a paper using the appropriate connector.
        
        Args:
            paper: Paper model with metadata
            
        Returns:
            PDF content as bytes or None if unavailable
        """
        # Determine the appropriate connector
        source = paper.source
        if source in self.connectors:
            connector = self.connectors[source]
            try:
                return await connector.download_fulltext(paper.paper_id)
            except Exception as e:
                logger.warning(f"Failed to download PDF using {source} connector: {str(e)}")
                
        # Fallback: try direct download if paper has a PDF URL
        if paper.pdf_url:
            await self._ensure_aiohttp_session()
            try:
                async with self._session.get(paper.pdf_url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'pdf' in content_type.lower() or paper.pdf_url.lower().endswith('.pdf'):
                            return await response.read()
            except Exception as e:
                logger.warning(f"Failed to download PDF directly from URL: {str(e)}")
                
        # If paper has a DOI, try resolving via DOI
        if paper.doi:
            await self._ensure_aiohttp_session()
            try:
                doi_url = f"https://doi.org/{paper.doi}"
                async with self._session.get(doi_url, allow_redirects=True) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'pdf' in content_type.lower():
                            return await response.read()
            except Exception as e:
                logger.warning(f"Failed to resolve PDF via DOI: {str(e)}")
                
        # No PDF found
        return None
        
    async def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract text content from a PDF.
        
        Args:
            pdf_content: PDF content as bytes
            
        Returns:
            Extracted text as a string
        """
        loop = asyncio.get_running_loop()
        
        # Use PyPDF2 to extract text (run in executor to not block)
        try:
            # Create an in-memory file for PyPDF2
            pdf_file = io.BytesIO(pdf_content)
            
            # Define a function to extract text using PyPDF2
            def extract_with_pypdf():
                text = ""
                try:
                    with PyPDF2.PdfReader(pdf_file) as pdf:
                        for page_num in range(len(pdf.pages)):
                            page = pdf.pages[page_num]
                            text += page.extract_text() + "\n\n"
                except Exception as e:
                    logger.error(f"Error extracting text with PyPDF2: {e}")
                return text
                
            # Run in executor to avoid blocking
            return await loop.run_in_executor(None, extract_with_pypdf)
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {str(e)}")
            return ""
            
    async def get_paper_fulltext(self, paper: Paper) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Get the full text of a paper as both PDF and extracted text.
        
        Args:
            paper: Paper model with metadata
            
        Returns:
            Tuple of (pdf_content, extracted_text)
        """
        pdf_content = await self.download_pdf(paper)
        
        # If PDF was found, extract text
        if pdf_content:
            text_content = await self.extract_text_from_pdf(pdf_content)
            return pdf_content, text_content
            
        return None, None
        
    async def fetch_and_extract(self, paper_id: str) -> Tuple[Optional[Paper], Optional[bytes], Optional[str]]:
        """
        Complete pipeline to fetch paper metadata, download PDF, and extract text.
        
        Args:
            paper_id: Identifier for the paper, possibly prefixed with source (e.g., 'arxiv:2104.08935')
            
        Returns:
            Tuple of (paper_metadata, pdf_content, extracted_text)
        """
        # Determine the source and ID
        source = None
        if ':' in paper_id:
            source, _ = paper_id.split(':', 1)
            
        # Find an appropriate connector
        connector = None
        if source and source in self.connectors:
            connector = self.connectors[source]
        else:
            # Try all connectors
            for conn_source, conn in self.connectors.items():
                try:
                    normalized_id = conn.parse_paper_id(paper_id)
                    if normalized_id != paper_id:  # The connector recognized this ID format
                        connector = conn
                        paper_id = normalized_id
                        source = conn_source
                        break
                except NotImplementedError:
                    continue
                except Exception as e:
                    logger.warning(f"Error in connector {conn_source} while parsing ID: {e}")
                    
        if connector is None:
            raise ValueError(f"No connector available for paper ID: {paper_id}")
            
        # Get metadata
        try:
            paper = await connector.get_paper_metadata(paper_id)
        except Exception as e:
            logger.error(f"Failed to get paper metadata: {e}")
            return None, None, None
            
        # Get full text
        pdf_content, text_content = await self.get_paper_fulltext(paper)
        
        return paper, pdf_content, text_content 