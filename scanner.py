import base64
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Pattern

try:
    import yaml
except ImportError:  # pragma: no cover - fallback when PyYAML is missing
    yaml = None


SEVERITY_MAP = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


def normalize_severity(value: str) -> str:
    return SEVERITY_MAP.get(value.lower(), value) if isinstance(value, str) else "Medium"


@dataclass
class RuleDef:
    id: str
    pattern: str
    severity: str = "Medium"
    description: str = ""
    enabled: bool = True
    validators: List[str] = field(default_factory=list)
    flags: int = re.MULTILINE


@dataclass
class AllowList:
    patterns: List[Pattern]
    paths: List[Pattern]
    repos: List[str]


DEFAULT_RULES: List[RuleDef] = [
    RuleDef(
        id="AWS_ACCESS_KEY",
        pattern=r"AKIA[0-9A-Z]{16}",
        severity="High",
        description="AWS Access Key ID",
        validators=["length>=20"],
    ),
    RuleDef(
        id="GITHUB_TOKEN",
        pattern=r"ghp_[0-9A-Za-z]{36}",
        severity="High",
        description="GitHub personal access token",
        validators=["length>=39"],
    ),
    RuleDef(
        id="RSA_PRIVATE_KEY",
        pattern=r"-----BEGIN RSA PRIVATE KEY-----",
        severity="High",
        description="RSA private key header",
        validators=["pem"],
    ),
    RuleDef(
        id="JWT",
        pattern=r"[A-Za-z0-9_-]+?\.[A-Za-z0-9_-]+?\.[A-Za-z0-9_-]{10,}",
        severity="Medium",
        description="Likely JWT token",
        validators=["jwt"],
    ),
]


def load_rules(path: str = "rules.yml") -> List[RuleDef]:
    file_path = Path(path)
    if file_path.exists() and yaml:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or []
        rules: List[RuleDef] = []
        for item in data:
            rules.append(
                RuleDef(
                    id=item.get("id"),
                    pattern=item.get("pattern"),
                    severity=normalize_severity(item.get("severity", "Medium")),
                    description=item.get("description", ""),
                    enabled=item.get("enabled", True),
                    validators=item.get("validators", []) or [],
                )
            )
        return rules
    return DEFAULT_RULES


def load_allowlist(path: str = "allowlist.yml") -> AllowList:
    file_path = Path(path)
    if not file_path.exists() or not yaml:
        return AllowList(patterns=[], paths=[], repos=[])
    data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
    patterns = [re.compile(p) for p in data.get("patterns", [])]
    paths = [re.compile(p) for p in data.get("paths", [])]
    repos = data.get("repos", [])
    return AllowList(patterns=patterns, paths=paths, repos=repos)


def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    freq = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    entropy = 0.0
    length = len(text)
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def mask_secret(secret: str, keep: int = 4) -> str:
    if len(secret) <= keep * 2:
        return secret
    return f"{secret[:keep]}...{secret[-keep:]}"


def compile_rules(rules: Iterable[RuleDef]):
    compiled = []
    for rule in rules:
        if not rule.enabled:
            continue
        compiled.append((rule, re.compile(rule.pattern, rule.flags)))
    return compiled


def _is_base64url(text: str) -> bool:
    try:
        padding = "=" * (-len(text) % 4)
        base64.urlsafe_b64decode(text + padding)
        return True
    except Exception:
        return False


def _luhn_ok(text: str) -> bool:
    digits = [int(c) for c in text if c.isdigit()]
    if len(digits) < 2:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def _is_jwt(token: str) -> bool:
    parts = token.split(".")
    if len(parts) != 3:
        return False
    header, payload, signature = parts
    if not (header and payload and signature):
        return False
    return _is_base64url(header) and _is_base64url(payload)


def _is_pem(snippet: str) -> bool:
    return snippet.startswith("-----BEGIN") or "BEGIN " in snippet


def _passes_validators(snippet: str, validators: List[str]) -> bool:
    for validator in validators:
        rule = validator.lower()
        if rule == "jwt" and not _is_jwt(snippet):
            return False
        if rule == "base64" and not _is_base64url(snippet):
            return False
        if rule == "pem" and not _is_pem(snippet):
            return False
        if rule == "luhn" and not _luhn_ok(snippet):
            return False
        if rule.startswith("length>="):
            try:
                min_len = int(rule.split(">=")[1])
                if len(snippet) < min_len:
                    return False
            except ValueError:
                continue
    return True


def _is_allowed(snippet: str, file_path: Optional[str], repo: Optional[str], allowlist: AllowList) -> bool:
    if repo and repo in allowlist.repos:
        return True
    if file_path:
        for path_rule in allowlist.paths:
            if path_rule.search(file_path):
                return True
    for pattern in allowlist.patterns:
        if pattern.search(snippet):
            return True
    return False


def scan_text(
    content: str,
    rules: Optional[Iterable[RuleDef]] = None,
    entropy_threshold: float = 4.0,
    entropy_min_length: int = 24,
    file_path: Optional[str] = None,
    repo: Optional[str] = None,
    allowlist: Optional[AllowList] = None,
):
    rules_to_use = rules or DEFAULT_RULES
    compiled = compile_rules(rules_to_use)
    findings = []
    allow = allowlist or AllowList(patterns=[], paths=[], repos=[])

    for rule, pattern in compiled:
        for match in pattern.finditer(content):
            snippet = match.group(0)
            if _is_allowed(snippet, file_path, repo, allow):
                continue
            if not _passes_validators(snippet, rule.validators):
                continue
            findings.append(
                {
                    "rule_id": rule.id,
                    "severity": normalize_severity(rule.severity),
                    "description": rule.description,
                    "match": snippet,
                    "masked": mask_secret(snippet),
                }
            )

    for candidate in re.findall(r"[A-Za-z0-9+/=_-]{24,}", content):
        if len(candidate) < entropy_min_length:
            continue
        if _is_allowed(candidate, file_path, repo, allow):
            continue
        if shannon_entropy(candidate) >= entropy_threshold:
            findings.append(
                {
                    "rule_id": "HIGH_ENTROPY",
                    "severity": "Medium",
                    "description": "High-entropy token",
                    "match": candidate,
                    "masked": mask_secret(candidate),
                }
            )
    return findings
