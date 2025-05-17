import arxiv
from typing import List, Dict, Any, Optional
import aiohttp
import asyncio
from datetime import datetime
from ..models import Paper, Author, SearchQuery
from .base import BaseConnector

class ArXivConnector(BaseConnector):
    """Connector for the arXiv API."""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        super().__init__(session)
        # ArXiv client doesn't need an aiohttp session directly
        self._client = arxiv.Client()
        
    async def search(self, query: SearchQuery) -> List[Paper]:
        """Search for papers on arXiv."""
        # Convert our search query to arXiv search parameters
        search = arxiv.Search(
            query=query.query,
            max_results=query.max_results,
            sort_by=arxiv.SortCriterion.Relevance if query.sort_by == "relevance" else arxiv.SortCriterion.SubmittedDate
        )
        
        # Use run_in_executor to make the synchronous ArXiv API call non-blocking
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None, lambda: list(self._client.results(search))
        )
        
        papers = []
        for result in results:
            authors = [Author(name=author.name) for author in result.authors]
            
            paper = Paper(
                paper_id=f"arxiv:{result.get_short_id()}",
                title=result.title,
                authors=authors,
                abstract=result.summary,
                url=result.entry_id,
                pdf_url=result.pdf_url,
                publication_date=result.published,
                journal="arXiv",
                doi=None,  # arXiv entries don't have DOIs by default
                source="arxiv",
                citations_count=None, # Not provided by arXiv API
                raw_metadata={
                    "categories": [cat for cat in result.categories],
                    "comment": result.comment,
                    "journal_ref": result.journal_ref,
                    "primary_category": result.primary_category
                }
            )
            papers.append(paper)
            
        return papers
        
    async def get_paper_metadata(self, paper_id: str) -> Paper:
        """Get detailed metadata for a specific arXiv paper."""
        # Extract the actual arXiv ID
        if ":" in paper_id:
            _, arxiv_id = paper_id.split(":", 1)
        else:
            arxiv_id = paper_id
            
        search = arxiv.Search(id_list=[arxiv_id])
        
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None, lambda: list(self._client.results(search))
        )
        
        if not results:
            raise ValueError(f"ArXiv paper with ID {arxiv_id} not found")
            
        result = results[0]
        authors = [Author(name=author.name) for author in result.authors]
        
        return Paper(
            paper_id=f"arxiv:{result.get_short_id()}",
            title=result.title,
            authors=authors,
            abstract=result.summary,
            url=result.entry_id,
            pdf_url=result.pdf_url,
            publication_date=result.published,
            journal="arXiv",
            doi=None,
            source="arxiv",
            citations_count=None,
            raw_metadata={
                "categories": [cat for cat in result.categories],
                "comment": result.comment,
                "journal_ref": result.journal_ref,
                "primary_category": result.primary_category
            }
        )
        
    async def download_fulltext(self, paper_id: str) -> bytes:
        """Download the PDF of an arXiv paper."""
        await self._ensure_session()
        
        # Extract the actual arXiv ID
        if ":" in paper_id:
            _, arxiv_id = paper_id.split(":", 1)
        else:
            arxiv_id = paper_id
            
        # First get the paper metadata to get the PDF URL
        paper = await self.get_paper_metadata(f"arxiv:{arxiv_id}")
        
        if not paper.pdf_url:
            raise ValueError(f"No PDF URL available for paper {paper_id}")
            
        # Download the PDF
        async with self._session.get(paper.pdf_url) as response:
            if response.status != 200:
                raise ValueError(f"Failed to download PDF for {paper_id}: {response.status}")
                
            return await response.read()
            
    @staticmethod
    def parse_paper_id(external_id: str) -> str:
        """Parse and normalize an arXiv ID."""
        if external_id.startswith("arxiv:"):
            return external_id
        
        # If it's a URL, extract the ID
        if "arxiv.org" in external_id:
            # Handle URLs like https://arxiv.org/abs/2104.08935
            parts = external_id.split("/")
            for i, part in enumerate(parts):
                if part == "abs" and i < len(parts) - 1:
                    return f"arxiv:{parts[i+1]}"
                    
        # If it's just the ID
        return f"arxiv:{external_id}" 