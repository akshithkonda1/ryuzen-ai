"""Wolfram Alpha connector for computational knowledge."""

import logging
import os
from typing import List, Optional
import aiohttp
# defusedxml guards against XXE / entity-expansion in external API responses.
import defusedxml.ElementTree as ET

from ..base import Tier3Connector, KnowledgeSnippet, SourceCategory

logger = logging.getLogger(__name__)


class WolframAlphaConnector(Tier3Connector):
    """
    Wolfram Alpha Full Results API connector.

    Requires:
    - WOLFRAM_APP_ID: App ID from Wolfram Alpha Developer Portal

    API docs: https://products.wolframalpha.com/api/documentation
    """

    API_BASE = "http://api.wolframalpha.com/v2/query"
    SHORT_API = "http://api.wolframalpha.com/v1/result"

    def __init__(self, app_id: Optional[str] = None):
        super().__init__(
            source_name="WolframAlpha-API",
            reliability=0.95,
            category=SourceCategory.GENERAL,
            enabled=True,
            requires_api_key=True
        )
        self.app_id = app_id or os.environ.get("WOLFRAM_APP_ID")
        self._session = None

        if not self.app_id:
            logger.warning("Wolfram Alpha: Missing App ID, connector will return empty results")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=20)  # Wolfram can be slow
            )
        return self._session

    async def fetch(self, query: str, max_results: int = 3) -> List[KnowledgeSnippet]:
        if not self.app_id:
            logger.debug("Wolfram Alpha: No App ID configured")
            return []

        try:
            session = await self._get_session()

            # Try full results API first
            params = {
                "appid": self.app_id,
                "input": query,
                "format": "plaintext",
                "output": "xml",
            }

            async with session.get(self.API_BASE, params=params) as response:
                if response.status != 200:
                    logger.warning(f"Wolfram Alpha: {response.status}")
                    self._record_error()
                    return []

                xml_data = await response.text()

            # Parse XML response
            root = ET.fromstring(xml_data)

            if root.get("success") != "true":
                # Try short answer API as fallback
                return await self._fetch_short_answer(session, query)

            snippets = []
            pods = root.findall(".//pod")

            for pod in pods[:max_results * 2]:
                pod_title = pod.get("title", "")

                # Skip input interpretation
                if pod_title.lower() in ["input", "input interpretation"]:
                    continue

                # Get plaintext from subpods
                subpods = pod.findall(".//subpod")
                pod_content = []

                for subpod in subpods:
                    plaintext = subpod.find("plaintext")
                    if plaintext is not None and plaintext.text:
                        text = plaintext.text.strip()
                        if text:
                            pod_content.append(text)

                if pod_content:
                    content = f"{pod_title}:\n" + "\n".join(pod_content)

                    snippet = KnowledgeSnippet(
                        source_name=self.source_name,
                        content=content[:1500],
                        reliability=self.reliability,
                        category=self.category,
                        url=f"https://www.wolframalpha.com/input?i={query.replace(' ', '+')}",
                        metadata={
                            "pod_title": pod_title,
                            "type": "computational_knowledge",
                            "scanner": pod.get("scanner", ""),
                        }
                    )
                    snippets.append(snippet)

            self._record_success()
            return snippets[:max_results]

        except Exception as e:
            logger.error(f"Wolfram Alpha error: {e}")
            self._record_error()
            return []

    async def _fetch_short_answer(
        self,
        session: aiohttp.ClientSession,
        query: str
    ) -> List[KnowledgeSnippet]:
        """Fallback to short answer API."""
        try:
            params = {
                "appid": self.app_id,
                "i": query,
            }

            async with session.get(self.SHORT_API, params=params) as response:
                if response.status == 200:
                    answer = await response.text()
                    if answer and not answer.startswith("Wolfram|Alpha did not understand"):
                        return [KnowledgeSnippet(
                            source_name=self.source_name,
                            content=answer,
                            reliability=self.reliability,
                            category=self.category,
                            url=f"https://www.wolframalpha.com/input?i={query.replace(' ', '+')}",
                            metadata={"type": "short_answer"}
                        )]
            return []
        except Exception:
            return []

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
