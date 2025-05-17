from typing import Dict, Any, Optional, Union, List, Tuple
import asyncio
import logging
from datetime import datetime
from collections import Counter, defaultdict
import re
import json
from ..models import Paper, PublicationTrend

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """Pipeline for analyzing publication trends and identifying emerging topics."""
    
    def __init__(self):
        """Initialize the trend analyzer."""
        pass
        
    async def analyze_trends(self, papers: List[Paper]) -> PublicationTrend:
        """
        Analyze publication trends from a list of papers.
        
        Args:
            papers: List of Paper objects to analyze
            
        Returns:
            PublicationTrend object with trend analysis
        """
        if not papers:
            return PublicationTrend(
                query="",
                year_counts={},
                emerging_topics=[],
                frequent_authors=[],
                term_frequencies={},
                source_distribution={}
            )
            
        # Extract query from first paper if available
        query = papers[0].raw_metadata.get("query", "") if papers[0].raw_metadata else ""
        
        # Count publications by year
        year_counts = self._count_by_year(papers)
        
        # Extract n-grams from titles and abstracts
        title_abstract_text = self._concatenate_titles_and_abstracts(papers)
        term_frequencies = self._extract_ngrams(title_abstract_text)
        
        # Identify frequent authors
        frequent_authors = self._find_frequent_authors(papers)
        
        # Count publications by source
        source_distribution = self._count_by_source(papers)
        
        # Identify emerging topics using temporal analysis
        emerging_topics = self._identify_emerging_topics(papers)
        
        # Create and return the trend analysis
        return PublicationTrend(
            query=query,
            year_counts=year_counts,
            emerging_topics=emerging_topics,
            frequent_authors=frequent_authors,
            term_frequencies=term_frequencies,
            source_distribution=source_distribution
        )
        
    def _count_by_year(self, papers: List[Paper]) -> Dict[int, int]:
        """Count papers by publication year."""
        year_counts = defaultdict(int)
        
        for paper in papers:
            if paper.publication_date:
                year = paper.publication_date.year
                year_counts[year] += 1
                
        # Convert to regular dict and sort by year
        return dict(sorted(year_counts.items()))
        
    def _concatenate_titles_and_abstracts(self, papers: List[Paper]) -> str:
        """Combine all titles and abstracts for text analysis."""
        text = ""
        
        for paper in papers:
            if paper.title:
                text += paper.title + " "
            if paper.abstract:
                text += paper.abstract + " "
                
        return text
        
    def _extract_ngrams(self, text: str, max_ngram: int = 3, min_count: int = 2) -> Dict[str, int]:
        """Extract and count n-grams from text."""
        # Clean and normalize text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)  # Replace punctuation with spaces
        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        words = text.split()
        
        # Count n-grams
        ngram_counts = defaultdict(int)
        
        # Extract 1 to max_ngram-grams
        for n in range(1, max_ngram + 1):
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i+n])
                ngram_counts[ngram] += 1
                
        # Filter by minimum count and sort by frequency
        filtered_counts = {k: v for k, v in ngram_counts.items() if v >= min_count}
        return dict(sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True)[:50])
        
    def _find_frequent_authors(self, papers: List[Paper], top_n: int = 20) -> List[Tuple[str, int]]:
        """Find the most frequent authors."""
        author_counts = defaultdict(int)
        
        for paper in papers:
            for author in paper.authors:
                author_counts[author.name] += 1
                
        # Sort by frequency and return top N
        return sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
    def _count_by_source(self, papers: List[Paper]) -> Dict[str, int]:
        """Count papers by source."""
        source_counts = defaultdict(int)
        
        for paper in papers:
            source_counts[paper.source] += 1
            
        # Sort by frequency
        return dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True))
        
    def _identify_emerging_topics(self, papers: List[Paper], recent_years: int = 2) -> List[str]:
        """
        Identify emerging topics by looking at term frequency growth in recent years.
        
        This is a simplified implementation. A more sophisticated approach would:
        1. Calculate term frequencies by year
        2. Measure growth rates
        3. Apply statistical tests to identify significant growth
        """
        # Filter to recent and older papers
        current_year = datetime.now().year
        recent_papers = []
        older_papers = []
        
        for paper in papers:
            if paper.publication_date:
                if paper.publication_date.year >= current_year - recent_years:
                    recent_papers.append(paper)
                else:
                    older_papers.append(paper)
        
        if not recent_papers or not older_papers:
            return []  # Need both recent and older papers for comparison
            
        # Get terms from recent and older papers
        recent_text = self._concatenate_titles_and_abstracts(recent_papers)
        older_text = self._concatenate_titles_and_abstracts(older_papers)
        
        recent_terms = self._extract_ngrams(recent_text, max_ngram=2)
        older_terms = self._extract_ngrams(older_text, max_ngram=2)
        
        # Find terms that are more frequent in recent papers
        emerging_topics = []
        
        for term, count in recent_terms.items():
            older_count = older_terms.get(term, 0)
            
            # Skip common stop words and single letters
            if len(term) <= 1 or term in ["the", "and", "of", "in", "to", "a", "is", "that", "for", "on", "with"]:
                continue
                
            # Calculate normalized frequency (by paper count)
            recent_freq = count / len(recent_papers) if recent_papers else 0
            older_freq = older_count / len(older_papers) if older_papers else 0
            
            # Check if term is significantly more frequent in recent papers
            if recent_freq > older_freq * 1.5:  # 50% growth in frequency
                emerging_topics.append(term)
                
        return emerging_topics[:10]  # Return top 10 emerging topics 