from typing import List, Optional
from ..models import Paper, PaperComparison
from ..utils.llm_utils import call_anthropic_api, parse_json_response  # Fixed import path

# Define the LLM prompt template
PAPER_COMPARISON_PROMPT = """
You are a research assistant tasked with comparing multiple scholarly papers.
Please analyze the following papers and provide a detailed comparison of their:

1. Research Questions & Goals: Compare the main research questions, objectives, and scope
2. Methodologies: Compare approaches, techniques, experimental setups, and datasets
3. Key Findings: Compare the main results, focusing on similarities and differences
4. Limitations: Compare the stated limitations and constraints of each approach
5. Future Directions: Compare proposed future work and research opportunities

PAPERS TO COMPARE:

{papers_data}

Please structure your analysis to clearly highlight the key similarities and differences between these papers.
Focus especially on:
- Areas where the papers contradict each other
- Methodological differences that may explain different results
- Complementary findings that together provide deeper insights
- Evolution of research approaches if the papers span different time periods

Format your response as a JSON object with the following structure:
{{
  "research_questions": {{ 
    "comparison": "Overall comparison of research questions",
    "key_differences": ["Difference 1", "Difference 2"],
    "key_similarities": ["Similarity 1", "Similarity 2"]
  }},
  "methodologies": {{ 
    "comparison": "Overall comparison of methodologies",
    "key_differences": ["Difference 1", "Difference 2"],
    "key_similarities": ["Similarity 1", "Similarity 2"]
  }},
  "findings": {{ 
    "comparison": "Overall comparison of findings",
    "key_differences": ["Difference 1", "Difference 2"],
    "key_similarities": ["Similarity 1", "Similarity 2"]
  }},
  "limitations": {{ 
    "comparison": "Overall comparison of limitations",
    "key_differences": ["Difference 1", "Difference 2"],
    "key_similarities": ["Similarity 1", "Similarity 2"]
  }},
  "future_directions": {{ 
    "comparison": "Overall comparison of future directions",
    "key_differences": ["Difference 1", "Difference 2"],
    "key_similarities": ["Similarity 1", "Similarity 2"]
  }}
}}
"""

class PaperComparator:
    """Pipeline for comparing multiple scholarly papers using Anthropic Claude."""

    def __init__(self, llm_api_key: Optional[str] = None):
        self.llm_api_key = llm_api_key

    async def compare_papers(
        self,
        papers: List[Paper],
        abstracts_only: bool = False,
        full_texts: Optional[List[str]] = None
    ) -> PaperComparison:
        """Compare papers using their metadata and optionally full texts."""
        papers_data = []

        for i, paper in enumerate(papers):
            authors_str = ", ".join(author.name for author in paper.authors)
            pub_date = paper.publication_date.strftime("%Y-%m-%d") if paper.publication_date else "Unknown date"

            paper_data = f"Paper {i+1}: {paper.title}\n"
            paper_data += f"Authors: {authors_str}\n"
            paper_data += f"Publication Date: {pub_date}\n"
            paper_data += f"Journal/Source: {paper.journal or paper.source}\n\n"

            if paper.abstract:
                paper_data += f"Abstract:\n{paper.abstract}\n\n"

            if not abstracts_only and full_texts and i < len(full_texts) and full_texts[i]:
                truncated_text = full_texts[i][:10000] + "..." if len(full_texts[i]) > 10000 else full_texts[i]
                paper_data += f"Full Text:\n{truncated_text}\n\n"

            papers_data.append(paper_data)

        prompt = PAPER_COMPARISON_PROMPT.format(papers_data="\n---\n".join(papers_data))

        try:
            raw_response = await call_anthropic_api(prompt, api_key=self.llm_api_key)
            comparison_data = await parse_json_response(raw_response)

            return PaperComparison(
                paper_ids=[paper.paper_id for paper in papers],
                research_questions=comparison_data.get("research_questions", {}),
                methodologies=comparison_data.get("methodologies", {}),
                findings=comparison_data.get("findings", {}),
                limitations=comparison_data.get("limitations", {}),
                future_directions=comparison_data.get("future_directions", {})
            )
        except Exception as e:
            print(f"[PaperComparator] Error comparing papers: {e}")
            return PaperComparison(
                paper_ids=[paper.paper_id for paper in papers],
                research_questions={"comparison": f"Error generating comparison: {e}"},
                methodologies={"comparison": ""},
                findings={"comparison": ""},
                limitations={"comparison": ""},
                future_directions={"comparison": ""}
            )
