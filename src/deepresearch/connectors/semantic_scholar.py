from typing import List, Dict, Any, Optional
import aiohttp
import asyncio
from datetime import datetime
import semanticscholar as ss
from ..models import Paper, Author, SearchQuery
from .base import BaseConnector

class SemanticScholarConnector(BaseConnector):
    """Connector for the Semantic Scholar API."""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None, api_key: Optional[str] = None):
        super().__init__(session)
        # Semantic Scholar client
        self._client = ss.SemanticScholar(api_key=api_key)
        
    async def search(self, query: SearchQuery) -> List[Paper]:
        """Search for papers on Semantic Scholar."""
        loop = asyncio.get_running_loop()
        
        # Use run_in_executor to make the synchronous API call non-blocking
        search_params = {
            "query": query.query,
            "limit": query.max_results,
            "fields": [
                "paperId", "externalIds", "url", "title", "abstract", 
                "venue", "year", "publicationDate", "journal", 
                "authors", "citationCount", "openAccessPdf"
            ]
        }
        
        results = await loop.run_in_executor(
            None, lambda: self._client.search_paper(**search_params)
        )
        
        papers = []
        for result in results:
            # Process authors
            authors = []
            if "authors" in result and result["authors"]:
                for author_data in result["authors"]:
                    authors.append(Author(
                        name=author_data.get("name", ""),
                        affiliation=None,  # Not provided in basic search
                        email=None  # Not provided in basic search
                    ))
                    
            # Get publication date
            pub_date = None
            if "publicationDate" in result and result["publicationDate"]:
                try:
                    pub_date = datetime.fromisoformat(result["publicationDate"])
                except (ValueError, TypeError):
                    # Fallback to just the year
                    if "year" in result and result["year"]:
                        try:
                            pub_date = datetime(int(result["year"]), 1, 1)
                        except (ValueError, TypeError):
                            pass
                            
            # Get DOI
            doi = None
            if "externalIds" in result and result["externalIds"]:
                doi = result["externalIds"].get("DOI")
                
            # Get PDF URL
            pdf_url = None
            if "openAccessPdf" in result and result["openAccessPdf"]:
                pdf_url = result["openAccessPdf"].get("url")
                
            paper_id = f"semanticscholar:{result['paperId']}"
            
            paper = Paper(
                paper_id=paper_id,
                title=result.get("title", ""),
                authors=authors,
                abstract=result.get("abstract", ""),
                url=result.get("url", f"https://www.semanticscholar.org/paper/{result['paperId']}"),
                pdf_url=pdf_url,
                publication_date=pub_date,
                journal=result.get("journal", {}).get("name", result.get("venue", "")),
                doi=doi,
                source="semanticscholar",
                citations_count=result.get("citationCount"),
                raw_metadata={
                    "external_ids": result.get("externalIds", {}),
                    "s2_fields": result.get("fieldsOfStudy", [])
                }
            )
            papers.append(paper)
            
        return papers
        
    async def get_paper_metadata(self, paper_id: str) -> Paper:
        """Get detailed metadata for a specific Semantic Scholar paper."""
        # Extract the actual paper ID
        if ":" in paper_id:
            _, ss_id = paper_id.split(":", 1)
        else:
            ss_id = paper_id
            
        loop = asyncio.get_running_loop()
        
        # Get detailed paper info
        fields = [
            "paperId", "externalIds", "url", "title", "abstract", 
            "venue", "year", "publicationDate", "journal", 
            "authors", "citationCount", "openAccessPdf", 
            "fieldsOfStudy", "references", "citations"
        ]
        
        result = await loop.run_in_executor(
            None, lambda: self._client.get_paper(ss_id, fields=fields)
        )
        
        if not result:
            raise ValueError(f"Semantic Scholar paper with ID {ss_id} not found")
            
        # Process authors
        authors = []
        if "authors" in result and result["authors"]:
            for author_data in result["authors"]:
                authors.append(Author(
                    name=author_data.get("name", ""),
                    affiliation=None,  # Not provided in standard response
                    email=None  # Not provided in standard response
                ))
                
        # Get publication date
        pub_date = None
        if "publicationDate" in result and result["publicationDate"]:
            try:
                pub_date = datetime.fromisoformat(result["publicationDate"])
            except (ValueError, TypeError):
                # Fallback to just the year
                if "year" in result and result["year"]:
                    try:
                        pub_date = datetime(int(result["year"]), 1, 1)
                    except (ValueError, TypeError):
                        pass
                        
        # Get DOI
        doi = None
        if "externalIds" in result and result["externalIds"]:
            doi = result["externalIds"].get("DOI")
            
        # Get PDF URL
        pdf_url = None
        if "openAccessPdf" in result and result["openAccessPdf"]:
            pdf_url = result["openAccessPdf"].get("url")
            
        return Paper(
            paper_id=f"semanticscholar:{result['paperId']}",
            title=result.get("title", ""),
            authors=authors,
            abstract=result.get("abstract", ""),
            url=result.get("url", f"https://www.semanticscholar.org/paper/{result['paperId']}"),
            pdf_url=pdf_url,
            publication_date=pub_date,
            journal=result.get("journal", {}).get("name", result.get("venue", "")),
            doi=doi,
            source="semanticscholar",
            citations_count=result.get("citationCount"),
            raw_metadata={
                "external_ids": result.get("externalIds", {}),
                "s2_fields": result.get("fieldsOfStudy", []),
                "references_count": len(result.get("references", [])),
                "citations_count": len(result.get("citations", []))
            }
        )
        
    async def download_fulltext(self, paper_id: str) -> bytes:
        """Download the PDF of a paper from Semantic Scholar if available."""
        await self._ensure_session()
        
        # Get paper metadata first to find PDF URL
        paper = await self.get_paper_metadata(paper_id)
        
        if not paper.pdf_url:
            raise ValueError(f"No open access PDF available for {paper_id}")
            
        # Download the PDF
        async with self._session.get(paper.pdf_url) as response:
            if response.status != 200:
                raise ValueError(f"Failed to download PDF for {paper_id}: {response.status}")
                
            return await response.read()
            
    @staticmethod
    def parse_paper_id(external_id: str) -> str:
        """Parse and normalize a Semantic Scholar ID."""
        if external_id.startswith("semanticscholar:"):
            return external_id
            
        # If it's a URL, extract the ID
        if "semanticscholar.org/paper" in external_id:
            # Handle URLs like https://www.semanticscholar.org/paper/1234567890
            parts = external_id.split("/")
            for i, part in enumerate(parts):
                if part == "paper" and i < len(parts) - 1:
                    return f"semanticscholar:{parts[i+1]}"
                    
        # For DOIs, we'd need to search, but this is a simple implementation
        if external_id.startswith("10."):
            return f"doi:{external_id}"  # Flag for special handling
            
        # If it's just the ID
        return f"semanticscholar:{external_id}" 