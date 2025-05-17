from typing import Dict, Any, Optional, List, Union, Tuple
import asyncio
import logging
import json
from datetime import datetime

from .models import Paper, PaperSummary, SearchQuery, SearchResult, Annotation, CitationGraph
from .connectors import (
    ArXivConnector, 
    PubMedConnector, 
    SemanticScholarConnector, 
    GoogleScholarConnector, 
    GoogleDriveConnector
)
from .pipelines import (
    MetadataExtractor, 
    FullTextFetcher, 
    Summarizer, 
    CitationGraphBuilder
)

logger = logging.getLogger(__name__)

class DeepResearchOrchestrator:
    """
    Orchestrates the research process by managing connectors and pipelines.
    
    Deep Research MCP server functionality.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the orchestrator with optional configuration.
        
        Args:
            config: Configuration dictionary with API keys, settings, etc.
        """
        self.config = config or {}
        self._session = None
        self._connectors = {}
        self._pipelines = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize connectors and pipelines."""
        if self._initialized:
            return
            
        # Create shared aiohttp session
        import aiohttp
        self._session = aiohttp.ClientSession()
        
        # Initialize connectors
        self._connectors = {
            "arxiv": ArXivConnector(self._session),
            "pubmed": PubMedConnector(
                self._session, 
                email=self.config.get("pubmed_email", "deepresearch@example.com")
            ),
            "semanticscholar": SemanticScholarConnector(
                self._session,
                api_key=self.config.get("semanticscholar_api_key")
            ),
            "googlescholar": GoogleScholarConnector(
                self._session,
                use_proxy=self.config.get("use_proxy", False)
            ),
            "drive": GoogleDriveConnector(self._session)
        }
        
        # Initialize pipelines
        self._pipelines = {
            "metadata_extractor": MetadataExtractor(),
            "fulltext_fetcher": FullTextFetcher(self._connectors),
            "summarizer": Summarizer(
                llm_api_key=self.config.get("llm_api_key")
            ),
            "citation_graph_builder": CitationGraphBuilder(self._connectors)
        }
        
        self._initialized = True
        
    async def shutdown(self):
        """Clean up resources."""
        # Close all connectors
        for connector in self._connectors.values():
            await connector.close()
            
        # Close pipelines that need cleanup
        if "fulltext_fetcher" in self._pipelines:
            await self._pipelines["fulltext_fetcher"].close()
            
        # Close session
        if self._session:
            await self._session.close()
            self._session = None
            
        self._initialized = False
        
    async def search_papers(self, query: Union[str, SearchQuery]) -> SearchResult:
        """
        Search for papers across multiple sources.
        
        Args:
            query: Either a string query or a SearchQuery object
            
        Returns:
            SearchResult object with papers and metadata
        """
        await self.initialize()
        
        # Convert string query to SearchQuery if needed
        if isinstance(query, str):
            search_query = SearchQuery(query=query)
        else:
            search_query = query
            
        # Define tasks to search each source
        search_tasks = {}
        for source in search_query.sources:
            if source in self._connectors:
                search_tasks[source] = asyncio.create_task(
                    self._connectors[source].search(search_query)
                )
                
        # Wait for all search tasks to complete
        all_papers = []
        for source, task in search_tasks.items():
            try:
                papers = await task
                all_papers.extend(papers)
            except Exception as e:
                logger.error(f"Error searching {source}: {str(e)}")
                
        # Sort results based on sort criteria
        if search_query.sort_by == "date":
            # Sort by date, newest first
            all_papers.sort(
                key=lambda p: p.publication_date or datetime.min, 
                reverse=True
            )
        elif search_query.sort_by == "citations":
            # Sort by citation count, highest first
            all_papers.sort(
                key=lambda p: p.citations_count or 0,
                reverse=True
            )
            
        # Limit results to max_results
        total_found = len(all_papers)
        all_papers = all_papers[:search_query.max_results]
        
        # Create SearchResult
        return SearchResult(
            query=search_query.query,
            papers=all_papers,
            total_found=total_found
        )
        
    async def fetch_paper_metadata(self, paper_id: str) -> Paper:
        """
        Fetch detailed metadata for a paper.
        
        Args:
            paper_id: Identifier for the paper
            
        Returns:
            Paper object with metadata
        """
        await self.initialize()
        
        # Use citation graph builder's method which handles connector selection
        citation_builder = self._pipelines["citation_graph_builder"]
        paper = await citation_builder._get_paper_metadata(paper_id)
        
        if not paper:
            raise ValueError(f"Paper not found: {paper_id}")
            
        return paper
        
    async def download_fulltext(self, paper_id: str) -> bytes:
        """
        Download the full text PDF for a paper.
        
        Args:
            paper_id: Identifier for the paper
            
        Returns:
            PDF content as bytes
        """
        await self.initialize()
        
        # Get the paper metadata first
        paper = await self.fetch_paper_metadata(paper_id)
        
        # Use the fulltext fetcher to download
        fetcher = self._pipelines["fulltext_fetcher"]
        pdf_content = await fetcher.download_pdf(paper)
        
        if not pdf_content:
            raise ValueError(f"Full text not available for paper: {paper_id}")
            
        return pdf_content
        
    async def summarize_document(self, document: Union[str, bytes], paper_id: Optional[str] = None) -> PaperSummary:
        """
        Generate a structured summary of a document.
        
        Args:
            document: HTML or text content to summarize
            paper_id: Optional paper ID to attach to the summary
            
        Returns:
            PaperSummary object
        """
        await self.initialize()
        
        # If document is PDF (bytes), extract text
        if isinstance(document, bytes):
            fetcher = self._pipelines["fulltext_fetcher"]
            document = await fetcher.extract_text_from_pdf(document)
            
        # If we have a paper_id, get the paper metadata
        paper = None
        if paper_id:
            try:
                paper = await self.fetch_paper_metadata(paper_id)
            except Exception as e:
                logger.warning(f"Error fetching paper metadata for summary: {e}")
                
        # If we don't have paper metadata, create minimal Paper object
        if not paper:
            paper = Paper(
                paper_id=paper_id or "document:unknown",
                title="Unknown Document",
                authors=[],
                source="unknown"
            )
            
        # Use the summarizer to generate a summary
        summarizer = self._pipelines["summarizer"]
        return await summarizer.summarize_paper(paper, document)
        
    async def annotate_highlights(self, document: Union[str, bytes], paper_id: Optional[str] = None) -> Annotation:
        """
        Highlight key sentences and extract keywords from a document.
        
        Args:
            document: HTML or text content to annotate
            paper_id: Optional paper ID to attach to the annotations
            
        Returns:
            Annotation object
        """
        await self.initialize()
        
        # If document is PDF (bytes), extract text
        if isinstance(document, bytes):
            fetcher = self._pipelines["fulltext_fetcher"]
            document = await fetcher.extract_text_from_pdf(document)
            
        # If we have a paper_id, get the paper metadata
        paper = None
        if paper_id:
            try:
                paper = await self.fetch_paper_metadata(paper_id)
            except Exception as e:
                logger.warning(f"Error fetching paper metadata for annotation: {e}")
                
        # If we don't have paper metadata, create minimal Paper object
        if not paper:
            paper = Paper(
                paper_id=paper_id or "document:unknown",
                title="Unknown Document",
                authors=[],
                source="unknown"
            )
            
        # Use the summarizer to generate annotations
        summarizer = self._pipelines["summarizer"]
        annotations_dict = await summarizer.annotate_paper(paper, document)
        
        # Convert to Annotation object
        return Annotation(
            paper_id=annotations_dict["paper_id"],
            highlights=annotations_dict["highlights"],
            keywords=annotations_dict["keywords"]
        )
        
    async def get_citation_graph(self, paper_ids: List[str], depth: int = 1) -> CitationGraph:
        """
        Build a citation graph for one or more papers.
        
        Args:
            paper_ids: List of paper identifiers
            depth: How many levels of citations to include
            
        Returns:
            CitationGraph object
        """
        await self.initialize()
        
        # Use the citation graph builder
        graph_builder = self._pipelines["citation_graph_builder"]
        return await graph_builder.build_citation_graph(
            paper_ids, 
            depth=depth,
            max_citations=20,  # TODO: Make configurable
            direction="both"    # TODO: Make configurable
        )
        
    async def store_to_drive(self, document: bytes, folder_id: Optional[str] = None, paper_id: Optional[str] = None) -> str:
        """
        Save a document to Google Drive.
        
        Args:
            document: Document content (PDF)
            folder_id: Optional folder ID to store in
            paper_id: Optional paper ID to use for metadata and organization
            
        Returns:
            Drive link to the stored document
        """
        await self.initialize()
        
        drive_connector = self._connectors["drive"]
        
        # Authenticate if not already done
        await drive_connector.ensure_authenticated()
        
        # If we have a paper_id, get the paper metadata for better naming
        paper = None
        if paper_id:
            try:
                paper = await self.fetch_paper_metadata(paper_id)
            except Exception as e:
                logger.warning(f"Error fetching paper metadata for Drive storage: {e}")
                
        # Store based on whether we have paper metadata
        if paper:
            # Store as a research paper with the paper's metadata
            drive_doc = await drive_connector.store_paper(paper, document)
            return drive_doc.web_view_link
        else:
            # Store as a generic document
            filename = "document.pdf"
            
            # Create folder if needed
            if not folder_id:
                folder_id = await drive_connector.find_or_create_folder("Deep Research Documents")
                
            # Store the document
            drive_doc = await drive_connector.store_document(
                content=document,
                filename=filename,
                mime_type="application/pdf",
                folder_id=folder_id
            )
            
            return drive_doc.web_view_link
            
    async def search_across_sources(self, query: str, sources: List[str], max_results: int = 5) -> Dict[str, Any]:
        """
        Search across multiple scholarly sources with a single query.
        
        Args:
            query: The search query text
            sources: List of sources to search
            max_results: Maximum number of results per source
            
        Returns:
            Dictionary with results from each source
        """
        await self.initialize()
        
        # Create tasks for each source
        tasks = {}
        for source in sources:
            if source in self._connectors:
                connector = self._connectors[source]
                search_query = SearchQuery(query=query, max_results=max_results)
                tasks[source] = asyncio.create_task(connector.search(search_query))
        
        # Wait for all tasks to complete
        results = {}
        for source, task in tasks.items():
            try:
                papers = await task
                # Convert papers to serializable format
                papers_json = []
                for paper in papers:
                    papers_json.append({
                        "paper_id": paper.paper_id,
                        "title": paper.title,
                        "authors": [a.name for a in paper.authors],
                        "abstract": paper.abstract[:200] + "..." if paper.abstract and len(paper.abstract) > 200 else paper.abstract,
                        "url": paper.url,
                        "source": paper.source
                    })
                results[source] = {
                    "status": "success",
                    "count": len(papers),
                    "papers": papers_json
                }
            except Exception as e:
                results[source] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "query": query,
            "results": results
        } 