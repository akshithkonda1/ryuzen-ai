import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from testops_backend.core.store import init_db
from testops_backend.tests_master.master_router import router as master_router

app = FastAPI(title="TestOps Backend", version="2.5H+")

# Restrict CORS to an explicit allowlist. Never combine a wildcard origin with
# credentials: Starlette reflects the request Origin in that case, which would
# let any website issue authenticated cross-origin requests. Configure origins
# via TESTOPS_CORS_ORIGINS (comma-separated); defaults to localhost for dev.
_cors_origins = [
    origin.strip()
    for origin in os.getenv("TESTOPS_CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "ok"


app.include_router(master_router)
