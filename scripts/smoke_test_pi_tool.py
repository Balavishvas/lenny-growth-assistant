"""Smoke-test Pi's custom Lenny retrieval tool against a running local API."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "backend" / "app" / "pi_extensions" / "lenny_rag.ts"
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
PROMPT = (
    "You must call the search_lenny_transcripts tool exactly once with query "
    "'product market fit versus user activation' and top_k 3. "
    "After the tool returns, summarize one concrete point from the retrieved passages."
)


def find_pi_cli() -> str | None:
    """Find Pi even when Windows exposes it as an npm-generated .cmd shim."""
    found = shutil.which("pi") or shutil.which("pi.cmd") or shutil.which("pi.exe")
    if found:
        return found
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            for candidate in (
                Path(appdata) / "npm" / "pi.cmd",
                Path(appdata) / "npm" / "pi.exe",
            ):
                if candidate.is_file():
                    return str(candidate)
    return None


def main() -> int:
    if not EXTENSION.is_file():
        print(f"FAIL: Pi extension not found: {EXTENSION}", file=sys.stderr)
        return 2
    pi_cli = find_pi_cli()
    if not pi_cli:
        print(
            "FAIL: Pi CLI not found. Run Get-Command pi in PowerShell to locate it.",
            file=sys.stderr,
        )
        return 2

    command = [
        pi_cli,
        "--provider", "ollama",
        "--model", MODEL,
        "--extension", str(EXTENSION),
        "--print", PROMPT,
    ]
    print(f"Running Pi retrieval smoke test with model {MODEL}...")
    print(f"Using Pi CLI: {pi_cli}")
    try:
        result = subprocess.run(
            subprocess.list2cmdline(command) if os.name == "nt" else command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=240,
            check=False,
            shell=(os.name == "nt"),
        )
    except subprocess.TimeoutExpired:
        print("FAIL: Pi smoke test timed out after 240 seconds.", file=sys.stderr)
        return 2

    combined = result.stdout + "\n" + result.stderr
    print("\n--- Pi response ---")
    print(result.stdout.strip() or "(no stdout)")
    print("\n--- Tool execution logs ---")
    markers = [line for line in result.stderr.splitlines() if "[lenny-rag]" in line]
    print("\n".join(markers) if markers else "(no [lenny-rag] logs found)")

    invoked = "[lenny-rag] search_lenny_transcripts invoked" in combined
    succeeded = "[lenny-rag] retrieval_succeeded results=" in combined
    if result.returncode == 0 and invoked and succeeded:
        print("\nPASS: Pi invoked the custom tool and the retrieval API returned results.")
        return 0
    print(
        "\nFAIL: Expected both tool-invocation and successful-retrieval markers. "
        "Confirm the API is running at http://127.0.0.1:8000 and inspect the logs above.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
