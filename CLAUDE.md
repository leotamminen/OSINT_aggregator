# OSINT Aggregator — Project Context

## What this is
A multi-agent Open Source Intelligence tool. User inputs a name/username,
the backend spins up parallel async agents that each search a different source,
and results stream to the UI in real-time via WebSocket.

## Current state: Phase 2 complete
Sherlock is the only agent. All mocks removed. Bare-domain results filtered out.

## Stack
- **Backend:** Python, FastAPI, asyncio, WebSocket (`main.py`)
- **Frontend:** Single-file HTML/CSS/JS (`frontend/index.html`)
- **No framework, no build step** — just `uvicorn main:app --reload`

## Run
```bash
pip install -r requirements.txt
python -m uvicorn main:app --port 9000 --reload
# → http://localhost:9000
```

## File structure
```
OSINT_aggregator/
├── main.py              # All backend logic. MOCK_AGENTS list is what gets
│                        # replaced per phase. search_ws() is the WebSocket
│                        # handler — do not restructure it, only add agents.
├── frontend/
│   └── index.html       # Fully self-contained. CSS at top, HTML in middle,
│                        # JS starts around line 530. handle() processes all
│                        # incoming WebSocket messages. Do not rename fields.
├── requirements.txt
├── CLAUDE.md
├── .gitignore
└── LICENSE
```

## Architecture
User input → FastAPI WebSocket `/ws/search` → `asyncio.gather()` runs all agents
concurrently → each agent sends `scanning` then `result` message → frontend
renders cards in real-time as they arrive.

### WebSocket message protocol
These field names are used by the frontend — do not change them.
```json
{ "type": "started",  "query": "...", "total": 5 }
{ "type": "scanning", "agent": "HIBP" }
{ "type": "result",   "agent": "HIBP", "status": "breach|found|not_found",
                       "findings": [...], "severity": "high|medium|low|none",
                       "elapsed": 0.9 }
{ "type": "complete" }
```

### Adding a real agent
1. Write `async def run_X(username, **kwargs) -> dict`
2. Return `{ status, findings, severity }`
3. Replace the matching entry in `MOCK_AGENTS` with a call to your function
4. The WebSocket wrapper in `search_ws()` handles the rest automatically

## What NOT to touch
- WebSocket message protocol — frontend depends on exact field names
- `search_ws()` function structure — only add agents, never restructure
- Frontend CSS variables — UI theme is intentional
- Agent pill IDs in HTML (`pill-HIBP`, `pill-GitHub` etc.) — JS relies on them

## Development phases
- [x] Phase 1 — Mock UI + WebSocket shell
- [x] Phase 2 — Sherlock (real agent, pip install sherlock-project)
- [ ] Phase 3 — WHOIS + agent chaining (domain found → auto WHOIS)
- [ ] Phase 4 — Dorking via DuckDuckGo (needs rate limiting)
- [ ] Phase 5 — GitHub (real API)
- [ ] Phase 6 — D3.js network graph visualization
- [ ] Phase 7 — Ollama AI synthesis (local LLM summary)

## Skipped
- HIBP — requires paid subscription (was Phase 2)

## Key decisions already made
- LinkedIn skipped entirely (blocks automation aggressively)
- Dorking uses DuckDuckGo not Google (avoids instant IP block)
- Ollama for LLM (free, local, no API cost)
- No database — stateless per search, results live in frontend only

## HIBP — skipped
Requires paid subscription. Not implemented.

## Sherlock notes (Phase 2 — done)
- `pip install sherlock-project`
- Runs via `asyncio.create_subprocess_exec`, output parsed for `[+]` lines
- `--print-found --no-color --timeout 15` flags; process timeout 120s
- Input is username: strip spaces, lowercase — done in `search_ws`
- `_find_sherlock()` locates the executable via `shutil.which` + venv Scripts fallback

## WHOIS notes (Phase 3)
- `pip install python-whois`
- Triggered automatically if Dorking or GitHub agent finds a domain
- This is agent chaining — WHOIS does not appear in initial MOCK_AGENTS,
  it launches dynamically when another agent returns a domain as a finding

## Dorking notes (Phase 4)
- Use DuckDuckGo via `pip install duckduckgo-search`
- Build queries like: `"Leo Tamminen" site:linkedin.com OR site:github.com`
- Add 2-3s delay between queries to avoid blocks
- Results are unpredictable — always handle empty gracefully

## Frontend UI notes
- Dark theme, accent color: `#00e5a0` (mint green)
- Severity → card border: high=red, medium=mint, low=gray, none=dimmed
- Agent pills update state: idle → scanning → found/breach/not_found
- Summary bar shows after `type: complete` message
- Location autocomplete has 35 cities hardcoded in CITIES array in JS
