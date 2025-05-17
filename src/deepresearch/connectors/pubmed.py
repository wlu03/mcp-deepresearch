from typing import List, Dict, Any, Optional
import aiohttp
import asyncio
from datetime import datetime
from Bio import Entrez
from Bio import Medline

# Local app imports (assumed to be in your project)
from ..models import Paper, Author, SearchQuery
from .base import BaseConnector

# Required for all Entrez queries (NCBI requires email for usage tracking)
Entrez.email = "wesleylu03@gmail.com"

class PubMedConnector(BaseConnector):
    """Connector for querying PubMed using NCBI's E-utilities via Biopython."""
    def __init__(self, session: Optional[aiohttp.ClientSession] = None, email: Optional[str] = None):
        # Initialize with an aiohttp session (used for async HTTP calls)
        super().__init__(session)
        if email:
            Entrez.email = email

    async def search(self, query: SearchQuery) -> List[Paper]:
        """
        Perform a search query on PubMed and return a list of Paper objects.
        This includes title, authors, abstract, DOI, journal, etc.
        """
        loop = asyncio.get_running_loop()

        # Run Entrez.esearch
        handle = await loop.run_in_executor(
            None,
            lambda: Entrez.esearch(
                db="pubmed",
                term=query.query,               # Search term (e.g., "cancer treatment 2023")
                retmax=query.max_results,       # Max number of results to fetch
                sort="relevance" if query.sort_by == "relevance" else "date"
            )
        )

        # Parse search results into a Python dict
        search_results = await loop.run_in_executor(None, lambda: Entrez.read(handle))
        handle.close()

        id_list = search_results["IdList"] # List of matching PubMed IDs
        if not id_list:
            return [] 

        # Fetch metadata for the list of IDs
        handle = await loop.run_in_executor(
            None,
            lambda: Entrez.efetch(
                db="pubmed",
                id=id_list,
                rettype="medline",      # Get MEDLINE format
                retmode="text"          # Text format
            )
        )

        # Parse MEDLINE records
        records = await loop.run_in_executor(None, lambda: list(Medline.parse(handle)))
        handle.close()

        papers = []
        for record in records:
            # Parse authors
            authors = []
            if "AU" in record:
                for author_name in record["AU"]:
                    authors.append(Author(name=author_name))

            # Parse publication date (attempt to get at least the year)
            pub_date = None
            if "DP" in record:
                try:
                    date_str = record["DP"].split("-")[0]  # Get just the year
                    pub_date = datetime.strptime(date_str, "%Y")
                except (ValueError, IndexError):
                    pass

            # Extract DOI
            doi = None
            if "AID" in record:
                for aid in record["AID"]:
                    if aid.endswith("[doi]"):
                        doi = aid.split(" ")[0]
                        break

            journal = record.get("TA", record.get("JT", None))  # Abbreviated or full journal name

            # Create a Paper object from the record
            paper = Paper(
                paper_id=f"pubmed:{record['PMID']}",
                title=record.get("TI", ""),
                authors=authors,
                abstract=record.get("AB", ""),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{record['PMID']}/",
                pdf_url=None,
                publication_date=pub_date,
                journal=journal,
                doi=doi,
                source="pubmed",
                citations_count=None,  # PubMed doesn't provide citation counts
                raw_metadata={
                    "mesh_terms": record.get("MH", []),
                    "publication_types": record.get("PT", []),
                    "keywords": record.get("OT", [])
                }
            )
            papers.append(paper)

        return papers

    async def get_paper_metadata(self, paper_id: str) -> Paper:
        """
        Retrieve full metadata for a single paper by PubMed ID.
        """
        if ":" in paper_id:
            _, pubmed_id = paper_id.split(":", 1)
        else:
            pubmed_id = paper_id

        loop = asyncio.get_running_loop()

        # Fetch MEDLINE record for the paper
        handle = await loop.run_in_executor(
            None,
            lambda: Entrez.efetch(
                db="pubmed",
                id=pubmed_id,
                rettype="medline",
                retmode="text"
            )
        )

        records = await loop.run_in_executor(None, lambda: list(Medline.parse(handle)))
        handle.close()

        if not records:
            raise ValueError(f"PubMed paper with ID {pubmed_id} not found")

        record = records[0]

        # Parse author info
        authors = []
        if "AU" in record:
            for author_name in record["AU"]:
                authors.append(Author(name=author_name))

        # Parse date
        pub_date = None
        if "DP" in record:
            try:
                date_str = record["DP"].split("-")[0]
                pub_date = datetime.strptime(date_str, "%Y")
            except (ValueError, IndexError):
                pass

        # Parse DOI
        doi = None
        if "AID" in record:
            for aid in record["AID"]:
                if aid.endswith("[doi]"):
                    doi = aid.split(" ")[0]
                    break

        journal = record.get("TA", record.get("JT", None))

        return Paper(
            paper_id=f"pubmed:{record['PMID']}",
            title=record.get("TI", ""),
            authors=authors,
            abstract=record.get("AB", ""),
            url=f"https://pubmed.ncbi.nlm.nih.gov/{record['PMID']}/",
            pdf_url=None,
            publication_date=pub_date,
            journal=journal,
            doi=doi,
            source="pubmed",
            citations_count=None,
            raw_metadata={
                "mesh_terms": record.get("MH", []),
                "publication_types": record.get("PT", []),
                "keywords": record.get("OT", [])
            }
        )

    async def download_fulltext(self, paper_id: str) -> bytes:
        """
        Try to download the full-text PDF of a paper.
        This uses either:
        1. DOI to redirect to publisher
        2. PMC (PubMed Central) if available
        """
        await self._ensure_session()  # Ensure aiohttp session is initialized

        if ":" in paper_id:
            _, pubmed_id = paper_id.split(":", 1)
        else:
            pubmed_id = paper_id

        # Get metadata to retrieve DOI
        paper = await self.get_paper_metadata(f"pubmed:{pubmed_id}")

        if paper.doi:
            open_access_url = f"https://doi.org/{paper.doi}"

            # Try fetching from DOI redirect
            try:
                async with self._session.get(open_access_url, allow_redirects=True) as response:
                    if response.status == 200:
                        content_type = response.headers.get("Content-Type", "")
                        if "pdf" in content_type.lower():
                            return await response.read()
            except Exception:
                pass  # Continue to next fallback

        # Try to find full-text PDF from PMC
        loop = asyncio.get_running_loop()

        handle = await loop.run_in_executor(
            None,
            lambda: Entrez.elink(
                dbfrom="pubmed",
                id=pubmed_id,
                linkname="pubmed_pmc"
            )
        )
        link_results = await loop.run_in_executor(None, lambda: Entrez.read(handle))
        handle.close()

        pmc_id = None
        if link_results and link_results[0]["LinkSetDb"]:
            for link in link_results[0]["LinkSetDb"]:
                if link["LinkName"] == "pubmed_pmc":
                    for id_data in link["Link"]:
                        pmc_id = id_data["Id"]
                        break

        if pmc_id:
            pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"
            try:
                async with self._session.get(pmc_url) as response:
                    if response.status == 200:
                        return await response.read()
            except Exception:
                pass

        # No full-text PDF found
        raise ValueError(f"Could not find accessible full text for PubMed ID {pubmed_id}")

    @staticmethod
    def parse_paper_id(external_id: str) -> str:
        """
        Normalize user input to standardized paper ID format: pubmed:<id>
        Handles:
        - Raw IDs: "12345678"
        - PubMed URLs: "https://pubmed.ncbi.nlm.nih.gov/12345678/"
        - Already prefixed: "pubmed:12345678"
        """
        if external_id.startswith("pubmed:"):
            return external_id

        if "pubmed.ncbi.nlm.nih.gov" in external_id:
            parts = external_id.split("/")
            for part in parts:
                if part.isdigit():
                    return f"pubmed:{part}"

        if external_id.isdigit():
            return f"pubmed:{external_id}"

        return external_id
