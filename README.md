# Agentic Software Engineering System - URL Shortener

This repository contains an **Agentic Software Engineering System** designed to drive requirements through the software development lifecycle (SDLC) autonomously, producing a functional, production-ready URL Shortener product.

The primary deliverable of this assignment is the **orchestration layer** that manages requirement understanding, design, task decomposition, implementation, testing, and release readiness.

---

## 🛠️ Architecture Overview

The system is split into two primary components:
1. **The Orchestrator Engine (`/orchestrator`)**: Built using **LangGraph** to construct a state-based Directed Acyclic Graph (DAG) representing the SDLC. It implements entry/exit gates, state checkpointers (via SQLite), human approval checkpoints, and observability logging.
2. **The Product (`/product`)**: A minimal, lean URL shortener backend built with **FastAPI**, **SQLAlchemy**, and **SQLite** generated automatically by the Orchestrator.

```text
/
├── orchestrator/          # The core SDLC orchestrator engine (LangGraph)
│   ├── engine/            # DAG runner, state management, and metrics
│   ├── agents/            # Prompts, nodes, and LLM integrations
│   └── gates/             # AST check and security guardrails
├── product/               # The generated URL Shortener service
│   ├── app/               # FastAPI backend codebase
│   └── tests/             # Generated test suite
└── runs/                  # Local run logs (JSONL) and SQLite state DBs
```

---

## 🚀 Steps Accomplished

1. **Architecture Planning**: Designed a stateful SDLC execution loop with human-in-the-loop gates and SQLite database checkpointers.
2. **DAG Implementation**: Built a graph using **LangGraph** with nodes representing:
   - **Requirements**: Normalizes feature request inputs.
   - **Design**: Plans files and architecture specs.
   - **Decomposition**: Translates the design into discrete coding tasks.
   - **Implementation**: Generates code with Python syntax and secret checks.
   - **Testing**: Synthesizes a matching testing suite.
   - **Release Readiness**: Packages artifacts to disk on approval.
3. **Observability Mapping**: Implemented a JSONL event logger capturing latency, tokens, retries, and errors to calculate MTTR and success rates.
4. **Mock Safeguard Integration**: Built a dual-mode execution switch (mock LLM vs. real Groq LLM) to prevent hitting strict 30 requests/day limits during orchestration testing.
5. **Product Generation**: Run the orchestrator end-to-end to generate a lean, functional URL shortener complete with collision-safe shortening hashes, redirect routes, Pydantic schemas, and unit tests.

---

## 🏃 How to Run the Project

### 1. Setup the Environment
Clone the repository and set up a virtual environment from the root directory:

```bash
# Setup virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install orchestrator dependencies
pip install -e .
```

---

### 2. Run the Orchestrator Scenarios

Before running, if you want to use the real LLM (Groq API) instead of Mock mode, configure your API credentials in your environment:
```powershell
$env:QROQ_API_KEY="your_groq_api_key"
$env:QROQ_BASE_URL="https://api.groq.com/openai/v1"
```

#### **Scenario A: Greenfield (Build New Service)**
Generates the base URL shortener service from scratch.
* **Mock Mode (No API keys required)**:
  ```bash
  python -m orchestrator.main --scenario "greenfield" --requirement "Build a minimal lean URL shortener API with FastAPI that saves to SQLite"
  ```
* **Groq Production Mode**:
  ```bash
  # Ensure QROQ_API_KEY is set
  python -m orchestrator.main --scenario "greenfield" --requirement "Build a minimal lean URL shortener API with FastAPI that saves to SQLite"
  ```

#### **Scenario B: Brownfield (Enhance Existing Service)**
Adds redirection analytics tracking and the stats endpoint on top of the existing codebase.
* **Mock Mode (No API keys required)**:
  ```bash
  python -m orchestrator.main --scenario "brownfield" --requirement "Enhance the existing URL shortener to track redirection usage. Add a clicks counter to the URLMap database model. For every redirect, increment the counter. Expose a new API endpoint GET /analytics/{code} returning the target URL and total clicks."
  ```
* **Groq Production Mode**:
  ```bash
  # Ensure QROQ_API_KEY is set
  python -m orchestrator.main --scenario "brownfield" --requirement "Enhance the existing URL shortener to track redirection usage. Add a clicks counter to the URLMap database model. For every redirect, increment the counter. Expose a new API endpoint GET /analytics/{code} returning the target URL and total clicks."
  ```

#### **Scenario C: Ambiguous (Interpret and Resolve)**
Provides a vague requirement (e.g. *"make safety better"* and *"make redirects dynamic"*) to demonstrate how the orchestrator PM agent identifies, resolves, and documents ambiguity automatically.
* **Mock Mode (No API keys required)**:
  ```bash
  python -m orchestrator.main --scenario "ambiguous" --requirement "Improve URL shortener backend safety and redirect features. We want to protect it but we also want the redirects to be dynamic and fast."
  ```
* **Groq Production Mode**:
  ```bash
  # Ensure QROQ_API_KEY is set
  python -m orchestrator.main --scenario "ambiguous" --requirement "Improve URL shortener backend safety and redirect features. We want to protect it but we also want the redirects to be dynamic and fast."
  ```

---

### 3. Run and Test the Generated URL Shortener
The product generated by the orchestrator resides inside the `/product` directory.

#### **A. Run Pytest**
Ensure `pytest` is installed in your venv, navigate to `product/`, and run:
```bash
cd product
pip install pytest
python -m pytest
```

#### **B. Run the FastAPI Server**
Start the application:
```bash
python -m uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger docs will be hosted at `http://localhost:8000/docs`.

---

## 📈 Observability & Metrics
Every orchestrator execution creates a state directory in `runs/run_<run_uuid>/`.
- **`state.sqlite`**: Fully queryable relational database tracking stage results, retry counts, task lists, and checkpoints.
- **`events.jsonl`**: Captures event timestamps, latency (`duration_ms`), stage types, and errors. Useful for calculating:
  - **Success Rate**: Successful runs vs. Total runs.
  - **MTTR (Mean Time to Recovery)**: Delay between a fail event and subsequent recovery.
  - **E2E Latency**: Time elapsed from `Requirements` start to `ReleaseReadiness` end.

---

## 🔬 Testing Approach, Limitations & Trade-offs

### 1. Testing Approach
- **Orchestrator Validation Gates**: The orchestrator protects the target product code using an AST-based syntax validator before writing any files. If validation fails, it routes execution back to the implementation stage with the syntax errors injected as feedback, allowing the model to self-heal.
- **Product Test Isolation**: Product unit tests run in isolation using a file-based SQLite database (`test.db`) that is generated and cleanly deleted after the test session to avoid dirty testing state.

### 2. Limitations & Trade-offs
- **In-Memory Rate Limiting**:
  - *Trade-off*: Implemented an in-memory sliding window rate limiter in [`main.py`](file:///c:/Users/varan/Projects/AI_Agent_URL_Shortner/product/app/main.py) for simplicity, performance, and keeping zero external dependencies.
  - *Limitation*: Application restarts clear all rate limit counters. It does not scale horizontally. In a multi-instance production environment, a Redis-backed rate limiter is required.
- **SQLite Database**:
  - *Trade-off*: SQLite is lightweight, serverless, and perfect for a lean URL shortener where read performance (redirection lookup) is dominant.
  - *Limitation*: Under heavy concurrent write operations (e.g. bulk URL shortening), SQLite will suffer from write-locking. A transition to PostgreSQL is advised for high-throughput production.
- **LLM Token & Rate Limits (TPM)**:
  - *Trade-off*: To operate within the 8,000 TPM limit of Groq/openai APIs during code generation, the orchestrator spaces task loops with 15-second delays and prompts the Design/Decomposition nodes to consolidate code changes into at most 2 files.
  - *Limitation*: While highly cost-effective and safe against rate limits, it increases the end-to-end execution latency of the orchestrator.

### 3. Engineering Decisions & Judgments
- **Simplified Settings wrapper**: Replaced complex Pydantic `BaseSettings` configurations with a native Python settings wrapper. This avoids version conflict imports (Pydantic V1 vs V2 migration bugs) while maintaining identical functionality.
- **SSRF / Loopback Protection**: Rather than just validating URL syntax, the shortener resolves target hostnames to block localhost and private IPv4 ranges (10.x, 192.168.x, 172.16-31.x). This prevents malicious users from utilizing the shortener to run Server-Side Request Forgery (SSRF) attacks against internal endpoints.
