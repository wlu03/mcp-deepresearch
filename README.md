# Deep Research MCP Server

An advanced scholarly research MCP server that provides a uniform set of tools for discovering, fetching, processing, and managing scholarly content across multiple sources.

## Features

The server integrates with multiple scholarly sources:
- arXiv
- PubMed 
- Semantic Scholar
- Google Scholar
- Google Drive (for document storage)

And provides powerful research tools:
- Cross-source paper search
- Full-text document retrieval
- Structured summaries of papers
- Key sentence highlighting and keyword extraction
- Citation graph generation
- Google Drive integration for document storage

## Tools

The MCP server provides the following tools:

### `search_papers`
Search multiple scholarly sources for papers matching a query.
- Required: `query` - Search query text
- Optional: `sources` - List of sources to search (default: all)
- Optional: `max_results` - Maximum number of results (default: 20)
- Optional: `sort_by` - Sorting criteria (default: relevance)

### `fetch_paper_metadata`
Fetch detailed metadata for a given paper ID.
- Required: `paper_id` - Paper identifier (e.g., 'arxiv:2104.08935')

### `download_fulltext`
Retrieve or download the PDF full text for a given paper ID.
- Required: `paper_id` - Paper identifier

### `summarize_document`
Generate a structured summary (background, methods, results, conclusions).
- Required: `document` - Document text or base64-encoded PDF content
- Optional: `content_type` - Type of content provided (default: text)
- Optional: `paper_id` - Paper ID for additional context

### `annotate_highlights`
Highlight key sentences and extract keywords from a document.
- Required: `document` - Document text or base64-encoded PDF content
- Optional: `content_type` - Type of content provided (default: text)
- Optional: `paper_id` - Paper ID for additional context

### `get_citation_graph`
Return citation relationships for a given paper or set of papers.
- Required: `paper_ids` - List of paper identifiers
- Optional: `depth` - Depth of citation graph (default: 1)

### `store_to_drive`
Save fetched PDFs and summaries to the user's Google Drive folder.
- Required: `document` - Base64-encoded PDF content
- Optional: `folder_id` - Google Drive folder ID to store in
- Optional: `paper_id` - Paper ID for better organization

## Prompts

The server also provides specialized prompts for research workflows:

### `research_assistant`
Ask a research assistant to help with scholarly papers.
- Required: `topic` - Research topic or query
- Optional: `detail_level` - Level of detail (basic/comprehensive)

### `citation_analyzer`
Analyze the citation graph and relationships of papers.
- Required: `paper_ids` - Paper IDs to analyze, comma-separated
- Optional: `analysis_focus` - Focus of the analysis (influence, trends, gaps)

## Configuration

The server requires configuration for API keys and credentials:

1. For Google Drive integration:
   - Create a `deepresearch_credentials.json` file with your Google API credentials
   - The first time you use Drive features, it will prompt for authentication

2. For API rate limits:
   - Some sources (especially Google Scholar) may require proxies for high-volume usage

## Quickstart

### Install

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  
  ```
  "mcpServers": {
    "deepresearch": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/wesleylu/Desktop/mcp-deepresearch/deepresearch",
        "run",
        "deepresearch"
      ]
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  
  ```
  "mcpServers": {
    "deepresearch": {
      "command": "uvx",
      "args": [
        "deepresearch"
      ]
    }
  }
  ```
</details>

## Development

### Building and Publishing

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

2. Build package distributions:
```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

3. Publish to PyPI:
```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:
- Token: `--token` or `UV_PUBLISH_TOKEN`
- Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).


You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /Users/wesleylu/Desktop/mcp-deepresearch/deepresearch run deepresearch
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

## Example Usage

Here's how you might use this MCP server with Claude:

1. First, search for papers on a topic:
   ```
   @deepresearch search_papers(query="Transformer protein folding")
   ```

2. Fetch detailed metadata for an interesting paper:
   ```
   @deepresearch fetch_paper_metadata(paper_id="arxiv:2106.14843")
   ```

3. Download and get a structured summary:
   ```
   @deepresearch download_fulltext(paper_id="arxiv:2106.14843")
   @deepresearch summarize_document(document=<pdf content>, content_type="pdf")
   ```

4. Explore the citation network:
   ```
   @deepresearch get_citation_graph(paper_ids=["arxiv:2106.14843"], depth=2)
   ```

5. Save to Google Drive:
   ```
   @deepresearch store_to_drive(document=<pdf content>, paper_id="arxiv:2106.14843")
   ```

## Model Context Protocol (MCP) Tools

The Deep Research MCP Server exposes the following tools:

### Paper Search and Retrieval

* `search_papers`: Search for papers across multiple scholarly sources
* `fetch_paper_metadata`: Get detailed information about a specific paper
* `download_fulltext`: Download the full text PDF of a paper

### Content Processing

* `summarize_document`: Generate a structured summary of a paper
* `annotate_highlights`: Extract key sentences from a paper
* `get_citation_graph`: Visualize citation relationships

### Storage

* `store_to_drive`: Save papers and research materials to Google Drive

### API Testing Tools

* `search_apis`: Search across multiple scholarly API sources with a single query
* `test_api_connector`: Test a specific API connector and return diagnostics
* `download_paper`: Download a paper by its ID from the appropriate source

## MCP Prompts

The server also provides specialized prompts:

* `research_assistant`: Specialized prompt for scholarly research assistance
* `citation_analyzer`: Specialized prompt for analyzing citation relationships