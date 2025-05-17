import asyncio
import aiohttp
import os
import sys
import argparse
import logging
from datetime import datetime
import pathlib
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("google_scholar_test")

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from deepresearch.connectors import GoogleScholarConnector, ArXivConnector
from deepresearch.models import SearchQuery, Paper

# Create download directory
DOWNLOAD_DIR = pathlib.Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

async def test_google_scholar_search(session, query_text="language model evaluation", max_results=3):
    """Test only the search functionality of Google Scholar connector"""
    print(f"\n=== Testing Google Scholar Search: '{query_text}' ===")
    
    try:
        # Debug instantiation
        print("Creating GoogleScholarConnector...")
        connector = GoogleScholarConnector(session, use_proxy=False)
        print("Connector created successfully")
        
        # Test search with debugging
        print(f"\nPerforming search for '{query_text}'...")
        query = SearchQuery(query=query_text, max_results=max_results)
        
        # Debug the scholarly module directly
        print("Debugging scholarly module...")
        from scholarly import scholarly
        print("Imported scholarly successfully")
        
        # Set up a search query using scholarly directly
        print("Setting up direct scholarly search...")
        try:
            direct_search = scholarly.search_pubs(query_text, patents=False, citations=False)
            print("Direct scholarly search object created")
            
            # Try to get the first result directly
            try:
                print("Trying to fetch first direct result...")
                first_result = next(direct_search)
                print(f"Direct result: {first_result.get('bib', {}).get('title', 'No title')}")
            except StopIteration:
                print("No direct results found")
            except Exception as e:
                print(f"Error getting direct result: {e}")
        except Exception as e:
            print(f"Direct scholarly search error: {e}")
        
        # Now test our connector
        print("\nTesting connector search...")
        papers = await connector.search(query)
        print(f"Search completed, found {len(papers)} papers")
        
        if papers:
            print("Papers found:")
            for i, paper in enumerate(papers, 1):
                print(f"{i}. {paper.title}")
                print(f"   Authors: {', '.join(a.name for a in paper.authors)}")
                print(f"   URL: {paper.url}")
                print(f"   PDF URL: {paper.pdf_url}")
                print(f"   Paper ID: {paper.paper_id}")
                print()
            
            # Try metadata retrieval on first paper
            if papers and papers[0].url and "arxiv.org" in papers[0].url:
                try:
                    # Extract arxiv ID which should work better
                    paper_id = papers[0].paper_id
                    arxiv_id = None
                    if papers[0].url and "arxiv.org" in papers[0].url:
                        arxiv_id_match = re.search(r"arxiv\.org\/(?:abs|pdf)\/([^\/]+)", papers[0].url)
                        if arxiv_id_match:
                            arxiv_id = arxiv_id_match.group(1)
                    
                    if arxiv_id:
                        print(f"\nTesting ArXiv metadata retrieval for arxiv:{arxiv_id}...")
                        arxiv_connector = ArXivConnector(session)
                        paper = await arxiv_connector.get_paper_metadata(f"arxiv:{arxiv_id}")
                        print(f"Retrieved metadata successfully from ArXiv: {paper.title}")
                        
                        # Try PDF download
                        print(f"\nAttempting to download PDF from ArXiv...")
                        pdf_data = await arxiv_connector.download_fulltext(f"arxiv:{arxiv_id}")
                        
                        # Save the PDF
                        clean_id = arxiv_id.replace(":", "_")
                        clean_title = ''.join(c if c.isalnum() or c in [' ', '.', '-', '_'] else '_' for c in paper.title)
                        filename = f"arxiv_{clean_id}_{clean_title[:50]}.pdf"
                        filepath = DOWNLOAD_DIR / filename
                        
                        with open(filepath, "wb") as f:
                            f.write(pdf_data)
                        
                        print(f"Downloaded {len(pdf_data)} bytes of PDF data")
                        print(f"Saved to: {filepath}")
                except Exception as e:
                    print(f"ArXiv test error: {e}")
                    print(f"Error type: {type(e).__name__}")
        else:
            print("No papers found")
                
    except Exception as e:
        print(f"Error in test: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Print traceback for more detailed debugging
        import traceback
        print("\nTraceback:")
        traceback.print_exc()
        
        # Debug the connector's code
        print("\nDebugging connector code:")
        print("Checking connector's search method...")
        import inspect
        if hasattr(GoogleScholarConnector, 'search'):
            print(inspect.getsource(GoogleScholarConnector.search))
        else:
            print("search method not found")

async def test_google_scholar_metadata(session, paper_id):
    """Test only the metadata retrieval functionality"""
    print(f"\n=== Testing Google Scholar Metadata Retrieval: '{paper_id}' ===")
    
    try:
        connector = GoogleScholarConnector(session, use_proxy=False)
        paper = await connector.get_paper_metadata(paper_id)
        
        print(f"Title: {paper.title}")
        print(f"Authors: {', '.join(a.name for a in paper.authors)}")
        print(f"PDF URL: {paper.pdf_url}")
        
        # Test PDF download if URL is available
        if paper.pdf_url:
            try:
                print(f"\nAttempting to download PDF...")
                pdf_data = await connector.download_fulltext(paper_id)
                
                # Save the PDF
                clean_id = paper_id.replace(":", "_")
                clean_title = ''.join(c if c.isalnum() or c in [' ', '.', '-', '_'] else '_' for c in paper.title)
                filename = f"{clean_id}_{clean_title[:50]}.pdf"
                filepath = DOWNLOAD_DIR / filename
                
                with open(filepath, "wb") as f:
                    f.write(pdf_data)
                
                print(f"Downloaded {len(pdf_data)} bytes of PDF data")
                print(f"Saved to: {filepath}")
            except Exception as e:
                print(f"PDF download failed: {e}")
        else:
            print("No PDF URL available")
            
    except Exception as e:
        print(f"Error in metadata test: {e}")

async def debug_scholarly_module():
    """Test just the scholarly module directly"""
    print("\n=== Debugging Scholarly Module Directly ===")
    
    try:
        from scholarly import scholarly
        print("Module imported successfully")
        
        # Test a basic search
        print("\nTesting basic search...")
        results = scholarly.search_pubs("natural language processing", patents=False)
        
        # Get first few results
        print("First results:")
        count = 0
        for i in range(3):
            try:
                result = next(results)
                count += 1
                print(f"{i+1}. {result.get('bib', {}).get('title', 'No title')}")
            except StopIteration:
                print("No more results")
                break
            except Exception as e:
                print(f"Error getting result {i}: {e}")
                break
                
        print(f"Successfully retrieved {count} results")
        
    except Exception as e:
        print(f"Error debugging scholarly: {e}")

async def debug_connector_methods():
    """Print and analyze the Google Scholar connector methods"""
    print("\n=== Debugging Google Scholar Connector Methods ===")
    
    try:
        import inspect
        from deepresearch.connectors.google_scholar import GoogleScholarConnector
        
        # Get search method source
        print("\nSearch Method Source:")
        print(inspect.getsource(GoogleScholarConnector.search))
        
        # Get metadata method source
        print("\nGet Paper Metadata Method Source:")
        print(inspect.getsource(GoogleScholarConnector.get_paper_metadata))
        
        # Get download method source
        print("\nDownload Fulltext Method Source:")
        print(inspect.getsource(GoogleScholarConnector.download_fulltext))
        
    except Exception as e:
        print(f"Error inspecting connector methods: {e}")

async def main():
    parser = argparse.ArgumentParser(description='Test and debug Google Scholar connector')
    parser.add_argument('--mode', choices=['search', 'metadata', 'scholarly', 'methods', 'all'], 
                        default='all', help='Which test to run')
    parser.add_argument('--query', type=str, default="language model evaluation", 
                        help='Search query to use')
    parser.add_argument('--paper_id', type=str, default=None, 
                        help='Paper ID for metadata test')
    parser.add_argument('--max_results', type=int, default=3,
                        help='Maximum number of results to return')
    
    args = parser.parse_args()
    
    if args.mode == 'all' and not args.paper_id:
        print("Running in 'all' mode requires a paper_id for metadata testing.")
        print("Defaulting to search and scholarly tests only.")
        args.mode = 'methods'
    
    async with aiohttp.ClientSession() as session:
        if args.mode in ['search', 'all']:
            await test_google_scholar_search(session, args.query, args.max_results)
            
        if args.mode in ['metadata', 'all'] and args.paper_id:
            await test_google_scholar_metadata(session, args.paper_id)
            
        if args.mode in ['scholarly', 'all']:
            await debug_scholarly_module()
            
        if args.mode in ['methods', 'all']:
            await debug_connector_methods()

if __name__ == "__main__":
    asyncio.run(main()) 