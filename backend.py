from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
from datetime import datetime

app = FastAPI()
hosts: Dict[str, dict] = {}
commands: Dict[str, dict] = {}
sessions: Dict[str, dict] = {}

class HostData(BaseModel):
    host_id: str
    specs: dict
    network: dict
    available: bool
    installed_apps: list  # list of installed games/software

class CommandData(BaseModel):
    command: str  # start/stop
    app: str = None  # optional app/game to launch

class SessionData(BaseModel):
    host_id: str
    user_id: str
    app: str = None
    start_time: datetime = None
    end_time: datetime = None

def calculate_grade(specs, network):
    cpu_score = specs.get("cpu_score", 0)
    gpu_score = specs.get("gpu_score", 0)
    ram_score = specs.get("ram_gb", 0)
    latency = network.get("latency_ms", 1000)
    upload = network.get("upload_mbps", 1)
    grade = 0.4*cpu_score + 0.3*gpu_score + 0.2*ram_score + 0.1*upload - 0.05*latency
    return max(grade, 0)

@app.post("/hosts/register")
def register_host(host: HostData):
    grade = calculate_grade(host.specs, host.network)
    pay_rate = round(grade * 0.5, 2)
    hosts[host.host_id] = {
        "specs": host.specs,
        "network": host.network,
        "available": host.available,
        "grade": grade,
        "pay_rate": pay_rate,
        "installed_apps": host.installed_apps
    }
    return {"status": "ok", "grade": grade, "pay_rate": pay_rate}

@app.get("/hosts/available")
def get_available_hosts():
    available_hosts = [{"host_id": hid, **info} for hid, info in hosts.items() if info["available"]]
    return sorted(available_hosts, key=lambda h: h["grade"], reverse=True)

@app.post("/hosts/command/{host_id}")
def send_command(host_id: str, cmd: CommandData):
    if host_id in hosts:
        commands[host_id] = {"command": cmd.command, "app": cmd.app}
        return {"status": "ok"}
    return {"status": "host not found"}

@app.get("/hosts/command/{host_id}")
def get_command(host_id: str):
    return commands.get(host_id, {"command": None})

@app.post("/sessions/start")
def start_session(session: SessionData):
    session_id = f"{session.user_id}-{session.host_id}-{datetime.utcnow().timestamp()}"
    session.start_time = datetime.utcnow()
    sessions[session_id] = {"host_id": session.host_id, "user_id": session.user_id,
                            "app": session.app, "start_time": session.start_time,
                            "end_time": None, "earned": 0}
    hosts[session.host_id]["available"] = False
    return {"session_id": session_id}

@app.post("/sessions/end/{session_id}")
def end_session(session_id: str):
    if session_id not in sessions:
        return {"status": "not found"}
    session = sessions[session_id]
    session["end_time"] = datetime.utcnow()
    duration_hours = (session["end_time"] - session["start_time"]).total_seconds() / 3600
    host_info = hosts[session["host_id"]]
    earned = round(duration_hours * host_info["pay_rate"], 2)
    session["earned"] = earned
    hosts[session["host_id"]]["available"] = True
    return {"status": "ok", "earned": earned, "duration_hours": round(duration_hours, 2)}

@app.get("/hosts/info/{host_id}")
def host_info(host_id: str):
    return hosts.get(host_id, {"status": "not found"})


