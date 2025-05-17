from typing import Dict, Any, Optional, Union, List
import asyncio
import logging
import re
from ..models import Paper, PaperSummary
from ..utils.llm_utils import call_anthropic_api, parse_json_response

logger = logging.getLogger(__name__)

# Define the LLM prompt template for summarizing a paper
SUMMARIZE_PROMPT_TEMPLATE = """
You are a research assistant tasked with creating a structured summary of a scholarly paper.
Please analyze the following paper and create a detailed, well-structured summary with the following sections:

1. Background: Describe the context and motivation for the research, prior work, and the gap being addressed.
2. Methods: Summarize the key methodologies, techniques, and approaches used in the paper.
3. Results: Present the most important findings, data, and outcomes reported in the paper.
4. Conclusions: Summarize the main conclusions, implications, and future directions suggested by the authors.

Each section should be comprehensive but concise, capturing the essential information.

PAPER TITLE: {title}
PAPER AUTHORS: {authors}
PAPER ABSTRACT: {abstract}

PAPER FULL TEXT:
{text}

Please format your response as:
# Background
[background content]

# Methods
[methods content]

# Results
[results content]

# Conclusions
[conclusions content]
"""

# Define the LLM prompt template for generating annotations
ANNOTATE_PROMPT_TEMPLATE = """
You are a research assistant tasked with identifying and highlighting key information in a scholarly paper.
Please analyze the following paper and:

1. Identify the 5-10 most important sentences that capture key findings, methodologies, and conclusions.
2. Extract 10-15 keywords that represent the core topics and concepts in the paper.

PAPER TITLE: {title}
PAPER AUTHORS: {authors}
PAPER ABSTRACT: {abstract}

PAPER FULL TEXT:
{text}

Please format your response as:
# Key Sentences
1. [Sentence 1]
2. [Sentence 2]
...

# Keywords
[keyword1], [keyword2], [keyword3], ...
"""

# Add this to the top with the other prompt templates
SECTION_SUMMARIZE_PROMPT_TEMPLATE = """
You are a research assistant tasked with summarizing a specific section of a scholarly paper.
Please analyze the following paper section and create a detailed, focused summary.

PAPER TITLE: {title}
PAPER AUTHORS: {authors}
PAPER SECTION: {section_name}

SECTION TEXT:
{section_text}

Please provide a comprehensive but concise summary of this section, capturing:
1. The main points and arguments presented
2. Any important methodology details (if applicable)
3. Key findings or results (if applicable)
4. How this section connects to the overall paper's narrative

Your summary should maintain the technical accuracy of the original while being more accessible.
"""

class Summarizer:
    """Pipeline for generating structured summaries and annotations of scholarly papers."""
    
    def __init__(self, llm_api_key: Optional[str] = None):
        """
        Initialize the summarizer.
        
        Args:
            llm_api_key: API key for the language model service
        """
        self.llm_api_key = llm_api_key
        
    async def summarize_paper(self, paper: Paper, full_text: str) -> PaperSummary:
        """
        Generate a structured summary of a paper.
        
        Args:
            paper: Paper model with metadata
            full_text: Full text of the paper
            
        Returns:
            PaperSummary object with structured sections
        """
        # Create the prompt
        authors_str = ", ".join(author.name for author in paper.authors)
        prompt = SUMMARIZE_PROMPT_TEMPLATE.format(
            title=paper.title,
            authors=authors_str,
            abstract=paper.abstract,
            text=full_text[:10000]  # Limit text length for LLM context window
        )
        
        # Call LLM
        try:
            response = await call_anthropic_api(prompt, self.llm_api_key)
            
            # Parse the response to extract sections
            background = self._extract_section(response, "Background")
            methods = self._extract_section(response, "Methods")
            results = self._extract_section(response, "Results")
            conclusions = self._extract_section(response, "Conclusions")
            
            # Create the summary object
            return PaperSummary(
                paper_id=paper.paper_id,
                background=background,
                methods=methods,
                results=results,
                conclusions=conclusions
            )
        except Exception as e:
            logger.error(f"Failed to generate paper summary: {str(e)}")
            # Return a minimal summary with error information
            return PaperSummary(
                paper_id=paper.paper_id,
                background=f"Error generating summary: {str(e)}",
                methods="",
                results="",
                conclusions=""
            )
            
    async def annotate_paper(self, paper: Paper, full_text: str) -> Dict[str, Any]:
        """
        Generate annotations for a paper including key sentences and keywords.
        
        Args:
            paper: Paper model with metadata
            full_text: Full text of the paper
            
        Returns:
            Dictionary with highlights and keywords
        """
        # Create the prompt
        authors_str = ", ".join(author.name for author in paper.authors)
        prompt = ANNOTATE_PROMPT_TEMPLATE.format(
            title=paper.title,
            authors=authors_str,
            abstract=paper.abstract,
            text=full_text[:10000]  # Limit text length for LLM context window
        )
        
        # Call LLM
        try:
            response = await call_anthropic_api(prompt, self.llm_api_key)
            
            # Parse the response to extract key sentences and keywords
            sentences = self._extract_key_sentences(response)
            keywords = self._extract_keywords(response)
            
            # Create the annotations
            return {
                "paper_id": paper.paper_id,
                "highlights": [{"text": sentence} for sentence in sentences],
                "keywords": keywords
            }
        except Exception as e:
            logger.error(f"Failed to generate paper annotations: {str(e)}")
            # Return minimal annotations with error information
            return {
                "paper_id": paper.paper_id,
                "highlights": [{"text": f"Error generating annotations: {str(e)}"}],
                "keywords": []
            }
            
    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract content of a specific section from the structured response."""
        pattern = rf"#\s*{section_name}\s*\n(.*?)(?:\n#|$)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return f"No {section_name} section found in the summary."
        
    def _extract_key_sentences(self, text: str) -> List[str]:
        """Extract key sentences from the structured response."""
        pattern = r"#\s*Key\s*Sentences\s*\n(.*?)(?:\n#|$)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            sentences_text = match.group(1).strip()
            # Extract numbered sentences
            sentences = re.findall(r"\d+\.\s*(.*?)(?:\n|$)", sentences_text)
            return sentences
        return []
        
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from the structured response."""
        pattern = r"#\s*Keywords\s*\n(.*?)(?:\n#|$)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            keywords_text = match.group(1).strip()
            # Split by commas and clean up
            keywords = [k.strip() for k in keywords_text.split(",")]
            return [k for k in keywords if k]  # Filter out empty strings
        return []

    async def summarize_section(self, paper: Paper, section_name: str, section_text: str) -> str:
        """
        Generate a focused summary of a specific paper section.
        
        Args:
            paper: Paper model with metadata
            section_name: Name of the section (e.g., "Introduction", "Methods", "Results")
            section_text: Text content of the section
            
        Returns:
            Summary text for the specific section
        """
        # Create the prompt
        authors_str = ", ".join(author.name for author in paper.authors)
        prompt = SECTION_SUMMARIZE_PROMPT_TEMPLATE.format(
            title=paper.title,
            authors=authors_str,
            section_name=section_name,
            section_text=section_text[:10000]  # Limit text length for LLM context window
        )
        
        # Call LLM
        try:
            response = await call_anthropic_api(prompt, self.llm_api_key)
            
            # Return the summary (no need to extract sections)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate section summary: {str(e)}")
            # Return error message on failure
            return f"Error generating summary for {section_name} section: {str(e)}" 