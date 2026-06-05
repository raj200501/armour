"""Scan commit candidates for obvious API key material.

The script reports file and line only. It intentionally does not print matched
secret values.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


SECRET_PATTERNS = (
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")),
    ("gemini_ai_studio_key", re.compile(r"\bAQ\.[0-9A-Za-z_-]{20,}\b")),
    ("openai_api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("anthropic_api_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan tracked and unignored files for common secrets.")
    parser.add_argument("--staged-only", action="store_true", help="Scan only files staged in git.")
    args = parser.parse_args()

    files = _git_files(staged_only=args.staged_only)
    findings: list[str] = []
    for path in files:
        findings.extend(_scan_path(path))
    if findings:
        print("Potential secret material found:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"No obvious secrets found in {len(files)} commit candidate files.")
    return 0


def _git_files(staged_only: bool) -> list[Path]:
    command = ["git", "diff", "--cached", "--name-only"] if staged_only else [
        "git",
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _scan_path(path: Path) -> list[str]:
    if not path.is_file() or path.suffix in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
        return []
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    if b"\0" in raw:
        return []
    text = raw.decode("utf-8", errors="ignore")
    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(f"{path}:{line_number} matched {name}")
    return findings


if __name__ == "__main__":
    sys.exit(main())
