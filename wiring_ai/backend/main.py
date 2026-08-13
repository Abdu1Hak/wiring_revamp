# main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.preprocess import router as preprocess_router
from api.routes.components import router as components_router  # your existing route
from mcp_.server import mcp

logging.basicConfig(level=logging.INFO)



# ── App Creation ──────────────────────────────────────────────────────────────
app = FastAPI(title="Wiring AI", version="0.1.0")

# ── CORS (allow your Vite frontend to call the API) ───────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount MCP server ──────────────────────────────────────────────────────────
app.mount("/mcp", mcp.sse_app())

@app.get("/")
def root():
    return {"message": "Wiring AI backend is running"}

# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(components_router)   # GET  /api/components
app.include_router(preprocess_router)   # POST /api/preprocess/onboard