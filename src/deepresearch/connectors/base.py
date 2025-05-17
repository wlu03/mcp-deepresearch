from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
from ..models import Paper, SearchQuery

class BaseConnector(ABC):
    """Base class for all connectors to scholarly sources."""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the connector with an optional aiohttp session."""
        self._session = session
        self._owns_session = False
        
    async def _ensure_session(self):
        """Ensure we have an aiohttp session to use."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
            
    async def close(self):
        """Close resources if we own them."""
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None
            self._owns_session = False
            
    @abstractmethod
    async def search(self, query: SearchQuery) -> List[Paper]:
        """Search for papers matching the query."""
        pass
        
    @abstractmethod
    async def get_paper_metadata(self, paper_id: str) -> Paper:
        """Get detailed metadata for a specific paper."""
        pass
        
    @abstractmethod
    async def download_fulltext(self, paper_id: str) -> bytes:
        """Download the full text of a paper as bytes."""
        pass
        
    @staticmethod
    @abstractmethod
    def parse_paper_id(external_id: str) -> str:
        """Parse and normalize an external ID to the connector's native format."""
        pass 