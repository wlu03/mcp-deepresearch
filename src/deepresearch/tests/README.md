# Deep Research Connector Tests

This directory contains test scripts for validating the functionality of the Deep Research connectors.

## Available Test Scripts

### 1. test_connectors.py
The original test script for all connectors. Provides basic validation.

### 2. test_connectors_download.py
Enhanced version that downloads PDFs to the `downloads/` directory. Use this to test the complete pipeline from search to download.

### 3. test_google_scholar_fix.py
Specialized test script for the Google Scholar connector with improved debugging and error handling. Includes:
- Direct scholarly module testing
- Connector method inspection
- ArXiv fallback for PDF downloads
- Detailed error reporting

### 4. test_semantic_scholar_direct.py
Direct test for Semantic Scholar API to diagnose connectivity issues.

## Common Issues and Solutions

1. **Google Scholar**:
   - Issue: `TypeError: expected string or bytes-like object, got 'list'`
   - Solution: Fixed in connector by handling both string and list author formats
   - Issue: PDF download limitations
   - Solution: Extract ArXiv IDs for papers that are also hosted on ArXiv

2. **Semantic Scholar**:
   - Issue: Rate limiting and API connectivity
   - Solution: Use API key when available, implement retry logic

3. **General Connectivity**:
   - Use `--connector` parameter to test specific connectors
   - For detailed debugging, use specialized test scripts

## Running Tests

See the main `api_test_instructions.txt` file in the project root for detailed instructions on running these tests.

## Adding New Tests

When adding new tests, follow these guidelines:
1. Create a new test file with a descriptive name
2. Use async/await patterns for all network operations
3. Add proper error handling and debugging information
4. Document the test in this README and in the main test instructions file 