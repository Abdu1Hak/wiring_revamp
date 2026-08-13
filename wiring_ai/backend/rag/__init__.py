# rag/ package
# -------------
# This package implements the Retrieval-Augmented Generation (RAG) pipeline.
# It has 3 modules:
#   - ingestor.py  : Fetches datasheets (PDF/URL) and splits text into chunks
#   - embedder.py  : Converts text chunks into 768-dim vectors via Gemini
#   - retriever.py : Manages the Qdrant "datasheets" collection and searches it
