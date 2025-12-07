#!/usr/bin/env python3
"""
轻量 CLI：供本地/服务器 Hook 调用。
示例：
  git diff --cached --name-only --diff-filter=ACMR | xargs python cli.py --mode pre-commit --repo myrepo --branch main --files
"""
import argparse
import sys
from pathlib import Path
from typing import List

from scanner import load_allowlist, load_rules, scan_text


def is_binary(path: Path, chunk_size: int = 2048) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(chunk_size)
            return b"\0" in chunk
    except Exception:
        return False


def scan_file(
    path: Path,
    repo: str,
    branch: str,
    rules,
    allowlist,
    max_bytes: int,
    entropy_threshold: float,
    entropy_min_length: int,
):
    if not path.exists() or not path.is_file():
        return {"file": str(path), "error": "not_found", "findings": []}
    if is_binary(path):
        return {"file": str(path), "skipped": "binary", "findings": []}
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"file": str(path), "error": "read_error", "findings": []}
    if len(content.encode("utf-8")) > max_bytes:
        return {"file": str(path), "skipped": "too_large", "findings": []}
    findings = scan_text(
        content,
        rules,
        entropy_threshold,
        entropy_min_length,
        file_path=str(path),
        repo=repo,
        allowlist=allowlist,
    )
    return {"file": str(path), "findings": findings}


def main():
    parser = argparse.ArgumentParser(description="Secret scanner CLI")
    parser.add_argument("--mode", default="manual", help="pre-commit|pre-receive|manual")
    parser.add_argument("--repo", default="", help="repository name")
    parser.add_argument("--branch", default="", help="branch name")
    parser.add_argument("--files", nargs="*", help="files to scan")
    parser.add_argument("--max-bytes", type=int, default=512_000, help="max file size to scan (bytes)")
    parser.add_argument("--entropy-threshold", type=float, default=4.0)
    parser.add_argument("--entropy-min-length", type=int, default=24)
    args = parser.parse_args()

    rules = load_rules()
    allowlist = load_allowlist()
    files: List[str] = args.files or []
    if not files:
        sys.stderr.write("No files provided to scan.\n")
        return 0

    all_findings = []
    for file_path in files:
        result = scan_file(
            Path(file_path),
            repo=args.repo,
            branch=args.branch,
            rules=rules,
            allowlist=allowlist,
            max_bytes=args.max_bytes,
            entropy_threshold=args.entropy_threshold,
            entropy_min_length=args.entropy_min_length,
        )
        if result.get("findings"):
            all_findings.append(result)

    if all_findings:
        for item in all_findings:
            sys.stderr.write(f"[BLOCK] {item['file']}\n")
            for f in item["findings"]:
                sys.stderr.write(f" - {f['rule_id']} ({f['severity']}): {f['masked']}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
