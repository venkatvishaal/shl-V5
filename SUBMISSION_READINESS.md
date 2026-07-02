# Submission Readiness

Verdict: locally ready for submission, pending public deployment.

## What is implemented

- Required endpoints: `GET /health`, `POST /chat`.
- Stateless full-history `/chat` contract.
- Enforced maximum of 8 total conversation messages including the generated assistant response.
- Clarifying questions for vague requests.
- 1-10 catalog-only recommendations.
- Constraint refinement for duration, required assessment types, and excluded assessment types.
- Catalog-grounded assessment comparisons.
- Prompt-injection/off-topic/legal-safety refusals.
- Deterministic fallback ranking that works without external LLM latency.
- Gemini LLM path enabled through `.env`.
- LLM path protected by an 8-second timeout, with deterministic fallback before the assignment's 30-second cap.
- Offline catalog audit and behavioral evaluation.

## Latest validation

Commands run from `C:\TSVV\SHL\shl-V1`:

```powershell
& '..\venv\Scripts\python.exe' -m pytest tests -q
& '..\venv\Scripts\python.exe' scripts\evaluate.py
& '..\venv\Scripts\python.exe' scripts\catalog_audit.py
& '..\venv\Scripts\python.exe' scripts\verify_gemini_llm.py
```

Results:

- Full tests: `174 passed`.
- Assignment-compliance tests: `8 passed`.
- Evaluator: `ALL CHECKS PASSED`.
- Mean Recall@10: `94.44%`.
- Hallucinations: `0`.
- Schema failures: `0`.
- Catalog size: `368` assessments.
- Unique names: `368`.
- Unique URLs: `368`.
- Invalid SHL URL formats: `0`.

Note: `pytest tests` intentionally skips slow replay suites by default. Run them explicitly with:

```powershell
& '..\venv\Scripts\python.exe' -m pytest tests\test_traces_eval.py tests\test_overfitting.py -m slow -q
```

## Not yet done

- Public deployment URL is not created in this workspace.

## Recommended final submission checklist

1. Deploy `C:\TSVV\SHL\shl-V1`.
2. Call public `GET /health` and confirm `{"status": "ok"}`.
3. Call public `POST /chat` with a sample vague query and a sample JD query.
4. Include `APPROACH.md`, validation results, and public API URL in the submission.
