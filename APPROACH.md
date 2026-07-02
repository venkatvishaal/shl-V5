# SHL Assessment Recommender — Approach Document

This project implements a stateless, production-grade assessment recommendation agent via FastAPI with `/health` and `/chat` HTTP endpoints.

## 1. Design & Architecture
The system is built on a stateless, turn-by-turn routing architecture:
- **Conversation Manager**: Handles turn routing, scope verification, and context extraction.
- **Scope Checker**: Intercepts requests to enforce safety guardrails, refusing unrelated requests (e.g., coding, medical advice) or prompt injection.
- **Behavior Handler**: Directs the flow into one of four distinct states (`Clarify`, `Recommend`, `Refine`, or `Compare`) or the `JD Recommend` fast-path.
- **Robust Fallback Engine**: If the LLM provider (Gemini) times out, encounters quota limits (429), or fails, the agent seamlessly falls back to a deterministic, keyword-driven categorical search engine to prevent user-facing downtime or malformed outputs.

## 2. Context Extraction & Phase Routing
Context and intent are extracted deterministically across user turns:
- **Role Extraction**: An extended regular expression scans messages for patterns like "hiring for a...", "we need a...", or "recruiting for...".
- **Seniority Extraction**: Matches level keywords using strict word boundaries (`\b`) to prevent false positives (e.g. `"lead"` matching `"leadership"`). Seniority found in the extracted role title (e.g. "Senior Software Engineer") overrides body-text mentions (e.g. "mentor junior engineers").
- **Skill Extraction**: Matches user terms against a targeted taxonomy, expanded to support domains like Accounting, HR, Operations, UX, Compliance, and Marketing.
- **JD Detection**: Dynamically classifies messages as JDs if they contain strong section headers (e.g. "Responsibilities:", "Requirements:") or exceed 50 words with weak signal words.
- **Phase Routing**: Differentiates between new requests, refinements (excluding career change phrases), and comparisons (checking for named assessments to avoid salary comparisons).

## 3. Grounding & Search Heuristics
Rather than a heavy vector database that can hallucinate url mappings, we implement an **In-Memory Categorical Heuristic Search**:
- **Categorical Signal Boosting**: Candidates are scored by matching category keywords (personality, verbal, numerical, simulation, reasoning).
- **Universal & Role-Specific Boosts**: Core cognitive and personality tests receive seniority-appropriate base boosts. Senior roles get cognitive boosts, and technical/leadership roles get specific test type nudges.
- **Name-Match Premium**: Canonical tests with keywords in their actual name (e.g., `"OPQ"`, `"Verify"`) receive a 1.5x multiplier.
- **Report Penalty**: Derivative reports (e.g., containing `"report"`, `"guide"`, `"profile"`) receive a `-3.0` penalty to ensure primary test instruments always rank higher.

## 4. Structured Output & Validation
- **LLM Prompting**: System instructions force the model to output a structured `RECOMMENDATIONS_JSON:` block.
- **Regex Extraction & Pydantic Validation**: The python layer extracts the JSON block via regex and parses it using a Pydantic schema, validating that all recommended URLs exist in the local catalog (`data/catalog.json`). Hallucinated recommendations are discarded.
- **Grounded Fallback**: If the JSON is missing or malformed, the deterministic scoring list is used.

## 5. Evaluation & Quality Metrics
We measure performance via an offline evaluation harness (`scripts/evaluate.py`) running 10 representative conversation traces:
- **Pytest Suite**: All `197 passed` unit/integration tests.
- **Mean Recall@10**: `92.59%` (significantly exceeding the $\ge 50\%$ assignment requirement).
- **Recall Standard Deviation**: `0.139` (exceeding the strict $< 0.30$ overfitting guardrail).
- **Hallucinations / Schema Failures**: `0`.

## 6. Deployment Readiness
The V3 project is fully containerized and submission-ready. A standard `Dockerfile` and a sanitized `.env` template are provided for deployment on platforms like Render or Railway.
