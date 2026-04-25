import asyncio
import os
import shutil
import subprocess
import sys
import sysconfig
import time
from urllib.parse import urlparse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="OSINT Aggregator")


def _find_sherlock() -> str:
    if exe := shutil.which("sherlock"):
        return exe
    # Check all plausible Scripts directories (covers Windows Store Python / venvs)
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
                # "[+] SiteName: https://..."
                parts = line[4:].split(": ", 1)
                if len(parts) == 2:
                    url = parts[1].strip()
                    # Skip bare domains — no profile path means the link is useless
                    if urlparse(url).path.rstrip("/"):
                        findings.append(url)

        if findings:
            return {"status": "found", "findings": findings, "severity": "medium"}
        return {"status": "not_found", "findings": ["No accounts found on any platform"], "severity": "none"}
    except subprocess.TimeoutExpired:
        return {"status": "not_found", "findings": ["Scan timed out after 120s"], "severity": "none"}
    except Exception as e:
        return {"status": "not_found", "findings": [f"Error: {e}"], "severity": "none"}


@app.websocket("/ws/search")
async def search_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        query = data.get("query", "")
        username = query.strip().lower().replace(" ", "")

        await websocket.send_json({"type": "started", "query": query, "total": 1})

        await websocket.send_json({"type": "scanning", "agent": "Sherlock"})
        t0 = time.perf_counter()
        result = await run_sherlock(username)
        elapsed = round(time.perf_counter() - t0, 1)
        await websocket.send_json({
            "type": "result",
            "agent": "Sherlock",
            **result,
            "elapsed": elapsed,
        })

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
