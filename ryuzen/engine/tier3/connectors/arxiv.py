"""ArXiv connector for research papers."""

import logging
from typing import List
import aiohttp
# defusedxml guards against XXE / entity-expansion in external API responses.
import defusedxml.ElementTree as ET

from ..base import Tier3Connector, KnowledgeSnippet, SourceCategory

logger = logging.getLogger(__name__)


class ArxivConnector(Tier3Connector):
    """ArXiv API for research preprints and papers."""

    API_BASE = "http://export.arxiv.org/api/query"

    def __init__(self):
        super().__init__(
            source_name="Arxiv-API",
            reliability=0.93,
            category=SourceCategory.ACADEMIC,
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
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }

            async with session.get(self.API_BASE, params=params) as response:
                if response.status != 200:
                    logger.warning(f"ArXiv: {response.status}")
                    self._record_error()
                    return []

                xml_data = await response.text()

            root = ET.fromstring(xml_data)
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            snippets = []

            for entry in root.findall('atom:entry', namespace):
                title = entry.find('atom:title', namespace)
                summary = entry.find('atom:summary', namespace)
                link = entry.find('atom:id', namespace)
                published = entry.find('atom:published', namespace)

                # Get authors
                authors = []
                for author in entry.findall('atom:author', namespace):
                    name = author.find('atom:name', namespace)
                    if name is not None and name.text:
                        authors.append(name.text)

                # Get categories
                categories = []
                for cat in entry.findall('atom:category', namespace):
                    term = cat.get('term')
                    if term:
                        categories.append(term)

                if title is not None and summary is not None:
                    title_text = " ".join(title.text.split()) if title.text else ""
                    summary_text = " ".join(summary.text.split()) if summary.text else ""
                    content = f"{title_text}\n\n{summary_text}"

                    snippet = KnowledgeSnippet(
                        source_name=self.source_name,
                        content=content[:2000],
                        reliability=self.reliability,
                        category=self.category,
                        url=link.text if link is not None else None,
                        metadata={
                            "type": "research_paper",
                            "authors": authors[:5],  # Limit to 5 authors
                            "categories": categories,
                            "published": published.text if published is not None else None
                        }
                    )
                    snippets.append(snippet)

            self._record_success()
            return snippets[:max_results]

        except Exception as e:
            logger.error(f"ArXiv error: {e}")
            self._record_error()
            return []

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
