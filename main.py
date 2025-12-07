import hashlib
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from scanner import AllowList, RuleDef, load_allowlist, load_rules, mask_secret, scan_text

API_TOKEN = os.getenv("API_TOKEN") or None
ENTROPY_THRESHOLD = float(os.getenv("ENTROPY_THRESHOLD", "4.0"))
ENTROPY_MIN_LENGTH = int(os.getenv("ENTROPY_MIN_LENGTH", "24"))

app = FastAPI()

origins = os.getenv("CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rules_cache: List[RuleDef] = load_rules()
allowlist_cache: AllowList = load_allowlist()


def sync_rules_to_db(db: Session) -> None:
    for rule in rules_cache:
        existing = db.query(models.Rule).filter(models.Rule.id == rule.id).first()
        if existing:
            existing.pattern = rule.pattern
            existing.severity = rule.severity
            existing.description = rule.description
            existing.enabled = rule.enabled
        else:
            db.add(
                models.Rule(
                    id=rule.id,
                    pattern=rule.pattern,
                    severity=rule.severity,
                    description=rule.description,
                    enabled=rule.enabled,
                )
            )
    db.commit()


with models.SessionLocal() as init_db:
    sync_rules_to_db(init_db)


def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_auth(x_api_key: Optional[str] = Header(default=None)):
    if API_TOKEN and x_api_key != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )


class ScanRequest(BaseModel):
    content: str
    repo: Optional[str] = None
    branch: Optional[str] = None
    file_path: Optional[str] = None
    mode: Optional[str] = None
    commit: Optional[str] = None
    author: Optional[str] = None
    line: Optional[int] = None


class UpdateFindingStatus(BaseModel):
    status: Literal["New", "Resolved", "Ignored"]


class UpdateRuleBody(BaseModel):
    enabled: bool


def scan_for_secrets(text: str) -> List[str]:
    return [
        item["match"]
        for item in scan_text(
            text, rules_cache, ENTROPY_THRESHOLD, ENTROPY_MIN_LENGTH, allowlist=allowlist_cache
        )
    ]


@app.get("/ping", response_class=PlainTextResponse)
async def ping() -> str:
    return "pong"


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "rules": len(rules_cache),
        "allowlist_patterns": len(allowlist_cache.patterns),
    }


@app.get("/api/rules")
async def get_rules(_: None = Depends(require_auth)):
    return [
        {
            "id": rule.id,
            "severity": rule.severity,
            "description": rule.description,
            "pattern": rule.pattern,
            "enabled": rule.enabled,
        }
        for rule in rules_cache
    ]


@app.patch("/api/rules/{rule_id}")
async def update_rule(
    rule_id: str, payload: UpdateRuleBody, _: None = Depends(require_auth), db: Session = Depends(get_db)
):
    target = None
    for rule in rules_cache:
        if rule.id == rule_id:
            rule.enabled = payload.enabled
            target = rule
            break
    if not target:
        raise HTTPException(status_code=404, detail="Rule not found")

    rules_file = Path("rules.yml")
    if rules_file.exists():
        try:
            import yaml

            content = yaml.safe_load(rules_file.read_text(encoding="utf-8")) or []
            for item in content:
                if item.get("id") == rule_id:
                    item["enabled"] = payload.enabled
            rules_file.write_text(yaml.safe_dump(content, allow_unicode=True), encoding="utf-8")
        except Exception:
            # 如果写文件失败，至少保证内存中已更新，不影响请求
            pass
    sync_rules_to_db(db)
    return {"id": rule_id, "enabled": payload.enabled}


@app.post("/api/rules/reload")
async def reload_rules(_: None = Depends(require_auth), db: Session = Depends(get_db)):
    global rules_cache
    rules_cache = load_rules()
    sync_rules_to_db(db)
    return {"message": "规则已重新加载", "count": len(rules_cache)}


@app.post("/api/allowlist/reload")
async def reload_allowlist(_: None = Depends(require_auth)):
    global allowlist_cache
    allowlist_cache = load_allowlist()
    return {"message": "白名单已重新加载"}


@app.post("/scan")
@app.post("/api/scan")
async def scan(
    request: ScanRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_auth),
):
    start = time.perf_counter()
    findings = scan_text(
        request.content,
        rules_cache,
        ENTROPY_THRESHOLD,
        ENTROPY_MIN_LENGTH,
        file_path=request.file_path,
        repo=request.repo,
        allowlist=allowlist_cache,
    )
    duration_ms = int((time.perf_counter() - start) * 1000)

    scan_record = models.ScanRecord(
        mode=request.mode,
        repo=request.repo,
        branch=request.branch,
        file_path=request.file_path,
        findings_count=len(findings),
        duration_ms=duration_ms,
    )
    db.add(scan_record)

    if findings:
        for finding in findings:
            snippet_hash = hashlib.sha256(finding["match"].encode("utf-8")).hexdigest()[
                :16
            ]
            incident = models.SecretIncident(
                file_path=request.file_path or "",
                secret_content=f"{finding['rule_id']}#{snippet_hash}",
                created_at=datetime.now(),
            )
            db.add(incident)

            finding_record = models.Finding(
                repo=request.repo or "unknown",
                branch=request.branch or "unknown",
                file_path=request.file_path or "",
                line=request.line or 0,
                masked_snippet=finding["masked"] or mask_secret(finding["match"]),
                commit=request.commit or "",
                author=request.author or "unknown",
                status="New",
                rule_id=finding["rule_id"],
                rule_severity=finding["severity"],
                rule_description=finding["description"],
                created_at=datetime.now(),
            )
            db.add(finding_record)
            if finding["severity"] in ("High", "Critical"):
                db.add(
                    models.Alert(
                        finding_id=None,
                        channel="local-log",
                        status="Pending",
                    )
                )

    db.commit()

    if findings:
        return {
            "message": "检测到密钥泄露",
            "found": findings,
            "duration_ms": duration_ms,
        }

    return {"message": "未发现敏感信息", "duration_ms": duration_ms}


@app.get("/api/findings")
async def list_findings(
    limit: int = 50,
    offset: int = 0,
    repo: Optional[str] = None,
    branch: Optional[str] = None,
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_auth),
):
    query = db.query(models.Finding)
    if repo:
        query = query.filter(models.Finding.repo == repo)
    if branch:
        query = query.filter(models.Finding.branch == branch)
    if status_filter:
        query = query.filter(models.Finding.status == status_filter)
    if severity:
        query = query.filter(models.Finding.rule_severity == severity)

    incidents = (
        query.order_by(models.Finding.created_at.desc()).offset(offset).limit(limit).all()
    )
    return [
        {
            "id": item.id,
            "repo": item.repo or "",
            "branch": item.branch or "",
            "file_path": item.file_path or "",
            "line": item.line or 0,
            "masked_snippet": item.masked_snippet or "",
            "commit": item.commit or "",
            "author": item.author or "",
            "created_at": item.created_at,
            "status": item.status or "New",
            "rule": {
                "id": item.rule_id or "",
                "severity": item.rule_severity or "Medium",
                "description": item.rule_description or "",
            },
        }
        for item in incidents
    ]


@app.patch("/api/findings/{finding_id}")
async def update_finding_status(
    finding_id: int, payload: UpdateFindingStatus, db: Session = Depends(get_db), _: None = Depends(require_auth)
):
    finding = (
        db.query(models.Finding).filter(models.Finding.id == finding_id).first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    finding.status = payload.status
    db.commit()
    db.refresh(finding)
    return {
        "id": finding.id,
        "status": finding.status,
    }


@app.get("/api/stats")
async def stats(db: Session = Depends(get_db), _: None = Depends(require_auth)):
    total = db.query(models.Finding).count()
    recent = (
        db.query(models.Finding)
        .filter(models.Finding.created_at >= datetime.utcnow() - timedelta(days=1))
        .count()
    )
    scans = db.query(models.ScanRecord).count()
    return {"total_findings": total, "findings_24h": recent, "scans": scans}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
