# app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class HostRegister(BaseModel):
    host_id: str
    specs: Dict[str, Any]
    network: Dict[str, Any]
    available: bool
    installed_apps: List[str] = []

class HostOut(BaseModel):
    host_id: str
    grade: float
    pay_rate: float
    available: bool
    specs: Dict[str, Any]
    network: Dict[str, Any]
    installed_apps: List[str]

class CommandPayload(BaseModel):
    command: str
    app: Optional[str] = None

class JobCreate(BaseModel):
    app: str
    payload: Dict[str, Any] = {}
    # optional constraints (min_gpu_score etc.)
    min_cpu_score: Optional[int] = None
    min_gpu_score: Optional[int] = None
