from typing import List, Dict, Any, Optional
import aiohttp
import asyncio
from datetime import datetime
import re
from scholarly import scholarly
from ..models import Paper, Author, SearchQuery
from .base import BaseConnector
import logging

logger = logging.getLogger(__name__)

class GoogleScholarConnector(BaseConnector):
    """
    Connector for Google Scholar using scholarly library.
    
    Note: Google Scholar doesn't have an official API and may rate-limit or block scraping.
    This connector should be used with caution and appropriate rate limiting.
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None, use_proxy: bool = False):
        super().__init__(session)
        self._use_proxy = use_proxy
        
    async def _setup_scholarly(self):
        """Configure scholarly with proxy if needed."""
        if self._use_proxy:
            # This would be configured with a real proxy in production
            # scholarly.use_proxy() 
            pass
            
    async def search(self, query: SearchQuery) -> List[Paper]:
        """Search for papers on Google Scholar."""
        await self._setup_scholarly()
        loop = asyncio.get_running_loop()
        
        # Use run_in_executor to make the synchronous API call non-blocking
        search_query = scholarly.search_pubs(
            query.query,
            patents=False,  # Exclude patents from search
            citations=False  # Don't fetch citation data to speed up search
        )
        
        # Fetch results (limited by max_results)
        results = []
        try:
            # Get results up to max_results
            for _ in range(query.max_results):
                try:
                    result = await loop.run_in_executor(None, lambda: next(search_query))
                    results.append(result)
                except StopIteration:
                    break
        except Exception as e:
            logger.warning(f"Error searching Google Scholar: {e}")
        
        papers = []
        for i, result in enumerate(results):
            # Extract authors (google scholar can provide either a string or a list of authors)
            authors = []
            author_data = result.get("bib", {}).get("author", "")
            
            # Handle author data which can be either a string or a list
            if author_data:
                if isinstance(author_data, str):
                    # Handle string case - split on "and" or commas
                    author_names = re.split(r",\s*|\s+and\s+", author_data)
                    for name in author_names:
                        if name.strip():
                            authors.append(Author(name=name.strip()))
                elif isinstance(author_data, list):
                    # Handle list case - each item is already an author name
                    for name in author_data:
                        if isinstance(name, str) and name.strip():
                            authors.append(Author(name=name.strip()))
            
            # Publication year as datetime
            pub_date = None
            pub_year = result.get("bib", {}).get("pub_year")
            if pub_year:
                try:
                    pub_date = datetime(int(pub_year), 1, 1)
                except (ValueError, TypeError):
                    pass
            
            # Citations count
            cite_count = None
            num_citations = result.get("num_citations")
            if num_citations is not None:
                cite_count = int(num_citations)
            
            # Create a paper_id from the cluster_id or a simple counter if not available
            cluster_id = result.get("cluster_id", f"gs-temp-{i}")
            paper_id = f"googlescholar:{cluster_id}"
            
            paper = Paper(
                paper_id=paper_id,
                title=result.get("bib", {}).get("title", ""),
                authors=authors,
                abstract="",  # Google Scholar doesn't provide abstracts
                url=result.get("pub_url", ""),
                pdf_url=result.get("eprint_url"),
                publication_date=pub_date,
                journal=result.get("bib", {}).get("venue", ""),
                doi=None,  # Not directly provided
                source="googlescholar",
                citations_count=cite_count,
                raw_metadata={
                    "snippet": result.get("snippet", ""),
                    "source": result.get("source", ""),
                    "citation_id": result.get("citation_id")
                }
            )
            papers.append(paper)
        
        return papers
    
    async def get_paper_metadata(self, paper_id: str) -> Paper:
        """
        Get detailed metadata for a specific Google Scholar paper.
        
        This is challenging with Google Scholar as it doesn't have persistent IDs.
        We'll need to search for the paper and match it.
        """
        # Extract the actual Google Scholar ID
        if ":" in paper_id:
            _, gs_id = paper_id.split(":", 1)
        else:
            gs_id = paper_id
        
        await self._setup_scholarly()
        loop = asyncio.get_running_loop()
        
        # Try to look up by cluster_id
        try:
            # Fix the URL construction - use correct Google Scholar URL format
            search_url = f"https://scholar.google.com/scholar?cluster={gs_id}"
            logger.debug(f"Searching using URL: {search_url}")
            
            result = await loop.run_in_executor(
                None, lambda: scholarly.search_pubs_custom_url(search_url)
            )
            # Get the first result
            paper_data = await loop.run_in_executor(None, lambda: next(result))
            
            # Now fill in the details
            full_paper = await loop.run_in_executor(
                None, lambda: scholarly.fill(paper_data)
            )
            
            # Extract authors (handling both string and list cases)
            authors = []
            author_data = full_paper.get("bib", {}).get("author", "")
            
            if author_data:
                if isinstance(author_data, str):
                    # Handle string case
                    author_names = re.split(r",\s*|\s+and\s+", author_data)
                    for name in author_names:
                        if name.strip():
                            authors.append(Author(name=name.strip()))
                elif isinstance(author_data, list):
                    # Handle list case
                    for name in author_data:
                        if isinstance(name, str) and name.strip():
                            authors.append(Author(name=name.strip()))
            
            pub_date = None
            pub_year = full_paper.get("bib", {}).get("pub_year")
            if pub_year:
                try:
                    pub_date = datetime(int(pub_year), 1, 1)
                except (ValueError, TypeError):
                    pass
            
            cite_count = None
            num_citations = full_paper.get("num_citations")
            if num_citations is not None:
                cite_count = int(num_citations)
            
            return Paper(
                paper_id=f"googlescholar:{gs_id}",
                title=full_paper.get("bib", {}).get("title", ""),
                authors=authors,
                abstract="",  # Google Scholar doesn't provide abstracts
                url=full_paper.get("pub_url", ""),
                pdf_url=full_paper.get("eprint_url"),
                publication_date=pub_date,
                journal=full_paper.get("bib", {}).get("venue", ""),
                doi=None,
                source="googlescholar",
                citations_count=cite_count,
                raw_metadata={
                    "snippet": full_paper.get("snippet", ""),
                    "source": full_paper.get("source", ""),
                    "citation_id": full_paper.get("citation_id"),
                    "citations": [cite.get("bib", {}).get("title", "") 
                                  for cite in full_paper.get("citations", [])]
                }
            )
        
        except Exception as e:
            logger.error(f"Error fetching Google Scholar paper metadata: {e}")
            raise ValueError(f"Failed to retrieve Google Scholar paper with ID {gs_id}: {str(e)}")
    
    async def download_fulltext(self, paper_id: str) -> bytes:
        """
        Download the full text of a paper from Google Scholar if available.
        
        Note: Google Scholar often only provides links to publisher sites, 
        not direct PDF downloads.
        """
        await self._ensure_session()
        
        # Get paper metadata first to find PDF URL
        paper = await self.get_paper_metadata(paper_id)
        
        if not paper.pdf_url:
            raise ValueError(f"No PDF URL available for {paper_id}")
        
        # Download the PDF
        async with self._session.get(paper.pdf_url) as response:
            if response.status != 200:
                raise ValueError(f"Failed to download PDF for {paper_id}: {response.status}")
            
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower():
                raise ValueError(f"Retrieved content is not a PDF for {paper_id}")
                
            return await response.read()
    
    @staticmethod
    def parse_paper_id(external_id: str) -> str:
        """Parse and normalize a Google Scholar ID."""
        if external_id.startswith("googlescholar:"):
            return external_id
        
        # Handle common Google Scholar URL patterns
        if "scholar.google.com" in external_id:
            # Extract cluster ID from URL
            match = re.search(r'cluster=([^&]+)', external_id)
            if match:
                return f"googlescholar:{match.group(1)}"
        
        # If it's just the ID
        return f"googlescholar:{external_id}" 