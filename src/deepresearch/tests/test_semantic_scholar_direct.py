import semanticscholar as ss
import asyncio
import time

def test_direct_api():
    """Test direct access to Semantic Scholar API"""
    print("Testing direct access to Semantic Scholar API...")
    
    try:
        # Create client
        print("Creating client...")
        client = ss.SemanticScholar()
        print("Client created successfully")
        
        # Test getting a paper by ID
        print("\nTesting get_paper...")
        paper_id = "0796f6cd-5712-4342-9c9f-3f3735f6e20a"  # GPT-3 paper ID
        print(f"Fetching paper {paper_id}...")
        
        # Add delay to avoid rate limiting
        time.sleep(1)
        
        paper = client.get_paper(paper_id)
        if paper:
            print(f"Successfully retrieved paper: {paper['title']}")
        else:
            print("Paper not found")
            
        # Test searching for papers
        print("\nTesting paper search...")
        print("Searching for 'machine learning'...")
        
        # Add delay to avoid rate limiting
        time.sleep(1)
        
        papers = client.search_paper("machine learning", limit=3)
        if papers:
            print(f"Found {len(papers)} papers:")
            for i, p in enumerate(papers, 1):
                print(f"{i}. {p['title']}")
        else:
            print("No papers found")
            
        print("\nDirect API test completed successfully")
        
    except Exception as e:
        print(f"Error in direct API test: {e}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'args') and e.args:
            print(f"Error details: {e.args}")

if __name__ == "__main__":
    test_direct_api() 