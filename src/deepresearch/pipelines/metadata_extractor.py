from typing import Dict, Any, Optional, Union, List
import re
import json
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from ..models import Paper, Author

class MetadataExtractor:
    """Extract and normalize metadata from different scholarly sources."""
    
    @staticmethod
    async def extract_from_bibtex(bibtex_str: str) -> Paper:
        """Extract paper metadata from BibTeX format."""
        # Basic BibTeX parser - in a real implementation, use a proper BibTeX parser
        entry_type_match = re.search(r'@(\w+)\s*\{([^,]*)', bibtex_str)
        if not entry_type_match:
            raise ValueError("Invalid BibTeX format")
            
        entry_type = entry_type_match.group(1).lower()
        entry_key = entry_type_match.group(2).strip()
        
        # Extract all fields
        fields = {}
        field_matches = re.finditer(r'(\w+)\s*=\s*[{"]([^}"]*)[}"]', bibtex_str)
        
        for match in field_matches:
            field_name = match.group(1).lower()
            field_value = match.group(2)
            fields[field_name] = field_value
            
        # Process authors
        authors = []
        if 'author' in fields:
            # Split on 'and' but handle names with 'and' in them
            author_names = re.split(r'\s+and\s+', fields['author'])
            for name in author_names:
                authors.append(Author(name=name.strip()))
                
        # Process publication date
        pub_date = None
        if 'year' in fields:
            try:
                year = int(fields['year'])
                month = int(fields.get('month', '1'))
                day = 1
                pub_date = datetime(year, month, day)
            except (ValueError, TypeError):
                pass
                
        # Create paper object
        return Paper(
            paper_id=f"bibtex:{entry_key}",
            title=fields.get('title', ''),
            authors=authors,
            abstract=fields.get('abstract', ''),
            url=fields.get('url', ''),
            pdf_url=fields.get('pdf', ''),
            publication_date=pub_date,
            journal=fields.get('journal', fields.get('booktitle', '')),
            doi=fields.get('doi', ''),
            source="bibtex",
            citations_count=None,
            raw_metadata=fields
        )
        
    @staticmethod
    async def extract_from_json(json_str: str) -> Paper:
        """Extract paper metadata from JSON format."""
        try:
            data = json.loads(json_str)
            
            # Process authors
            authors = []
            if 'authors' in data:
                for author_data in data['authors']:
                    if isinstance(author_data, str):
                        authors.append(Author(name=author_data))
                    elif isinstance(author_data, dict):
                        authors.append(Author(
                            name=author_data.get('name', ''),
                            affiliation=author_data.get('affiliation'),
                            email=author_data.get('email')
                        ))
                        
            # Process publication date
            pub_date = None
            if 'publication_date' in data:
                try:
                    pub_date = datetime.fromisoformat(data['publication_date'])
                except (ValueError, TypeError):
                    # Try to parse just year
                    if 'year' in data:
                        try:
                            pub_date = datetime(int(data['year']), 1, 1)
                        except (ValueError, TypeError):
                            pass
            elif 'year' in data:
                try:
                    pub_date = datetime(int(data['year']), 1, 1)
                except (ValueError, TypeError):
                    pass
                    
            # Create paper object
            return Paper(
                paper_id=data.get('id', data.get('paper_id', f"json:{data.get('title', '')}")),
                title=data.get('title', ''),
                authors=authors,
                abstract=data.get('abstract', ''),
                url=data.get('url', ''),
                pdf_url=data.get('pdf_url', ''),
                publication_date=pub_date,
                journal=data.get('journal', data.get('venue', '')),
                doi=data.get('doi', ''),
                source=data.get('source', 'json'),
                citations_count=data.get('citations_count'),
                raw_metadata=data
            )
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format")
            
    @staticmethod
    async def extract_from_html(html_str: str) -> Paper:
        """Extract paper metadata from HTML (using meta tags and schema.org markup)."""
        soup = BeautifulSoup(html_str, 'html.parser')
        
        # Try to extract from meta tags first
        meta_data = {}
        for meta in soup.find_all('meta'):
            if meta.get('name') and meta.get('content'):
                meta_data[meta['name']] = meta['content']
            elif meta.get('property') and meta.get('content'):
                meta_data[meta['property']] = meta['content']
                
        # Try to extract from schema.org markup
        schema_data = {}
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['ScholarlyArticle', 'Article']:
                    schema_data = data
                    break
            except (json.JSONDecodeError, TypeError):
                continue
                
        # Combine data sources with priority to schema.org
        combined_data = {**meta_data, **schema_data}
        
        # Process title
        title = (
            schema_data.get('headline', schema_data.get('name', '')) or
            meta_data.get('citation_title', meta_data.get('og:title', '')) or
            soup.title.string if soup.title else ''
        )
        
        # Process authors
        authors = []
        author_data = schema_data.get('author', [])
        if author_data:
            if not isinstance(author_data, list):
                author_data = [author_data]
                
            for author in author_data:
                if isinstance(author, dict):
                    authors.append(Author(
                        name=author.get('name', ''),
                        affiliation=author.get('affiliation', {}).get('name') if isinstance(author.get('affiliation'), dict) else author.get('affiliation'),
                        email=None
                    ))
                    
        if not authors and 'citation_author' in meta_data:
            if isinstance(meta_data['citation_author'], list):
                for author_name in meta_data['citation_author']:
                    authors.append(Author(name=author_name))
            else:
                authors.append(Author(name=meta_data['citation_author']))
                
        # Process publication date
        pub_date = None
        date_str = (
            schema_data.get('datePublished') or
            meta_data.get('citation_publication_date') or
            meta_data.get('article:published_time')
        )
        
        if date_str:
            try:
                pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
                
        # Create paper object
        return Paper(
            paper_id=f"html:{title}",  # Create a simple ID from title
            title=title,
            authors=authors,
            abstract=meta_data.get('description', meta_data.get('og:description', '')),
            url=meta_data.get('og:url', ''),
            pdf_url=meta_data.get('citation_pdf_url', ''),
            publication_date=pub_date,
            journal=meta_data.get('citation_journal_title', schema_data.get('publishedIn', '')),
            doi=meta_data.get('citation_doi', ''),
            source='html',
            citations_count=None,
            raw_metadata=combined_data
        )
        
    @staticmethod
    async def extract_metadata(
        source_data: Union[str, Dict[str, Any]], 
        format_type: str
    ) -> Paper:
        """Extract metadata from various formats."""
        if isinstance(source_data, dict):
            source_data = json.dumps(source_data)
            format_type = 'json'
            
        if format_type == 'bibtex':
            return await MetadataExtractor.extract_from_bibtex(source_data)
        elif format_type == 'json':
            return await MetadataExtractor.extract_from_json(source_data)
        elif format_type == 'html':
            return await MetadataExtractor.extract_from_html(source_data)
        else:
            raise ValueError(f"Unsupported format type: {format_type}") 