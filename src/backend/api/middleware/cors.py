"""CORS middleware configuration for the backend API layer.

Origins are read from the RYUZEN_CORS_ORIGINS environment variable
(comma-separated) and default to localhost for development. A wildcard origin is
only honored when credentials are disabled; combining ``*`` with credentials is
rejected because it effectively allows any site to make authenticated requests.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def apply_cors(app: FastAPI) -> None:
    """Apply a CORS policy driven by RYUZEN_CORS_ORIGINS.

    Set RYUZEN_CORS_ORIGINS to a comma-separated allowlist of origins for the
    deployment. Defaults to http://localhost:3000 for local development.
    """

    origins = [
        origin.strip()
        for origin in os.getenv("RYUZEN_CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]
    allow_credentials = "*" not in origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

