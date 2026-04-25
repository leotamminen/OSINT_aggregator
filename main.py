import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="OSINT Aggregator")

# ─────────────────────────────────────────
# MOCK AGENT DATA — replace with real agents in later phases
# ─────────────────────────────────────────
MOCK_AGENTS = [
    {
        "agent": "HIBP",
        "delay": 0.9,
        "status": "breach",
        "findings": [
            "Found in 3 data breaches",
            "Adobe (Oct 2013) — email + password hash",
            "LinkedIn (May 2016) — email + password hash",
            "Dropbox (Jul 2012) — email + password hash",
        ],
        "severity": "high",
    },
    {
        "agent": "GitHub",
        "delay": 1.5,
        "status": "found",
        "findings": [
            "Profile: github.com/{username}",
            "32 public repositories",
            "Primary languages: Python, JavaScript",
            "Email in commits: {username}@example.com",
            "Active contributor since 2020",
        ],
        "severity": "medium",
    },
    {
        "agent": "Sherlock",
        "delay": 4.2,
        "status": "found",
        "findings": [
            "twitter.com/{username}",
            "reddit.com/u/{username}",
            "dev.to/{username}",
            "news.ycombinator.com/user?id={username}",
            "pypi.org/user/{username}",
        ],
        "severity": "medium",
    },
    {
        "agent": "Dorking",
        "delay": 2.3,
        "status": "found",
        "findings": [
            "LinkedIn profile indexed publicly",
            "Conference speaker bio (2023)",
            "University thesis PDF indexed",
        ],
        "severity": "low",
    },
    {
        "agent": "WHOIS",
        "delay": 0.6,
        "status": "not_found",
        "findings": [
            "No domain registrations found",
        ],
        "severity": "none",
    },
]


@app.websocket("/ws/search")
async def search_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        query = data.get("query", "target")
        username = query.lower().replace(" ", "")

        await websocket.send_json({
            "type": "started",
            "query": query,
            "total": len(MOCK_AGENTS),
        })

        async def run_agent(agent_data: dict):
            # Notify frontend: agent is starting
            await websocket.send_json({
                "type": "scanning",
                "agent": agent_data["agent"],
            })

            # Simulate work (replace with real logic in later phases)
            await asyncio.sleep(agent_data["delay"])

            # Substitute username placeholder in findings
            findings = [
                f.replace("{username}", username)
                for f in agent_data["findings"]
            ]

            await websocket.send_json({
                "type": "result",
                "agent": agent_data["agent"],
                "status": agent_data["status"],
                "findings": findings,
                "severity": agent_data["severity"],
                "elapsed": round(agent_data["delay"], 1),
            })

        # All agents run concurrently — results arrive as each finishes
        await asyncio.gather(*[run_agent(a) for a in MOCK_AGENTS])

        await websocket.send_json({"type": "complete"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# Static files mount must come AFTER all route definitions
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
