# SHL Assessment Recommender

Conversational AI agent that recommends SHL assessments to hiring managers and recruiters through multi-turn dialogue. Built with FastAPI.

## Features

- **Multi-turn conversation**: Clarify requirements through natural dialogue
- **Smart recommendations**: 1-10 ranked assessments based on role, skills, seniority
- **Job description parsing**: Paste a JD and get immediate recommendations
- **Mid-conversation refinement**: Update constraints without restarting
- **Assessment comparison**: Compare assessments using catalog data
- **Scope boundaries**: Stays within SHL catalog; refuses off-topic requests

## Quick Start

### Prerequisites
- Python 3.9+
- API key from one of: Anthropic, OpenAI, Gemini, or Groq

### Setup

```bash
# Clone and enter the project
cd shl-V5

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API key and provider

# Run the service
python main.py
```

### Test the service

```bash
# Health check
curl http://localhost:8000/health

# Chat with the agent
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I need to hire a Java developer"}]}'

# Run tests
pytest tests/ -v
```

## API Endpoints

### `GET /health`
Returns service readiness status.

### `POST /chat`
Main conversation endpoint.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Hiring a senior Java developer who works with stakeholders"}
  ]
}
```

**Response:**
```json
{
  "reply": "Here are some assessments that match...",
  "recommendations": [
    {
      "name": "Java 8 (New)",
      "url": "https://www.shl.com/solutions/products/java-8-new/",
      "test_type": "K"
    }
  ],
  "end_of_conversation": false
}
```

## Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI Web Service             │
│   (/health, /chat, /docs)              │
├─────────────────────────────────────────┤
│  Conversation Manager                   │
│  (turn tracking, context extraction)    │
├─────────────────────────────────────────┤
│  Agent Logic                            │
│  (clarify, recommend, refine, compare)  │
├─────────────────────────────────────────┤
│  LLM Integration                        │
│  (Anthropic, OpenAI, Gemini, Groq)     │
├─────────────────────────────────────────┤
│  Retrieval Layer                        │
│  (deterministic heuristic search)       │
├─────────────────────────────────────────┤
│  Catalog Data                           │
│  (JSON catalog of SHL assessments)      │
└─────────────────────────────────────────┘
```

## Project Structure

```
shl-V5/
├── main.py                 # FastAPI entry point
├── config.py               # Configuration management
├── src/
│   ├── api/
│   │   ├── schemas.py      # Pydantic request/response models
│   │   └── endpoints.py    # /health and /chat route handlers
│   ├── agent/
│   │   ├── conversation_manager.py  # Multi-turn conversation logic
│   │   ├── behavior_handler.py      # Clarify, recommend, refine, compare
│   │   ├── scope_checker.py         # Boundary enforcement
│   │   └── constants.py             # Agent keyword lists and constants
│   ├── retrieval/
│   │   └── catalog.py      # Catalog data management
│   ├── llm/
│   │   ├── client.py       # LLM API wrapper (multi-provider)
│   │   └── prompts.py      # System/user prompt templates
│   └── utils/
│       └── logger.py       # Custom logging configuration
├── data/
│   └── catalog.json        # SHL assessment catalog
├── tests/
│   ├── test_endpoints.py   # API endpoint tests
│   ├── test_conversation.py # Conversation behavior tests
│   ├── test_agent.py       # Agent logic unit tests
│   └── test_retrieval.py   # Retrieval/search tests
├── requirements.txt
├── .env.example
└── README.md
```

## Key Design Decisions

1. **Stateless API**: Full conversation history in each request; no server-side state
2. **Raw LLM SDK**: No LangChain/LlamaIndex; direct control over prompts and validation
3. **Deterministic search**: High-performance heuristic keyword scoring for robust retrieval
4. **Validation-first**: All recommendations validated against catalog before returning
5. **Behavior-based routing**: Conversation phase determines which behavior to use

## Conversation Behaviors

| Behavior | Trigger | Output |
|----------|---------|--------|
| Clarify | Vague input, insufficient context | Questions to gather info |
| Recommend | Sufficient context gathered | 1-10 assessments with explanations |
| Refine | "Actually...", "Add...", "Change..." | Updated recommendations |
| Compare | "Difference between X and Y" | Factual comparison from catalog |
| Refuse | Off-topic, legal, prompt injection | Polite redirection |

## Supported LLM Providers

- **Anthropic Claude** (recommended): `claude-3-sonnet-20240229`
- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Google Gemini**: gemini-pro
- **Groq**: Fast inference with various models

Set `LLM_PROVIDER` in `.env` and provide the corresponding API key.

## Development

```bash
# Run tests
pytest tests/ -v

# Run with auto-reload
uvicorn main:app --reload --port 8000

# View API docs
open http://localhost:8000/docs
```

## License

MIT
