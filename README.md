# OSINT Aggregator

Open Source Intelligence aggregator — real-time multi-agent search.

## Current phase: 1 (Mock UI + WebSocket shell)

All agents return mock data. The architecture is complete and ready for real agents.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the backend
uvicorn main:app --reload

# 3. Open in browser
# http://localhost:8000
```

## Development phases

- [x] **Phase 1** — FastAPI + WebSocket shell, mock agents, full UI
- [ ] **Phase 2** — HIBP real agent
- [ ] **Phase 3** — Sherlock real agent
- [ ] **Phase 4** — WHOIS + agent chaining
- [ ] **Phase 5** — Dorking (DuckDuckGo)
- [ ] **Phase 6** — D3.js network graph
- [ ] **Phase 7** — Ollama AI synthesis

## Project structure

```
osint-aggregator/
├── main.py              # FastAPI backend + WebSocket endpoint
├── requirements.txt
├── frontend/
│   └── index.html       # Single-page UI
└── README.md
```

## Adding a real agent (Phase 2+)

Replace the corresponding entry in `MOCK_AGENTS` in `main.py` with a real
async function. The WebSocket protocol (`scanning` → `result`) stays the same.
# OSINT_aggregator
