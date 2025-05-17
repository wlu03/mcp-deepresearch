from typing import Dict, Any, Optional, Union, List
import asyncio
import logging
import re
from ..models import Paper, Relation
from ..utils.llm_utils import call_anthropic_api, parse_json_response

logger = logging.getLogger(__name__)

# Define the LLM prompt template for extracting relationships
RELATION_EXTRACTION_PROMPT = """
You are a research assistant tasked with identifying relationships between concepts in a scholarly paper.
Please analyze the following paper and extract important relationships between entities, such as:

- Causal relationships (X causes Y, X increases Y, X inhibits Y)
- Comparative relationships (X outperforms Y, X is more effective than Y)
- Correlative relationships (X is associated with Y, X is related to Y)
- Compositional relationships (X consists of Y, X contains Y)

For each relationship, identify:
1. The source concept
2. The relation type
3. The target concept
4. The specific section where this relation was found (Introduction, Methods, Results, Discussion)
5. A short quote from the text supporting this relation

PAPER TITLE: {title}
PAPER AUTHORS: {authors}
PAPER ABSTRACT: {abstract}

PAPER FULL TEXT:
{text}

Format your response as a JSON list of relations:
[
  {{
    "source": "concept1",
    "relation": "causes",
    "target": "concept2",
    "section": "Results",
    "evidence": "We observed that concept1 directly causes concept2..."
  }},
  ...
]
"""

class RelationExtractor:
    """Pipeline for extracting relationships between concepts in scholarly papers."""
    
    def __init__(self, llm_api_key: Optional[str] = None):
        """
        Initialize the relation extractor.
        
        Args:
            llm_api_key: API key for the language model service
        """
        self.llm_api_key = llm_api_key
        
    async def extract_relations(self, paper: Paper, full_text: str) -> List[Relation]:
        """
        Extract relationships between concepts in a paper.
        
        Args:
            paper: Paper model with metadata
            full_text: Full text of the paper
            
        Returns:
            List of Relation objects
        """
        # Create the prompt
        authors_str = ", ".join(author.name for author in paper.authors)
        prompt = RELATION_EXTRACTION_PROMPT.format(
            title=paper.title,
            authors=authors_str,
            abstract=paper.abstract,
            text=full_text[:10000]  # Limit text length for LLM context window
        )
        
        # Call LLM
        try:
            response = await call_anthropic_api(prompt, self.llm_api_key)
            
            # Parse the response to extract relations
            import json
            try:
                # First try to parse the response directly with json.loads
                relations_data = json.loads(response)
            except json.JSONDecodeError:
                # If direct parsing fails, use the helper
                relations_data = await parse_json_response(response)
            
            # Convert to Relation objects
            relations = []
            for rel_data in relations_data:
                relation = Relation(
                    paper_id=paper.paper_id,
                    source=rel_data.get("source", ""),
                    relation=rel_data.get("relation", ""),
                    target=rel_data.get("target", ""),
                    section=rel_data.get("section", ""),
                    evidence=rel_data.get("evidence", "")
                )
                relations.append(relation)
            
            return relations
        except Exception as e:
            logger.error(f"Failed to extract relations: {str(e)}")
            # Return empty list on error
            return [] 