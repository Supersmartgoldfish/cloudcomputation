# app/worker.py
import os
from celery import Celery
from .database import DATABASE_URL
from . import database
from sqlalchemy.orm import Session
from . import models, crud
from datetime import datetime

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
celery = Celery(__name__, broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

@celery.task(bind=True)
def dispatch_job(self, job_id: int):
    # This task is responsible for picking a host and instructing it to run the job.
    # Very basic strategy: pick highest-graded available host.
    db = database.SessionLocal()
    try:
        job = db.query(models.Job).get(job_id)
        if not job or job.status != "pending":
            return {"status": "invalid job"}
        host = db.query(models.Host).filter(models.Host.available == True).order_by(models.Host.grade.desc()).first()
        if not host:
            job.status = "pending"
            db.commit()
            return {"status": "no-host"}
        # assign
        job = crud.assign_job_to_host(db, job_id, host.id)
        # In production: send a command to the host agent (via webhooks / command queue) saying "run this docker image/command"
        # For demo we just mark it, and the host agent polling endpoint would read commands from an in-memory dict or route.
        # Simulate work (real work happens on host)
        return {"status": "assigned", "host_id": host.host_id, "job_id": job.id}
    finally:
        db.close()
