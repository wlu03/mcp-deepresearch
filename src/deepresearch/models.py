from typing import List, Dict, Optional, Any, Union, Tuple
from pydantic import BaseModel, Field, AnyUrl
from datetime import datetime

class Author(BaseModel):
    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None
    
class Paper(BaseModel):
    paper_id: str
    title: str
    authors: List[Author]
    abstract: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    publication_date: Optional[datetime] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    source: str  # 'arxiv', 'pubmed', 'semanticscholar', 'googlescholar'
    citations_count: Optional[int] = None
    raw_metadata: Optional[Dict[str, Any]] = None
    
class PaperSummary(BaseModel):
    paper_id: str
    background: str
    methods: str
    results: str
    conclusions: str
    
class Annotation(BaseModel):
    paper_id: str
    highlights: List[Dict[str, Any]]
    keywords: List[str]
    notes: Optional[str] = None
    
class CitationLink(BaseModel):
    source_id: str
    target_id: str
    
class CitationGraph(BaseModel):
    nodes: List[Paper]
    links: List[CitationLink]
    
class DriveDocument(BaseModel):
    document_id: str
    name: str
    mime_type: str
    web_view_link: str
    created_time: datetime
    
class SearchQuery(BaseModel):
    query: str
    sources: List[str] = Field(default_factory=lambda: ["arxiv", "pubmed", "semanticscholar"])
    max_results: int = 20
    sort_by: str = "relevance"  # 'relevance', 'date', 'citations'
    
class SearchResult(BaseModel):
    query: str
    papers: List[Paper]
    total_found: int
    thematic_summary: Optional[str] = None
    suggested_queries: Optional[List[str]] = None

class Relation(BaseModel):
    paper_id: str
    source: str
    relation: str
    target: str
    section: Optional[str] = None
    evidence: Optional[str] = None

class PaperComparison(BaseModel):
    paper_ids: List[str]
    research_questions: Dict[str, Any]
    methodologies: Dict[str, Any]
    findings: Dict[str, Any]
    limitations: Dict[str, Any]
    future_directions: Dict[str, Any]

class PublicationTrend(BaseModel):
    query: str
    year_counts: Dict[int, int]  # Publication count by year
    emerging_topics: List[str]   # List of emerging topics/terms
    frequent_authors: List[Tuple[str, int]]  # Author name and count
    term_frequencies: Dict[str, int]  # Term frequency counts
    source_distribution: Dict[str, int]  # Count by source 