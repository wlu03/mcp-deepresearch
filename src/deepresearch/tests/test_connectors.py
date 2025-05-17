import asyncio
import aiohttp
import os
import sys
import argparse
import json
from datetime import datetime

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from deepresearch.connectors import (
    ArXivConnector,
    PubMedConnector, 
    SemanticScholarConnector,
    GoogleScholarConnector,
    GoogleDriveConnector
)
from deepresearch.models import SearchQuery, Paper

async def test_arxiv(session):
    """Test ArXiv connector functionality"""
    print("\n=== Testing ArXiv Connector ===")
    
    try:
        connector = ArXivConnector(session)
        
        # Test search
        print("\nTesting search...")
        query = SearchQuery(query="transformer neural networks", max_results=5)
        papers = await connector.search(query)
        print(f"Found {len(papers)} papers")
        if papers:
            print(f"First paper: {papers[0].title}")
            
        # Test metadata retrieval
        if papers:
            paper_id = papers[0].paper_id
            print(f"\nTesting metadata retrieval for {paper_id}...")
            paper = await connector.get_paper_metadata(paper_id)
            print(f"Title: {paper.title}")
            print(f"Authors: {', '.join(a.name for a in paper.authors)}")
            print(f"Abstract: {paper.abstract[:150]}...")
            
            # Test PDF download
            print(f"\nTesting PDF download for {paper_id}...")
            pdf_data = await connector.download_fulltext(paper_id)
            print(f"Downloaded {len(pdf_data)} bytes of PDF data")
            
        # Test ID parsing
        print("\nTesting ID parsing...")
        test_ids = [
            "2104.08935",
            "arxiv:2104.08935",
            "https://arxiv.org/abs/2104.08935"
        ]
        for test_id in test_ids:
            parsed = connector.parse_paper_id(test_id)
            print(f"Original: {test_id} -> Parsed: {parsed}")
            
    except Exception as e:
        print(f"Error testing ArXiv connector: {e}")

async def test_pubmed(session):
    """Test PubMed connector functionality"""
    print("\n=== Testing PubMed Connector ===")
    
    try:
        connector = PubMedConnector(session, email="deepresearch@example.com")
        
        # Test search
        print("\nTesting search...")
        query = SearchQuery(query="CRISPR gene editing", max_results=5)
        papers = await connector.search(query)
        print(f"Found {len(papers)} papers")
        if papers:
            print(f"First paper: {papers[0].title}")
            
        # Test metadata retrieval
        if papers:
            paper_id = papers[0].paper_id
            print(f"\nTesting metadata retrieval for {paper_id}...")
            paper = await connector.get_paper_metadata(paper_id)
            print(f"Title: {paper.title}")
            print(f"Authors: {', '.join(a.name for a in paper.authors)}")
            print(f"Abstract: {paper.abstract[:150] if paper.abstract else 'No abstract'}...")
            
            # Test fulltext download (may not be available for all papers)
            try:
                print(f"\nTesting PDF download for {paper_id}...")
                pdf_data = await connector.download_fulltext(paper_id)
                print(f"Downloaded {len(pdf_data)} bytes of PDF data")
            except Exception as e:
                print(f"Full text download failed (expected for many PubMed papers): {e}")
            
        # Test ID parsing
        print("\nTesting ID parsing...")
        test_ids = [
            "12345678",
            "pubmed:12345678",
            "https://pubmed.ncbi.nlm.nih.gov/12345678/"
        ]
        for test_id in test_ids:
            parsed = connector.parse_paper_id(test_id)
            print(f"Original: {test_id} -> Parsed: {parsed}")
            
    except Exception as e:
        print(f"Error testing PubMed connector: {e}")

async def test_semantic_scholar(session):
    """Test Semantic Scholar connector functionality"""
    print("\n=== Testing Semantic Scholar Connector ===")
    
    try:
        api_key = os.environ.get("SEMANTICSCHOLAR_API_KEY", None)
        connector = SemanticScholarConnector(session, api_key=api_key)
        
        # Test search
        print("\nTesting search...")
        query = SearchQuery(query="GPT-4 capabilities", max_results=5)
        papers = await connector.search(query)
        print(f"Found {len(papers)} papers")
        if papers:
            print(f"First paper: {papers[0].title}")
            
        # Test metadata retrieval
        if papers:
            paper_id = papers[0].paper_id
            print(f"\nTesting metadata retrieval for {paper_id}...")
            paper = await connector.get_paper_metadata(paper_id)
            print(f"Title: {paper.title}")
            print(f"Authors: {', '.join(a.name for a in paper.authors)}")
            print(f"Abstract: {paper.abstract[:150] if paper.abstract else 'No abstract'}...")
            
            # Test fulltext download (may not be available for all papers)
            if paper.pdf_url:
                try:
                    print(f"\nTesting PDF download for {paper_id}...")
                    pdf_data = await connector.download_fulltext(paper_id)
                    print(f"Downloaded {len(pdf_data)} bytes of PDF data")
                except Exception as e:
                    print(f"Full text download failed: {e}")
            else:
                print("No PDF URL available for this paper")
            
        # Test ID parsing
        print("\nTesting ID parsing...")
        test_ids = [
            "12345678",
            "semanticscholar:12345678",
            "https://www.semanticscholar.org/paper/12345678"
        ]
        for test_id in test_ids:
            parsed = connector.parse_paper_id(test_id)
            print(f"Original: {test_id} -> Parsed: {parsed}")
            
    except Exception as e:
        print(f"Error testing Semantic Scholar connector: {e}")

async def test_google_scholar(session):
    """Test Google Scholar connector functionality"""
    print("\n=== Testing Google Scholar Connector ===")
    print("\nNote: Google Scholar may rate-limit or block scraping attempts")
    
    try:
        connector = GoogleScholarConnector(session, use_proxy=False)
        
        # Test search
        print("\nTesting search...")
        query = SearchQuery(query="language model evaluation", max_results=3)
        papers = await connector.search(query)
        print(f"Found {len(papers)} papers")
        if papers:
            print(f"First paper: {papers[0].title}")
            
        # Test metadata retrieval (this might fail due to rate limiting)
        if papers:
            try:
                paper_id = papers[0].paper_id
                print(f"\nTesting metadata retrieval for {paper_id}...")
                paper = await connector.get_paper_metadata(paper_id)
                print(f"Title: {paper.title}")
                print(f"Authors: {', '.join(a.name for a in paper.authors)}")
            except Exception as e:
                print(f"Metadata retrieval failed (possibly due to rate limiting): {e}")
            
        # Test ID parsing
        print("\nTesting ID parsing...")
        test_ids = [
            "abcdef123456",
            "googlescholar:abcdef123456",
            "https://scholar.google.com/scholar?cluster=abcdef123456"
        ]
        for test_id in test_ids:
            parsed = connector.parse_paper_id(test_id)
            print(f"Original: {test_id} -> Parsed: {parsed}")
            
    except Exception as e:
        print(f"Error testing Google Scholar connector: {e}")

async def test_google_drive(session):
    """Test Google Drive connector functionality"""
    print("\n=== Testing Google Drive Connector ===")
    
    try:
        connector = GoogleDriveConnector(session)
        
        # Test authentication
        print("\nTesting authentication (this will prompt for authorization if needed)...")
        auth_success = await connector.authenticate()
        if auth_success:
            print("Authentication successful")
            
            # Test folder creation
            test_folder_name = f"DeepResearch_Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"\nTesting folder creation: {test_folder_name}...")
            folder_id = await connector.create_folder(test_folder_name)
            print(f"Created folder with ID: {folder_id}")
            
            # Test document upload
            print("\nTesting document upload...")
            test_content = "This is a test document created by DeepResearch test script."
            test_filename = "test_document.txt"
            doc = await connector.store_document(
                content=test_content,
                filename=test_filename,
                mime_type="text/plain",
                folder_id=folder_id
            )
            print(f"Uploaded document: {doc.name}")
            print(f"View at: {doc.web_view_link}")
            
            # Test listing documents
            print("\nTesting document listing...")
            docs = await connector.list_documents(folder_id=folder_id)
            print(f"Found {len(docs)} documents in folder")
            for d in docs:
                print(f"- {d.name} ({d.mime_type})")
                
            # Test downloading document
            print("\nTesting document download...")
            content = await connector.download_document(doc.document_id)
            print(f"Downloaded {len(content)} bytes")
            print(f"Content: {content.decode('utf-8')}")
        else:
            print("Authentication failed")
            
    except Exception as e:
        print(f"Error testing Google Drive connector: {e}")
        
async def main():
    parser = argparse.ArgumentParser(description='Test DeepResearch connectors')
    parser.add_argument('--connector', choices=['arxiv', 'pubmed', 'semanticscholar', 'googlescholar', 'drive', 'all'], 
                        default='all', help='Which connector to test')
    
    args = parser.parse_args()
    
    async with aiohttp.ClientSession() as session:
        if args.connector in ['arxiv', 'all']:
            await test_arxiv(session)
            
        if args.connector in ['pubmed', 'all']:
            await test_pubmed(session)
            
        if args.connector in ['semanticscholar', 'all']:
            await test_semantic_scholar(session)
            
        if args.connector in ['googlescholar', 'all']:
            await test_google_scholar(session)
            
        if args.connector in ['drive', 'all']:
            await test_google_drive(session)

if __name__ == "__main__":
    asyncio.run(main()) 