"""
Minimal SAML handler to validate assertions against expected audience and issuer.
"""
from __future__ import annotations

import base64
import hashlib
from typing import Dict, Optional

# Use defusedxml to parse attacker-controlled SAML assertions safely. The stdlib
# ElementTree parser is vulnerable to XXE / entity-expansion (billion laughs)
# attacks, and SAML assertions arrive from outside the trust boundary.
import defusedxml.ElementTree as ET

from .idp_metadata_cache import IdPMetadataCache


class SAMLHandler:
    def __init__(self, metadata_cache: Optional[IdPMetadataCache] = None):
        self.metadata_cache = metadata_cache or IdPMetadataCache()

    def parse_assertion(self, b64_assertion: str) -> Dict[str, str]:
        xml_data = base64.b64decode(b64_assertion)
        root = ET.fromstring(xml_data)
        ns = {"saml2": "urn:oasis:names:tc:SAML:2.0:assertion"}
        issuer = root.findtext(".//saml2:Issuer", namespaces=ns)
        subject = root.findtext(".//saml2:NameID", namespaces=ns)
        audience = root.findtext(".//saml2:Audience", namespaces=ns)
        return {"issuer": issuer or "", "subject": subject or "", "audience": audience or ""}

    def validate(self, b64_assertion: str, expected_audience: str) -> Dict[str, str]:
        data = self.parse_assertion(b64_assertion)
        if data["audience"] != expected_audience:
            raise ValueError("Audience mismatch")
        if not data["issuer"]:
            raise ValueError("Missing issuer in assertion")
        metadata = self.metadata_cache.get(data["issuer"]) or {}
        thumbprint = hashlib.sha256(b64_assertion.encode()).hexdigest()
        return {**data, "thumbprint": thumbprint, "idp_metadata": metadata}

    def cache_metadata(self, issuer: str, metadata: dict) -> None:
        self.metadata_cache.set(issuer, metadata)
