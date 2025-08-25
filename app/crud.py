# app/crud.py
from sqlalchemy.orm import Session
from . import models
from datetime import datetime
from typing import Dict
import math

def upsert_host(db: Session, host_payload: Dict):
    h = db.query(models.Host).filter(models.Host.host_id == host_payload["host_id"]).first()
    grade = calculate_grade(host_payload["specs"], host_payload["network"])
    pay = round(grade * 0.5, 2)
    if h:
        h.specs = host_payload["specs"]
        h.network = host_payload["network"]
        h.available = host_payload.get("available", True)
        h.installed_apps = host_payload.get("installed_apps", [])
        h.grade = grade
        h.pay_rate = pay
        h.last_seen = datetime.utcnow()
    else:
        h = models.Host(
            host_id=host_payload["host_id"],
            specs=host_payload["specs"],
            network=host_payload["network"],
            available=host_payload.get("available", True),
            installed_apps=host_payload.get("installed_apps", []),
            grade=grade,
            pay_rate=pay
        )
        db.add(h)
    db.commit()
    db.refresh(h)
    return h

def calculate_grade(specs: Dict, network: Dict) -> float:
    cpu = specs.get("cpu_score", 0)
    gpu = specs.get("gpu_score", 0)
    ram = specs.get("ram_gb", 0)
    latency = network.get("latency_ms", 999.0)
    upload = network.get("upload_mbps", 0.0)
    # normalized-ish formula
    score = 0.4 * cpu + 0.3 * gpu + 0.2 * ram + 0.1 * upload - 0.05 * latency
    return max(round(score, 2), 0.0)

def list_available_hosts(db: Session, limit: int = 50):
    return db.query(models.Host).filter(models.Host.available == True).order_by(models.Host.grade.desc()).limit(limit).all()

def set_host_command(db: Session, host_id: str, command: Dict):
    # For simplicity just store in memory or another table; we'll create an ad-hoc approach:
    # We'll use a simple table-less dict stored in memory in main app for speed (see main.py)
    # This function could be extended to persist commands in DB.
    raise NotImplementedError

def create_job(db: Session, user_id: int, app: str, payload: Dict):
    job = models.Job(user_id=user_id, app=app, payload=payload, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def assign_job_to_host(db: Session, job_id: int, host_id: int):
    job = db.query(models.Job).get(job_id)
    host = db.query(models.Host).get(host_id)
    if not job or not host:
        return None
    job.host_id = host.id
    job.status = "running"
    job.started_at = datetime.utcnow()
    host.available = False
    db.commit()
    db.refresh(job)
    return job
