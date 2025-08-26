# app.main
from fastapi import FastAPI, Depends, HTTPException, status
from . import models, database, auth, crud
from .schemas import *
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from .worker import dispatch_job
import os

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="CloudRig Backend - Fresh Start")

# Simple in-memory command store (replace with persistent queue if you like)
COMMAND_STORE = {}  # host_id -> {"command": str, "app": str, "job_id": int}

@app.post("/auth/register", response_model=Token)
def register(u: UserCreate, db: Session = Depends(auth.get_db)):
    existing = db.query(models.User).filter(models.User.email == u.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")
    hashed = auth.get_password_hash(u.password)
    user = models.User(email=u.email, hashed_password=hashed)
    db.add(user); db.commit(); db.refresh(user)
    token = auth.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect credentials")
    token = auth.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/hosts/register")
def register_host(h: HostRegister, db: Session = Depends(auth.get_db)):
    # Upsert and grade
    res = crud.upsert_host(db, h.dict())
    return {"status":"ok", "grade": res.grade, "pay_rate": res.pay_rate}

@app.get("/hosts/available", response_model=list[HostOut])
def available_hosts(limit: int = 50, db: Session = Depends(auth.get_db)):
    hosts = crud.list_available_hosts(db, limit=limit)
    out = []
    for h in hosts:
        out.append({
            "host_id": h.host_id,
            "grade": h.grade,
            "pay_rate": h.pay_rate,
            "available": h.available,
            "specs": h.specs or {},
            "network": h.network or {},
            "installed_apps": h.installed_apps or []
        })
    return out

@app.post("/hosts/command/{host_id}")
def send_command(host_id: str, cmd: CommandPayload, db: Session = Depends(auth.get_db)):
    # Put it in memory store; host agent polls /hosts/command/{host_id}
    COMMAND_STORE[host_id] = {"command": cmd.command, "app": cmd.app}
    return {"status":"ok"}

@app.get("/hosts/command/{host_id}")
def get_command(host_id: str):
    return COMMAND_STORE.get(host_id, {"command": None})

@app.post("/jobs/submit")
def submit_job(j: JobCreate, current_user = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    job = crud.create_job(db, user_id=current_user.id, app=j.app, payload=j.payload)
    # dispatch asynchronously
    dispatch_job.delay(job.id)
    return {"status":"queued", "job_id": job.id}

@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(auth.get_db)):
    job = db.query(models.Job).get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {
        "id": job.id, "status": job.status, "host_id": job.host_id,
        "started_at": job.started_at, "finished_at": job.finished_at
    }

@app.post("/sessions/end/{job_id}")
def end_session(job_id: int, db: Session = Depends(auth.get_db)):
    job = db.query(models.Job).get(job_id)
    if not job or job.status != "running":
        raise HTTPException(400, "invalid job")
    job.status = "done"
    job.finished_at = datetime.utcnow()
    # compute duration and payout
    # simplistic: duration = 1h per job for demo; payout = host.pay_rate * duration
    host = db.query(models.Host).get(job.host_id)
    duration_hours = max( ( (job.finished_at - job.started_at).total_seconds() / 3600.0 ) , 0.001 )
    payout = round(duration_hours * (host.pay_rate if host else 0), 2)
    job.earned = payout
    # free up host
    if host:
        host.available = True
    db.commit()
    return {"status":"ended", "earned": payout}

@app.get("/hosts/{host_id}/next-job")
def assign_job(host_id: str, db: Session = Depends(auth.get_db)):
    job = db.query(models.Job).filter(models.Job.status == "queued").first()
    if not job:
        return {"job": None}
    job.status = "running"
    job.host_id = host_id
    job.started_at = datetime.utcnow()
    db.commit()
    return {
        "id": job.id,
        "docker_image": job.docker_image,
        "command": job.command,
        "payload": job.payload
    }

@app.post("/hosts/{host_id}/jobs/{job_id}/done")
def job_done(host_id: str, job_id: int, result: dict, db: Session = Depends(auth.get_db)):
    job = db.query(models.Job).get(job_id)
    if not job or job.host_id != host_id:
        raise HTTPException(404, "job not found for this host")
    job.status = "done"
    job.finished_at = datetime.utcnow()
    job.result = result
    db.commit()
    return {"status": "ok"}
