# API Testing Tools for Claude

This document provides information about the API testing tools exposed to Claude through the Model Context Protocol (MCP).

## Available Tools

### 1. search_apis

This tool allows you to search across multiple scholarly API sources with a single query.

```python
search_apis(query: str, 
           sources: List[str] = ["arxiv", "pubmed", "semanticscholar", "googlescholar"], 
           max_results: int = 5) -> Dict[str, Any]
```

**Example:**
```
@deepresearch search_apis(query="large language models", sources=["arxiv", "semanticscholar"], max_results=3)
```

This will return papers from both ArXiv and Semantic Scholar about large language models, with up to 3 results from each source.

### 2. test_api_connector

This tool runs diagnostic tests on a specific API connector and reports the results.

```python
test_api_connector(connector: str, 
                  query: str = "machine learning", 
                  max_results: int = 3) -> Dict[str, Any]
```

**Example:**
```
@deepresearch test_api_connector(connector="arxiv", query="neural networks")
```

This will test the ArXiv connector by performing a search for "neural networks" and attempting to retrieve metadata for the first result.

### 3. download_paper

This tool downloads a paper by its ID from the appropriate source.

```python
download_paper(paper_id: str, 
              save_directory: str = "downloads") -> Dict[str, Any]
```

**Example:**
```
@deepresearch download_paper(paper_id="arxiv:2303.08774")
```

This will download the paper with the specified ArXiv ID and save it to the "downloads" directory.

## Error Handling

All tools return a dictionary with status information. The status field will be one of:
- "success": Operation completed successfully
- "partial_success": Some parts worked but there were errors
- "error": Operation failed
- "unknown": Status could not be determined
- "skipped": Operation was skipped (e.g., when testing Drive without auth)

For errors, check the "errors" list in the result for specific error messages.

## Usage Tips

1. **Specifying Sources**: When using `search_apis`, you can specify which sources to search to save time or focus on specific repositories.

2. **Downloading Papers**: Always check if a paper has a PDF available before attempting to download it. Some papers may only have metadata.

3. **Rate Limiting**: Be aware that some APIs (especially Google Scholar and Semantic Scholar) have rate limits. Spacing out requests can help.

4. **ID Formats**: Different sources use different ID formats:
   - ArXiv: `arxiv:2106.12345`
   - PubMed: `pubmed:34567890`
   - Semantic Scholar: `semanticscholar:corpus_id`
   - Google Scholar: `googlescholar:cluster_id`

5. **Testing Changes**: Use `test_api_connector` after making changes to connector code to verify everything still works.

## Troubleshooting

If you encounter issues with any of the API testing tools:

1. Check the error messages returned in the result
2. Verify the API source is online and responding
3. For Semantic Scholar, try setting an API key
4. For Google Scholar, be aware it may block requests due to rate limiting
5. For ArXiv, check that the paper ID format is correct

Remember that certain APIs may have temporary outages or maintenance windows that can affect availability. 