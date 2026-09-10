# Wiring AI

Wiring AI is an AI-assisted hardware design tool that converts natural-language project requirements into validated, pin-level wiring plans across a growing hardware component catalog.

The system combines **LangGraph**, **Qdrant**, **PostgreSQL**, **Redis**, and **ReactFlow** with datasheet-grounded RAG and deterministic validation logic to generate, verify, and automatically repair circuit connections.

## What it does

- Converts project descriptions into structured hardware requirements
- Selects compatible components from a 100+ component catalog
- Retrieves datasheet and pinout information using RAG
- Generates pin-level wiring connections
- Validates electrical and logical compatibility
- Detects invalid connections and attempts automatic rewiring
- Maintains project context and session state across the workflow
- Visualizes generated circuits through an interactive ReactFlow interface

## Architecture

Wiring AI uses a **13-stage stateful agent pipeline** covering:

`Project Input → Component Selection → Datasheet Retrieval → Circuit Generation → Validation → Error Detection → Automatic Rewiring → Final Circuit`

The goal is to combine LLM reasoning with deterministic electrical constraints rather than relying purely on model-generated wiring.

## Tech Stack

**Backend:** Python, LangGraph, FastAPI  
**AI / Retrieval:** Qdrant, RAG, LLM APIs  
**Data:** PostgreSQL, Redis  
**Frontend:** React / ReactFlow

## Project Status

> **Wiring AI is currently under active development.**

The core architecture and generation pipeline are functional, but I am continuing to improve reliability, expand component coverage, handle edge cases, and resolve integration and production-level bugs before considering the system production-ready.

Current work includes improving validation accuracy, failure recovery, datasheet ingestion, and evaluation of generated circuits across a wider range of hardware projects.

## Roadmap

- Expand hardware component and datasheet coverage
- Build a systematic evaluation suite for circuit-generation quality
- Measure invalid-connection and automatic-recovery rates
- Improve handling of ambiguous project requirements
- Add stronger electrical constraint validation
- Improve frontend circuit visualization and editing
- Harden the system against production edge cases

## Disclaimer

Generated circuits should currently be treated as **engineering assistance rather than verified production designs**. Hardware connections should be manually reviewed before being used on physical systems.
