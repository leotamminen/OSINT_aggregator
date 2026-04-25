import asyncio
import os
import shutil
import subprocess
import sys
import sysconfig
import time
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="OSINT Aggregator")


# ── GitHub ────────────────────────────────────────────────────────────────────

async def run_github(username: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.github.com/users/{username}",
                headers={"Accept": "application/vnd.github+json"},
            )

        if resp.status_code == 404:
            return {"status": "not_found", "findings": ["No GitHub account found"], "severity": "none"}

        resp.raise_for_status()
        d = resp.json()

        findings = [f"https://github.com/{username}"]
        if d.get("name"):       findings.append(f"Name: {d['name']}")
        if d.get("bio"):        findings.append(f"Bio: {d['bio']}")
        if d.get("location"):   findings.append(f"Location: {d['location']}")
        if d.get("email"):      findings.append(f"Email: {d['email']}")
        if d.get("blog"):       findings.append(f"Website: {d['blog']}")
        if d.get("company"):    findings.append(f"Company: {d['company']}")
        findings.append(f"Public repos: {d.get('public_repos', 0)}  ·  Followers: {d.get('followers', 0)}")
        if d.get("created_at"): findings.append(f"Account created: {d['created_at'][:10]}")

        return {"status": "found", "findings": findings, "severity": "medium"}

    except httpx.HTTPStatusError as e:
        return {"status": "not_found", "findings": [f"GitHub API error {e.response.status_code}"], "severity": "none"}
    except Exception as e:
        return {"status": "not_found", "findings": [f"Error: {e}"], "severity": "none"}


# ── Dorking ──────────────────────────────────────────────────────────────────

async def run_dorking(username: str) -> dict:
    def _blocking():
        from ddgs import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(f'"{username}"', max_results=10)) or []

    try:
        results = await asyncio.to_thread(_blocking)

        findings = []
        seen = set()
        for r in results:
            url = r.get("href", "")
            title = r.get("title", "").strip()
            if not url or url in seen:
                continue
            if not urlparse(url).path.rstrip("/"):
                continue
            # GitHub is covered by its own agent
            if "github.com" in url:
                continue
            # Drop fuzzy matches — username must appear in the URL or title
            if username not in url.lower() and username not in title.lower():
                continue
            seen.add(url)
            findings.append(f"{title} — {url}" if title else url)

        if findings:
            return {"status": "found", "findings": findings, "severity": "low"}
        return {"status": "not_found", "findings": ["No indexed results found"], "severity": "none"}
    except Exception as e:
        return {"status": "not_found", "findings": [f"Error: {e}"], "severity": "none"}


# ── Sherlock ──────────────────────────────────────────────────────────────────

def _find_sherlock() -> str:
    if exe := shutil.which("sherlock"):
        return exe
    candidates = [
        sysconfig.get_path("scripts"),
        sysconfig.get_path("scripts", "nt_user"),
        os.path.dirname(sys.executable),
    ]
    for scripts_dir in filter(None, candidates):
        for name in ("sherlock.exe", "sherlock"):
            path = os.path.join(scripts_dir, name)
            if os.path.isfile(path):
                return path
    return "sherlock"


async def run_sherlock(username: str) -> dict:
    def _blocking():
        result = subprocess.run(
            [_find_sherlock(), username, "--print-found", "--no-color", "--timeout", "15"],
            capture_output=True,
            timeout=120,
        )
        return result.stdout.decode("utf-8", errors="replace")

    try:
        output = await asyncio.to_thread(_blocking)

        findings = []
        for line in output.splitlines():
            if line.startswith("[+]"):
                parts = line[4:].split(": ", 1)
                if len(parts) == 2:
                    url = parts[1].strip()
                    if urlparse(url).path.rstrip("/"):
                        findings.append(url)

        if findings:
            return {"status": "found", "findings": findings, "severity": "medium"}
        return {"status": "not_found", "findings": ["No accounts found on any platform"], "severity": "none"}
    except subprocess.TimeoutExpired:
        return {"status": "not_found", "findings": ["Scan timed out after 120s"], "severity": "none"}
    except Exception as e:
        return {"status": "not_found", "findings": [f"Error: {e}"], "severity": "none"}


# ── WebSocket handler ─────────────────────────────────────────────────────────

AGENTS = [
    ("GitHub",   run_github),
    ("Dorking",  run_dorking),
    ("Sherlock", run_sherlock),
]


@app.websocket("/ws/search")
async def search_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        query = data.get("query", "")
        username = query.strip().lower().replace(" ", "")

        await websocket.send_json({"type": "started", "query": query, "total": len(AGENTS)})

        async def run_agent(name: str, fn):
            await websocket.send_json({"type": "scanning", "agent": name})
            t0 = time.perf_counter()
            result = await fn(username)
            elapsed = round(time.perf_counter() - t0, 1)
            await websocket.send_json({"type": "result", "agent": name, **result, "elapsed": elapsed})

        await asyncio.gather(*[run_agent(name, fn) for name, fn in AGENTS])

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
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)
