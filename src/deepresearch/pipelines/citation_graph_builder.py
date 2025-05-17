from typing import Dict, Any, Optional, Union, List, Set
import asyncio
import logging
from crossref.restful import Works
from ..models import Paper, CitationLink, CitationGraph
from ..connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class CitationGraphBuilder:
    """Pipeline for building citation networks between scholarly papers."""
    
    def __init__(self, connectors: Dict[str, BaseConnector]):
        """
        Initialize with a dictionary of connectors keyed by source name.
        
        Args:
            connectors: Dictionary of source connectors
        """
        self.connectors = connectors
        self._works = Works()
        
    async def build_citation_graph(
        self, 
        paper_ids: List[str], 
        depth: int = 1, 
        max_citations: int = 20,
        direction: str = "both"  # "both", "citing", or "cited"
    ) -> CitationGraph:
        """
        Build a citation graph starting from the given papers.
        
        Args:
            paper_ids: List of paper identifiers
            depth: How many levels of citations to follow (1 = direct citations only)
            max_citations: Maximum number of citations to include per paper
            direction: Whether to include papers that cite the source papers ("citing"),
                       papers that are cited by the source papers ("cited"), or both
                       
        Returns:
            CitationGraph object with nodes (papers) and links (citations)
        """
        # Track papers we've processed and citation links
        papers_dict: Dict[str, Paper] = {}
        citation_links: List[CitationLink] = []
        
        # Track papers to process
        papers_to_process = set(paper_ids)
        processed_papers: Set[str] = set()
        
        # Process papers up to the specified depth
        for current_depth in range(depth + 1):
            if not papers_to_process:
                break
                
            # Get the next batch of papers to process
            current_batch = list(papers_to_process)
            papers_to_process = set()
            
            # Process each paper in the current batch
            for paper_id in current_batch:
                if paper_id in processed_papers:
                    continue
                    
                try:
                    # Get the paper's metadata
                    paper = await self._get_paper_metadata(paper_id)
                    if paper:
                        papers_dict[paper_id] = paper
                        
                        # If we haven't reached max depth, collect citation relationships
                        if current_depth < depth:
                            # Get citations in both directions if requested
                            if direction in ["both", "citing"]:
                                citing_papers = await self._get_citing_papers(paper_id, max_citations)
                                for citing_id, citing_paper in citing_papers.items():
                                    if citing_id not in papers_dict:
                                        papers_dict[citing_id] = citing_paper
                                    if citing_id not in processed_papers:
                                        papers_to_process.add(citing_id)
                                    # Add citation link: citing paper -> current paper
                                    citation_links.append(CitationLink(
                                        source_id=citing_id,
                                        target_id=paper_id
                                    ))
                                    
                            if direction in ["both", "cited"]:
                                cited_papers = await self._get_cited_papers(paper_id, max_citations)
                                for cited_id, cited_paper in cited_papers.items():
                                    if cited_id not in papers_dict:
                                        papers_dict[cited_id] = cited_paper
                                    if cited_id not in processed_papers:
                                        papers_to_process.add(cited_id)
                                    # Add citation link: current paper -> cited paper
                                    citation_links.append(CitationLink(
                                        source_id=paper_id,
                                        target_id=cited_id
                                    ))
                                    
                        processed_papers.add(paper_id)
                except Exception as e:
                    logger.error(f"Error processing paper {paper_id}: {str(e)}")
                    processed_papers.add(paper_id)  # Mark as processed to avoid retry
                    
        # Create the graph from collected data
        return CitationGraph(
            nodes=list(papers_dict.values()),
            links=citation_links
        )
        
    async def _get_paper_metadata(self, paper_id: str) -> Optional[Paper]:
        """
        Get metadata for a paper using the appropriate connector.
        
        Args:
            paper_id: Identifier for the paper
            
        Returns:
            Paper object or None if not found
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
                        break
                except (NotImplementedError, ValueError):
                    continue
                    
        if connector is None:
            # For papers without a connector, try Crossref as a fallback
            if paper_id.startswith("doi:"):
                doi = paper_id.replace("doi:", "")
                loop = asyncio.get_running_loop()
                try:
                    crossref_data = await loop.run_in_executor(
                        None, lambda: self._works.doi(doi)
                    )
                    if crossref_data:
                        # Convert Crossref data to Paper object
                        return await self._crossref_to_paper(crossref_data)
                except Exception as e:
                    logger.warning(f"Error fetching DOI from Crossref: {e}")
                    
            return None
            
        # Get metadata using the connector
        try:
            return await connector.get_paper_metadata(paper_id)
        except Exception as e:
            logger.warning(f"Error getting paper metadata: {e}")
            return None
            
    async def _get_citing_papers(self, paper_id: str, max_papers: int) -> Dict[str, Paper]:
        """
        Get papers that cite the given paper.
        
        Args:
            paper_id: Identifier for the paper
            max_papers: Maximum number of papers to return
            
        Returns:
            Dictionary of papers keyed by their ID
        """
        # This is a simplified implementation that would be customized for each source
        
        # Check if we have a DOI
        doi = None
        if paper_id.startswith("doi:"):
            doi = paper_id.replace("doi:", "")
        else:
            # Try to get the paper metadata first to extract DOI
            paper = await self._get_paper_metadata(paper_id)
            if paper and paper.doi:
                doi = paper.doi
                
        if not doi:
            return {}
            
        # Use Crossref to get citing papers
        loop = asyncio.get_running_loop()
        try:
            # Note: Crossref's citing-doi endpoint requires an API token for production use
            citing_works = await loop.run_in_executor(
                None, 
                lambda: list(self._works.filter(references=doi).limit(max_papers))
            )
            
            papers = {}
            for work in citing_works:
                paper = await self._crossref_to_paper(work)
                if paper:
                    papers[paper.paper_id] = paper
                    
            return papers
        except Exception as e:
            logger.warning(f"Error getting citing papers: {e}")
            return {}
            
    async def _get_cited_papers(self, paper_id: str, max_papers: int) -> Dict[str, Paper]:
        """
        Get papers that are cited by the given paper.
        
        Args:
            paper_id: Identifier for the paper
            max_papers: Maximum number of papers to return
            
        Returns:
            Dictionary of papers keyed by their ID
        """
        # This is a source-specific operation; each source requires different handling
        
        # For Semantic Scholar, we can use their API directly
        if paper_id.startswith("semanticscholar:"):
            if "semanticscholar" in self.connectors:
                connector = self.connectors["semanticscholar"]
                try:
                    # Get the paper's metadata which includes references
                    paper = await connector.get_paper_metadata(paper_id)
                    
                    # The reference data is in raw_metadata
                    if paper and paper.raw_metadata and "references" in paper.raw_metadata:
                        references = paper.raw_metadata["references"][:max_papers]
                        
                        papers = {}
                        for ref in references:
                            if isinstance(ref, dict) and "paperId" in ref:
                                ref_id = f"semanticscholar:{ref['paperId']}"
                                try:
                                    ref_paper = await connector.get_paper_metadata(ref_id)
                                    if ref_paper:
                                        papers[ref_id] = ref_paper
                                except Exception:
                                    pass
                                    
                        return papers
                except Exception as e:
                    logger.warning(f"Error getting references from Semantic Scholar: {e}")
                    
        # For papers with DOIs, we can use Crossref
        doi = None
        if paper_id.startswith("doi:"):
            doi = paper_id.replace("doi:", "")
        else:
            # Try to get the paper metadata first to extract DOI
            paper = await self._get_paper_metadata(paper_id)
            if paper and paper.doi:
                doi = paper.doi
                
        if doi:
            loop = asyncio.get_running_loop()
            try:
                work = await loop.run_in_executor(
                    None, lambda: self._works.doi(doi)
                )
                
                if work and "reference" in work:
                    references = work["reference"][:max_papers]
                    
                    papers = {}
                    for ref in references:
                        if "DOI" in ref:
                            ref_doi = ref["DOI"]
                            ref_id = f"doi:{ref_doi}"
                            try:
                                ref_work = await loop.run_in_executor(
                                    None, lambda: self._works.doi(ref_doi)
                                )
                                if ref_work:
                                    ref_paper = await self._crossref_to_paper(ref_work)
                                    if ref_paper:
                                        papers[ref_id] = ref_paper
                            except Exception:
                                pass
                                
                    return papers
            except Exception as e:
                logger.warning(f"Error getting references from Crossref: {e}")
                
        return {}
        
    async def _crossref_to_paper(self, crossref_data: Dict[str, Any]) -> Optional[Paper]:
        """
        Convert Crossref data to a Paper object.
        
        Args:
            crossref_data: Crossref API response data
            
        Returns:
            Paper object or None if conversion fails
        """
        try:
            # Extract the DOI
            doi = crossref_data.get("DOI")
            if not doi:
                return None
                
            # Extract authors
            authors = []
            if "author" in crossref_data:
                for author_data in crossref_data["author"]:
                    name_parts = []
                    if "given" in author_data:
                        name_parts.append(author_data["given"])
                    if "family" in author_data:
                        name_parts.append(author_data["family"])
                        
                    if name_parts:
                        from ..models import Author
                        authors.append(Author(
                            name=" ".join(name_parts),
                            affiliation=author_data.get("affiliation", [{}])[0].get("name") if author_data.get("affiliation") else None
                        ))
                        
            # Extract publication date
            pub_date = None
            if "published-print" in crossref_data:
                date_parts = crossref_data["published-print"].get("date-parts", [[]])[0]
                if len(date_parts) >= 1:
                    from datetime import datetime
                    year = date_parts[0]
                    month = date_parts[1] if len(date_parts) >= 2 else 1
                    day = date_parts[2] if len(date_parts) >= 3 else 1
                    pub_date = datetime(year, month, day)
                    
            # Create the paper
            from ..models import Paper
            return Paper(
                paper_id=f"doi:{doi}",
                title=crossref_data.get("title", [""])[0] if isinstance(crossref_data.get("title", []), list) else crossref_data.get("title", ""),
                authors=authors,
                abstract=crossref_data.get("abstract", ""),
                url=crossref_data.get("URL", ""),
                pdf_url=None,  # Crossref doesn't provide direct PDF links
                publication_date=pub_date,
                journal=crossref_data.get("container-title", [""])[0] if isinstance(crossref_data.get("container-title", []), list) else crossref_data.get("container-title", ""),
                doi=doi,
                source="crossref",
                citations_count=crossref_data.get("is-referenced-by-count"),
                raw_metadata=crossref_data
            )
        except Exception as e:
            logger.error(f"Error converting Crossref data to Paper: {e}")
            return None 