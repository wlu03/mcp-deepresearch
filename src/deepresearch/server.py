import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
import base64
import io

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio

from .orchestration import DeepResearchOrchestrator
from .models import SearchQuery, Paper, PaperSummary

logger = logging.getLogger(__name__)

# Store notes as a simple key-value dict to demonstrate state management
notes: dict[str, str] = {}

# Create the MCP server
server = Server("deepresearch")

# Create the orchestrator
orchestrator = DeepResearchOrchestrator()

# Helper function to get the orchestrator
def get_orchestrator():
    """Get the global orchestrator instance."""
    return orchestrator

# Configure the server with the available tools
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List the deep research tools available in this MCP server."""
    return [
        types.Tool(
            name="search_papers",
            description="Search multiple scholarly sources for papers matching a query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "sources": {"type": "array", "items": {"type": "string", "enum": ["arxiv", "pubmed", "semanticscholar", "googlescholar"]}, "description": "Sources to search (default: all)"},
                    "max_results": {"type": "integer", "description": "Maximum number of results to return (default: 20)"},
                    "sort_by": {"type": "string", "enum": ["relevance", "date", "citations"], "description": "Sorting criteria (default: relevance)"}
                },
                "required": ["query"]
            },
        ),
        types.Tool(
            name="fetch_paper_metadata",
            description="Fetch detailed metadata (title, authors, abstract) for a given paper ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "Paper identifier (e.g., 'arxiv:2104.08935', 'pubmed:12345678')"}
                },
                "required": ["paper_id"]
            },
        ),
        types.Tool(
            name="download_fulltext",
            description="Retrieve or download the PDF/HTML full text for a given paper ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "Paper identifier (e.g., 'arxiv:2104.08935', 'pubmed:12345678')"}
                },
                "required": ["paper_id"]
            },
        ),
        types.Tool(
            name="summarize_document",
            description="Generate a structured summary (background, methods, results, conclusions).",
            inputSchema={
                "type": "object",
                "properties": {
                    "document": {"type": "string", "description": "Document text or base64-encoded PDF content"},
                    "content_type": {"type": "string", "enum": ["text", "pdf"], "description": "Type of content provided (default: text)"},
                    "paper_id": {"type": "string", "description": "Optional paper ID for additional context"}
                },
                "required": ["document"]
            },
        ),
        types.Tool(
            name="annotate_highlights",
            description="Highlight key sentences and extract keywords from a document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document": {"type": "string", "description": "Document text or base64-encoded PDF content"},
                    "content_type": {"type": "string", "enum": ["text", "pdf"], "description": "Type of content provided (default: text)"},
                    "paper_id": {"type": "string", "description": "Optional paper ID for additional context"}
                },
                "required": ["document"]
            },
        ),
        types.Tool(
            name="get_citation_graph",
            description="Return citation relationships for a given paper or set of papers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_ids": {"type": "array", "items": {"type": "string"}, "description": "List of paper identifiers"},
                    "depth": {"type": "integer", "description": "Depth of citation graph (1 = direct citations only, default: 1)"}
                },
                "required": ["paper_ids"]
            },
        ),
        types.Tool(
            name="store_to_drive",
            description="Save fetched PDFs and summaries to the user's Google Drive folder.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document": {"type": "string", "description": "Base64-encoded PDF content"},
                    "folder_id": {"type": "string", "description": "Optional Google Drive folder ID to store in"},
                    "paper_id": {"type": "string", "description": "Optional paper ID for better organization and naming"}
                },
                "required": ["document"]
            },
        ),
        types.Tool(
            name="search_apis",
            description="Search across multiple scholarly API sources with a single query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query text"},
                    "sources": {"type": "array", "items": {"type": "string", "enum": ["arxiv", "pubmed", "semanticscholar", "googlescholar"]}, "description": "List of sources to search (options: 'arxiv', 'pubmed', 'semanticscholar', 'googlescholar')"},
                    "max_results": {"type": "integer", "description": "Maximum number of results to return per source"}
                },
                "required": ["query"]
            },
        ),
        types.Tool(
            name="test_api_connector",
            description="Test a specific API connector and return diagnostics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "connector": {"type": "string", "enum": ["arxiv", "pubmed", "semanticscholar", "googlescholar", "drive"], "description": "The connector to test"},
                    "query": {"type": "string", "description": "Search query to use for testing"},
                    "max_results": {"type": "integer", "description": "Maximum number of results to return"}
                },
                "required": ["connector"]
            },
        ),
        types.Tool(
            name="download_paper",
            description="Download a paper by its ID from the appropriate source.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "The ID of the paper (e.g., 'arxiv:2312.12345', 'pubmed:12345678', etc.)"},
                    "save_directory": {"type": "string", "description": "Directory to save the PDF"}
                },
                "required": ["paper_id"]
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    if not arguments:
        arguments = {}
        
    try:
        # Handle each tool
        if name == "search_papers":
            query = arguments.get("query")
            sources = arguments.get("sources", ["arxiv", "pubmed", "semanticscholar"])
            max_results = arguments.get("max_results", 20)
            sort_by = arguments.get("sort_by", "relevance")
            
            search_query = SearchQuery(
                query=query,
                sources=sources,
                max_results=max_results,
                sort_by=sort_by
            )
            
            result = await orchestrator.search_papers(search_query)
            
            # Convert to JSON-serializable format
            papers_json = []
            for paper in result.papers:
                papers_json.append({
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "authors": [{"name": a.name} for a in paper.authors],
                    "abstract": paper.abstract,
                    "url": paper.url,
                    "publication_date": paper.publication_date.isoformat() if paper.publication_date else None,
                    "journal": paper.journal,
                    "source": paper.source,
                    "citations_count": paper.citations_count
                })
                
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "query": result.query,
                        "papers": papers_json,
                        "total_found": result.total_found
                    }, indent=2)
                )
            ]
            
        elif name == "fetch_paper_metadata":
            paper_id = arguments.get("paper_id")
            if not paper_id:
                raise ValueError("paper_id is required")
                
            paper = await orchestrator.fetch_paper_metadata(paper_id)
            
            # Convert to JSON-serializable format
            paper_json = {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "authors": [{"name": a.name, "affiliation": a.affiliation} for a in paper.authors],
                "abstract": paper.abstract,
                "url": paper.url,
                "pdf_url": paper.pdf_url,
                "publication_date": paper.publication_date.isoformat() if paper.publication_date else None,
                "journal": paper.journal,
                "doi": paper.doi,
                "source": paper.source,
                "citations_count": paper.citations_count
            }
                
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(paper_json, indent=2)
                )
            ]
            
        elif name == "download_fulltext":
            paper_id = arguments.get("paper_id")
            if not paper_id:
                raise ValueError("paper_id is required")
                
            pdf_content = await orchestrator.download_fulltext(paper_id)
            
            # Return as embedded resource
            return [
                types.EmbeddedResource(
                    uri=AnyUrl("paper://pdf/" + paper_id),
                    name=f"PDF for {paper_id}",
                    description=f"PDF full text of {paper_id}",
                    data=base64.b64encode(pdf_content).decode('ascii'),
                    mimeType="application/pdf"
                )
            ]
            
        elif name == "summarize_document":
            document = arguments.get("document")
            if not document:
                raise ValueError("document is required")
                
            content_type = arguments.get("content_type", "text")
            paper_id = arguments.get("paper_id")
            
            # Convert document to appropriate format
            if content_type == "pdf":
                try:
                    document = base64.b64decode(document)
                except Exception as e:
                    raise ValueError(f"Invalid base64-encoded PDF: {str(e)}")
                    
            summary = await orchestrator.summarize_document(document, paper_id)
            
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "paper_id": summary.paper_id,
                        "background": summary.background,
                        "methods": summary.methods,
                        "results": summary.results,
                        "conclusions": summary.conclusions
                    }, indent=2)
                )
            ]
            
        elif name == "annotate_highlights":
            document = arguments.get("document")
            if not document:
                raise ValueError("document is required")
                
            content_type = arguments.get("content_type", "text")
            paper_id = arguments.get("paper_id")
            
            # Convert document to appropriate format
            if content_type == "pdf":
                try:
                    document = base64.b64decode(document)
                except Exception as e:
                    raise ValueError(f"Invalid base64-encoded PDF: {str(e)}")
                    
            annotation = await orchestrator.annotate_highlights(document, paper_id)
            
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "paper_id": annotation.paper_id,
                        "highlights": annotation.highlights,
                        "keywords": annotation.keywords
                    }, indent=2)
                )
            ]
            
        elif name == "get_citation_graph":
            paper_ids = arguments.get("paper_ids", [])
            if not paper_ids:
                raise ValueError("paper_ids is required and must not be empty")
                
            depth = arguments.get("depth", 1)
            
            citation_graph = await orchestrator.get_citation_graph(paper_ids, depth)
            
            # Convert to JSON-serializable format
            nodes_json = []
            for paper in citation_graph.nodes:
                nodes_json.append({
                    "id": paper.paper_id,
                    "title": paper.title,
                    "authors": [a.name for a in paper.authors],
                    "journal": paper.journal,
                    "year": paper.publication_date.year if paper.publication_date else None,
                    "source": paper.source
                })
                
            links_json = []
            for link in citation_graph.links:
                links_json.append({
                    "source": link.source_id,
                    "target": link.target_id
                })
                
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "nodes": nodes_json,
                        "links": links_json
                    }, indent=2)
                )
            ]
            
        elif name == "store_to_drive":
            document = arguments.get("document")
            if not document:
                raise ValueError("document is required")
                
            folder_id = arguments.get("folder_id")
            paper_id = arguments.get("paper_id")
            
            # Decode the PDF
            try:
                pdf_content = base64.b64decode(document)
            except Exception as e:
                raise ValueError(f"Invalid base64-encoded PDF: {str(e)}")
                
            drive_link = await orchestrator.store_to_drive(pdf_content, folder_id, paper_id)
            
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "drive_link": drive_link
                    }, indent=2)
                )
            ]
        
        elif name == "search_apis":
            query = arguments.get("query")
            if not query:
                raise ValueError("query is required")
                
            sources = arguments.get("sources", ["arxiv", "pubmed", "semanticscholar", "googlescholar"])
            max_results = arguments.get("max_results", 5)
            
            result = await orchestrator.search_across_sources(query, sources, max_results)
            
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]
            
        elif name == "test_api_connector":
            connector = arguments.get("connector")
            if not connector:
                raise ValueError("connector is required")
                
            query = arguments.get("query", "machine learning")
            max_results = arguments.get("max_results", 3)
            
            import asyncio
            import sys
            import os
            from pathlib import Path
            import aiohttp
            
            results = {
                "connector": connector,
                "status": "unknown",
                "papers_found": 0,
                "errors": [],
                "messages": []
            }
            
            async def run_test():
                try:
                    # Set up session
                    async with aiohttp.ClientSession() as session:
                        # Get the appropriate connector
                        if connector == "arxiv":
                            from deepresearch.connectors import ArXivConnector
                            api = ArXivConnector(session)
                        elif connector == "pubmed":
                            from deepresearch.connectors import PubMedConnector
                            api = PubMedConnector(session)
                        elif connector == "semanticscholar":
                            from deepresearch.connectors import SemanticScholarConnector
                            api_key = os.environ.get("SEMANTICSCHOLAR_API_KEY")
                            api = SemanticScholarConnector(session, api_key=api_key)
                        elif connector == "googlescholar":
                            from deepresearch.connectors import GoogleScholarConnector
                            api = GoogleScholarConnector(session)
                        elif connector == "drive":
                            from deepresearch.connectors import GoogleDriveConnector
                            results["status"] = "skipped"
                            results["messages"].append("Drive connector requires OAuth setup - skipping automated test")
                            return
                        else:
                            results["status"] = "error"
                            results["errors"].append(f"Unknown connector: {connector}")
                            return
                        
                        # Test search
                        from deepresearch.models import SearchQuery
                        search_results = await api.search(SearchQuery(query=query, max_results=max_results))
                        
                        results["papers_found"] = len(search_results)
                        results["messages"].append(f"Found {len(search_results)} papers")
                        
                        # Get paper details for the first result if available
                        if search_results:
                            paper = search_results[0]
                            results["messages"].append(f"First paper: {paper.title}")
                            results["messages"].append(f"Authors: {', '.join(a.name for a in paper.authors)}")
                            
                            # Test metadata retrieval
                            try:
                                paper_id = paper.paper_id
                                metadata = await api.get_paper_metadata(paper_id)
                                results["messages"].append(f"Successfully retrieved metadata for {paper_id}")
                            except Exception as e:
                                results["errors"].append(f"Metadata retrieval error: {str(e)}")
                        
                        results["status"] = "success" if not results["errors"] else "partial_success"
                                
                except Exception as e:
                    results["status"] = "error"
                    results["errors"].append(f"Test failed: {str(e)}")
            
            await run_test()
            
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(results, indent=2)
                )
            ]
            
        elif name == "download_paper":
            paper_id = arguments.get("paper_id")
            if not paper_id:
                raise ValueError("paper_id is required")
                
            save_directory = arguments.get("save_directory", "downloads")
            
            import asyncio
            import aiohttp
            from pathlib import Path
            
            result = {
                "paper_id": paper_id,
                "status": "unknown",
                "filename": None,
                "error": None
            }
            
            save_dir = Path(save_directory)
            save_dir.mkdir(exist_ok=True)
            
            async def perform_download():
                try:
                    async with aiohttp.ClientSession() as session:
                        # Determine source type from paper_id
                        source_type = paper_id.split(":", 1)[0] if ":" in paper_id else None
                        
                        if source_type == "arxiv":
                            from deepresearch.connectors import ArXivConnector
                            connector = ArXivConnector(session)
                        elif source_type == "pubmed":
                            from deepresearch.connectors import PubMedConnector
                            connector = PubMedConnector(session)
                        elif source_type == "semanticscholar":
                            from deepresearch.connectors import SemanticScholarConnector
                            api_key = os.environ.get("SEMANTICSCHOLAR_API_KEY")
                            connector = SemanticScholarConnector(session, api_key=api_key)
                        elif source_type == "googlescholar":
                            from deepresearch.connectors import GoogleScholarConnector
                            connector = GoogleScholarConnector(session)
                        else:
                            result["status"] = "error"
                            result["error"] = f"Unknown source type for ID: {paper_id}"
                            return
                        
                        # Get metadata first for filename
                        paper = await connector.get_paper_metadata(paper_id)
                        
                        # Download fulltext
                        pdf_data = await connector.download_fulltext(paper_id)
                        
                        # Create clean filename
                        clean_id = paper_id.replace(":", "_").replace("/", "_")
                        clean_title = ''.join(c if c.isalnum() or c in [' ', '.', '-', '_'] else '_' for c in paper.title)
                        filename = f"{clean_id}_{clean_title[:50]}.pdf"
                        filepath = save_dir / filename
                        
                        # Save file
                        with open(filepath, "wb") as f:
                            f.write(pdf_data)
                        
                        result["status"] = "success"
                        result["filename"] = str(filepath)
                        
                except Exception as e:
                    result["status"] = "error"
                    result["error"] = str(e)
            
            await perform_download()
            
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Error executing tool {name}: {str(e)}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e)
                }, indent=2)
            )
        ]

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> Union[str, bytes]:
    """
    Read a specific resource by its URI.
    This handles resources like PDFs that were generated by tools.
    """
    if uri.scheme != "paper":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

    # Handle paper PDFs
    if uri.path.startswith("/pdf/"):
        paper_id = uri.path[5:]  # Remove "/pdf/" prefix
        try:
            pdf_content = await orchestrator.download_fulltext(paper_id)
            return pdf_content
        except Exception as e:
            raise ValueError(f"Error fetching PDF: {str(e)}")
            
    raise ValueError(f"Resource not found: {uri}")

# Define the prompt templates
@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    These are specialized prompts for research workflows.
    """
    return [
        types.Prompt(
            name="research_assistant",
            description="Ask a research assistant to help with scholarly papers",
            arguments=[
                types.PromptArgument(
                    name="topic",
                    description="Research topic or query",
                    required=True
                ),
                types.PromptArgument(
                    name="detail_level",
                    description="Level of detail (basic/comprehensive)",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="citation_analyzer",
            description="Analyze the citation graph and relationships of papers",
            arguments=[
                types.PromptArgument(
                    name="paper_ids",
                    description="Paper IDs to analyze, comma-separated",
                    required=True
                ),
                types.PromptArgument(
                    name="analysis_focus",
                    description="Focus of the analysis (influence, trends, gaps)",
                    required=False
                )
            ]
        )
    ]

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """
    Generate a prompt by combining arguments with server capabilities.
    """
    if not arguments:
        arguments = {}
        
    if name == "research_assistant":
        topic = arguments.get("topic", "")
        detail_level = arguments.get("detail_level", "basic")
        
        is_comprehensive = detail_level.lower() == "comprehensive"
        
        prompt = f"""You are a research assistant with access to scholarly databases including arXiv, PubMed, Semantic Scholar, and Google Scholar.

I'm researching the topic: {topic}

Please help me by:
1. Searching for the most relevant and recent papers on this topic
2. Providing a summary of the key findings and research directions
"""

        if is_comprehensive:
            prompt += """3. Analyzing the relationships between key papers
4. Identifying gaps and suggesting future research directions
5. Recommending specific papers I should read in detail

For the most important papers, please fetch their full details and provide a structured summary of their key contributions.
"""
        else:
            prompt += """3. Highlighting 3-5 key papers that are essential reading

Please focus on quality over quantity in your recommendations.
"""
            
        return types.GetPromptResult(
            description="Research assistant prompt",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=prompt
                    )
                )
            ]
        )
        
    elif name == "citation_analyzer":
        paper_ids = arguments.get("paper_ids", "")
        analysis_focus = arguments.get("analysis_focus", "influence")
        
        paper_ids_list = [p.strip() for p in paper_ids.split(",")]
        
        if analysis_focus == "influence":
            focus_desc = "influential these papers have been in their field"
        elif analysis_focus == "trends":
            focus_desc = "research trends these papers represent"
        elif analysis_focus == "gaps":
            focus_desc = "research gaps and opportunities suggested by these papers"
        else:
            focus_desc = "relationships between these papers"
            
        prompt = f"""You are a citation analysis expert with access to citation databases and full text of scholarly papers.

Please analyze the following paper(s):

{', '.join(paper_ids_list)}

I'd like to understand how {focus_desc}.

Please:
1. Fetch the citation graph for these papers
2. Analyze the key relationships and patterns
3. Identify the most important connected papers
4. Visualize the citation network if possible
5. Summarize your findings with specific recommendations for further reading

Please be specific in your analysis, citing paper titles and authors when relevant.
"""

        return types.GetPromptResult(
            description="Citation analyzer prompt",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=prompt
                    )
                )
            ]
        )
        
    else:
        raise ValueError(f"Unknown prompt: {name}")

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        try:
            # Initialize the orchestrator
            await orchestrator.initialize()
            
            # Run the server
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="deepresearch",
                    server_version="1",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
        finally:
            # Ensure we clean up resources
            await orchestrator.shutdown()
            
if __name__ == "__main__":
    asyncio.run(main())