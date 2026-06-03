"""PubMed connector for medical research."""

import logging
from typing import List
import aiohttp
# defusedxml guards against XXE / entity-expansion in external API responses.
import defusedxml.ElementTree as ET

from ..base import Tier3Connector, KnowledgeSnippet, SourceCategory

logger = logging.getLogger(__name__)


class PubMedConnector(Tier3Connector):
    """PubMed API for medical literature (NIH)."""

    SEARCH_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self):
        super().__init__(
            source_name="PubMed-API",
            reliability=0.94,
            category=SourceCategory.MEDICAL,
            enabled=True
        )
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self._session

    async def fetch(self, query: str, max_results: int = 3) -> List[KnowledgeSnippet]:
        try:
            session = await self._get_session()

            # Search for article IDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "xml",
                "sort": "relevance"
            }

            async with session.get(self.SEARCH_BASE, params=search_params) as response:
                if response.status != 200:
                    logger.warning(f"PubMed search: {response.status}")
                    self._record_error()
                    return []
                search_xml = await response.text()

            root = ET.fromstring(search_xml)
            ids = [id_elem.text for id_elem in root.findall(".//Id") if id_elem.text]

            if not ids:
                self._record_success()
                return []

            # Fetch abstracts
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "xml",
                "rettype": "abstract"
            }

            async with session.get(self.FETCH_BASE, params=fetch_params) as response:
                if response.status != 200:
                    logger.warning(f"PubMed fetch: {response.status}")
                    self._record_error()
                    return []
                fetch_xml = await response.text()

            articles_root = ET.fromstring(fetch_xml)
            snippets = []

            for article in articles_root.findall(".//PubmedArticle"):
                title_elem = article.find(".//ArticleTitle")
                abstract_elem = article.find(".//AbstractText")
                pmid_elem = article.find(".//PMID")

                # Get authors
                authors = []
                for author in article.findall(".//Author"):
                    last_name = author.find("LastName")
                    first_name = author.find("ForeName")
                    if last_name is not None and last_name.text:
                        name = last_name.text
                        if first_name is not None and first_name.text:
                            name = f"{first_name.text} {name}"
                        authors.append(name)

                # Get journal info
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else None

                # Get publication date
                pub_date = article.find(".//PubDate")
                year = pub_date.find("Year") if pub_date is not None else None
                pub_year = year.text if year is not None else None

                if title_elem is not None:
                    title = title_elem.text or ""
                    abstract = abstract_elem.text if abstract_elem is not None else ""
                    pmid = pmid_elem.text if pmid_elem is not None else ""

                    content = f"{title}\n\n{abstract}" if abstract else title
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None

                    snippet = KnowledgeSnippet(
                        source_name=self.source_name,
                        content=content[:2000],
                        reliability=self.reliability,
                        category=self.category,
                        url=url,
                        metadata={
                            "pmid": pmid,
                            "type": "medical_research",
                            "authors": authors[:5],
                            "journal": journal,
                            "year": pub_year
                        }
                    )
                    snippets.append(snippet)

            self._record_success()
            return snippets[:max_results]

        except Exception as e:
            logger.error(f"PubMed error: {e}")
            self._record_error()
            return []

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
