"""
Database models for lxmon-server using SQLAlchemy.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Server(Base):
    """Server model representing monitored servers."""
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    hostname = Column(String(255), nullable=False, unique=True)
    ip_address = Column(String(45))
    agent_api_key = Column(String(255), nullable=False)
    tenant_id = Column(String(50), default="default", index=True)
    status = Column(String(20), default="offline")  # online, offline, unknown
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    metrics = relationship("Metric", back_populates="server", cascade="all, delete-orphan")
    commands = relationship("Command", back_populates="server", cascade="all, delete-orphan")

class Metric(Base):
    """Metrics collected from servers."""
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    metric_type = Column(String(50), nullable=False)  # cpu, memory, disk, network
    metric_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    metric_metadata = Column(JSON)  # Additional metric data
    collected_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    server = relationship("Server", back_populates="metrics")

class Command(Base):
    """Commands sent to servers."""
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    command = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed, timeout
    exit_code = Column(Integer, nullable=True)
    stdout = Column(Text)
    stderr = Column(Text)
    executed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    server = relationship("Server", back_populates="commands")

class AlertRule(Base):
    """Alert rules for monitoring."""
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    metric_type = Column(String(50), nullable=False)
    metric_name = Column(String(100), nullable=False)
    condition = Column(String(20), nullable=False)  # gt, lt, eq, ne
    threshold = Column(Float, nullable=False)
    severity = Column(String(20), default="warning")  # info, warning, error, critical
    enabled = Column(Boolean, default=True)
    tenant_id = Column(String(50), default="default", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    """Triggered alerts."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), default="active")  # active, resolved, acknowledged
    triggered_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class User(Base):
    """Dashboard users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String(50), default="default", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
