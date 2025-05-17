# Deep Research MCP Server

An advanced scholarly research MCP server that provides a uniform set of tools for discovering, fetching, processing, and managing scholarly content across multiple sources.

## Overview

Deep Research is a Model Context Protocol (MCP) server that enables AI assistants like Claude to access and process scholarly literature from multiple sources, generate summaries, analyze citation networks, extract relationships between concepts, and more.

## Scholarly Sources

The server integrates with multiple academic repositories:
- arXiv
- PubMed 
- Semantic Scholar
- Google Scholar
- Google Drive (for document storage) (wip, annoying to setup)

## Core Capabilities

- **Cross-source paper search**: Find papers across multiple repositories with a single query
- **Full-text retrieval**: Download and process complete academic papers
- **AI-powered analysis**: Generate structured summaries, highlight key information, and extract relationships
- **Citation network analysis**: Build and explore citation graphs
- **Document management**: Store research papers and notes to Google Drive

## MCP Tools

### Paper Search and Retrieval

#### `search_papers`
Search multiple scholarly sources for papers matching a query.
- Required: `query` - Search query text
- Optional: `sources` - List of sources to search (default: all)
- Optional: `max_results` - Maximum number of results (default: 20)
- Optional: `sort_by` - Sorting criteria (default: relevance)

#### `fetch_paper_metadata`
Fetch detailed metadata for a given paper ID.
- Required: `paper_id` - Paper identifier (e.g., 'arxiv:2104.08935')

#### `download_fulltext`
Retrieve or download the PDF full text for a given paper ID.
- Required: `paper_id` - Paper identifier

### Content Processing

#### `summarize_document`
Generate a structured summary (background, methods, results, conclusions).
- Required: `document` - Document text or base64-encoded PDF content
- Optional: `content_type` - Type of content provided (default: text)
- Optional: `paper_id` - Paper ID for additional context

#### `annotate_highlights`
Highlight key sentences and extract keywords from a document.
- Required: `document` - Document text or base64-encoded PDF content
- Optional: `content_type` - Type of content provided (default: text)
- Optional: `paper_id` - Paper ID for additional context

#### `extract_relations`
Extract relationships between concepts in a scholarly paper.
- Required: `paper_id` - Paper identifier

#### `summarize_section`
Generate a focused summary of a specific section in a scholarly paper.
- Required: `document` - Document content (text or base64-encoded PDF)
- Required: `section_name` - Name of the section to summarize
- Optional: `content_type` - Type of content provided (default: text)
- Optional: `paper_id` - Paper ID for additional context

#### `compare_papers`
Compare multiple scholarly papers to highlight similarities and differences.
- Required: `paper_ids` - List of paper identifiers to compare
- Optional: `abstracts_only` - Whether to use only abstracts (default: false)

### Citation Analysis

#### `get_citation_graph`
Return citation relationships for a given paper or set of papers.
- Required: `paper_ids` - List of paper identifiers
- Optional: `depth` - Depth of citation graph (default: 1)
- Optional: `max_citations` - Maximum number of citations to return (default: 20)
- Optional: `direction` - Direction of citation relationships (default: both)

#### `analyze_trends`
Analyze publication trends over time, identify emerging topics, and plot term frequencies.
- Required: `query` - Search query to find papers for trend analysis
- Optional: `max_papers` - Maximum number of papers to analyze (default: 100)

### Storage

#### `store_to_drive`
Save fetched PDFs and summaries to Google Drive.
- Required: `document` - Base64-encoded PDF content
- Optional: `folder_id` - Google Drive folder ID to store in
- Optional: `paper_id` - Paper ID for better organization

### API Testing Tools

#### `search_apis`
Search across multiple scholarly API sources with a single query.
- Required: `query` - The search query text
- Optional: `sources` - List of sources to search
- Optional: `max_results` - Maximum number of results to return per source

#### `test_api_connector`
Test a specific API connector and return diagnostics.
- Required: `connector` - The connector to test
- Optional: `query` - Search query to use for testing
- Optional: `max_results` - Maximum number of results to return

#### `download_paper`
Download a paper by its ID from the appropriate source.
- Required: `paper_id` - The ID of the paper
- Optional: `save_directory` - Directory to save the PDF

## Specialized MCP Prompts

### `research_assistant`
Ask a research assistant to help with scholarly papers.
- Required: `topic` - Research topic or query
- Optional: `detail_level` - Level of detail (basic/comprehensive)

### `citation_analyzer`
Analyze the citation graph and relationships of papers.
- Required: `paper_ids` - Paper IDs to analyze, comma-separated
- Optional: `analysis_focus` - Focus of the analysis (influence, trends, gaps)

## Advanced Features

### Concept Relationship Extraction
Extract explicit relationships between concepts mentioned in scientific papers:
- Causal relationships (X causes Y, X inhibits Y)
- Comparative relationships (Algorithm A outperforms B)
- Correlative relationships (X is associated with Y)
- Compositional relationships (X consists of Y)

### Section-Specific Paper Summarization
Generate focused summaries of specific sections in a scholarly paper:
- Target individual sections (Introduction, Methods, Results, Discussion)
- Get detailed summaries that focus on the specific content of that section

### Paper Comparison Tool
Compare multiple papers to highlight similarities and differences across:
- Research questions and goals
- Methodologies and approaches
- Key findings and results
- Limitations of each study
- Future directions suggested by the authors

### Publication Trend Analysis
Analyze research trends across the literature:
- Track publication volume over time
- Identify emerging topics via n-gram frequency analysis
- Find frequent authors in the research area
- Analyze distribution of papers across sources
- Discover term frequencies to understand key concepts


## Installation & Setup

### Installation

First, clone this repository and install the package:

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-deepresearch.git
cd mcp-deepresearch

# Install the package in development mode
pip install -e .
```

### Configuration

The server requires configuration for API keys and credentials:

1. For Google Drive integration:
   - Create a `deepresearch_credentials.json` file with your Google API credentials
   - The first time you use Drive features, it will prompt for authentication

2. For API rate limits:
   - Some sources (especially Google Scholar) may require proxies for high-volume usage

### Starting the Server

You can run the server in two ways:

1. Using the Python module:
```bash
python -m deepresearch
```

2. Using the start_server script:
```bash
python start_server.py
```

### Connecting to Claude Desktop

To use the server with Claude Desktop:

1. Edit the Claude Desktop configuration file (located at `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
    "mcpServers": {
        "deepresearch": {
            "command": "/path/to/python3",
            "args": [
                "-m",
                "deepresearch"
            ],
            "workingDir": "/path/to/mcp-deepresearch"
        }
    }
}
```

2. Replace `/path/to/python3` with the path to your Python executable
3. Replace `/path/to/mcp-deepresearch` with the absolute path to your project
4. Restart Claude Desktop
5. Select "deepresearch" from the MCP server dropdown in Claude Desktop

## Example Usage

Here's how you might use this MCP server with Claude:

1. Search for papers on a topic:
   ```
   @deepresearch search_papers(query="Transformer protein folding")
   ```

2. Fetch metadata and download a paper:
   ```
   @deepresearch fetch_paper_metadata(paper_id="arxiv:2106.14843")
   @deepresearch download_fulltext(paper_id="arxiv:2106.14843")
   ```

3. Generate a summary:
   ```
   @deepresearch summarize_document(document=<pdf content>, content_type="pdf")
   ```

4. Extract relationships:
   ```
   @deepresearch extract_relations(paper_id="arxiv:2106.14843")
   ```

5. Analyze citation network:
   ```
   @deepresearch get_citation_graph(paper_ids=["arxiv:2106.14843"], depth=2)
   ```

6. Compare papers:
   ```
   @deepresearch compare_papers(paper_ids=["arxiv:2106.14843", "arxiv:2103.12116"])
   ```

7. Save to Google Drive:
   ```
   @deepresearch store_to_drive(document=<pdf content>, paper_id="arxiv:2106.14843")
   ```

## Debugging

You can debug the server using the Model Context Protocol Inspector:

```bash
npx @anthropic-ai/mcp-inspector@latest
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

## Connector Testing

The project includes several test scripts for validating the functionality of connectors:

1. `test_connectors.py`: Basic validation for all connectors
2. `test_connectors_download.py`: Enhanced version for the full search-to-download pipeline
3. `test_google_scholar_fix.py`: Specialized test for the Google Scholar connector 
4. `test_semantic_scholar_direct.py`: Direct test for Semantic Scholar API

### Common Issues and Solutions

1. **Google Scholar**:
   - PDF download limitations are addressed by extracting ArXiv IDs for papers also hosted on ArXiv

2. **Semantic Scholar**:
   - Rate limiting issues are handled with API keys and retry logic

3. **General Connectivity**:
   - Use `--connector` parameter to test specific connectors
   - For detailed debugging, use specialized test scripts

## Contributing

For contributions, please follow these guidelines:
1. Create a feature branch for new development
2. Add unit tests for new functionality
3. Ensure existing tests pass
4. Submit a pull request with detailed description

## License

This project is released under the MIT License. See the LICENSE file for details. 