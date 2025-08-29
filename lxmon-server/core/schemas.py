"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# Authentication schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=100)
    password: str = Field(..., min_length=6)
    tenant_id: Optional[str] = "default"

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Server schemas
class ServerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    hostname: str = Field(..., min_length=1, max_length=255)
    ip_address: Optional[str] = None

class ServerCreate(ServerBase):
    agent_api_key: str

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    status: Optional[str] = None

class ServerResponse(ServerBase):
    id: int
    agent_api_key: str
    tenant_id: str
    status: str
    last_heartbeat: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Agent schemas
class AgentRegister(BaseModel):
    hostname: str
    ip_address: Optional[str] = None
    api_key: str

class AgentHeartbeat(BaseModel):
    hostname: str
    status: str = "online"

class MetricData(BaseModel):
    metric_type: str  # cpu, memory, disk, network
    metric_name: str
    value: float
    unit: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MetricsPayload(BaseModel):
    hostname: str
    metrics: List[MetricData]
    api_key: str

# Command schemas
class CommandCreate(BaseModel):
    command: str = Field(..., min_length=1)

class CommandResponse(BaseModel):
    id: int
    server_id: int
    command: str
    status: str
    exit_code: Optional[int]
    stdout: Optional[str]
    stderr: Optional[str]
    executed_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class CommandResult(BaseModel):
    command_id: int
    exit_code: int
    stdout: str
    stderr: str

# Alert schemas
class AlertRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    metric_type: str
    metric_name: str
    condition: str  # gt, lt, eq, ne
    threshold: float
    severity: str = "warning"  # info, warning, error, critical

class AlertRuleCreate(AlertRuleBase):
    pass

class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    threshold: Optional[float] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None

class AlertRuleResponse(AlertRuleBase):
    id: int
    enabled: bool
    tenant_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class AlertResponse(BaseModel):
    id: int
    alert_rule_id: int
    server_id: int
    message: str
    severity: str
    status: str
    triggered_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True
