"""
Agent router for handling agent registration, metrics, and commands.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
import logging

from core.database import get_db
from core.auth import verify_api_key, get_agent_tenant_id
from database.redis_client import redis_client
from models.models import Server, Metric, Command
from core.schemas import (
    AgentRegister, AgentHeartbeat, MetricsPayload,
    CommandResponse, CommandResult
)

logger = logging.getLogger(__name__)

router = APIRouter()

async def get_server_by_hostname_and_key(
    db: AsyncSession, hostname: str, api_key: str
) -> Optional[Server]:
    """Get server by hostname and API key."""
    if not verify_api_key(api_key):
        return None

    result = await db.execute(
        select(Server).where(
            Server.hostname == hostname,
            Server.agent_api_key == api_key
        )
    )
    return result.scalar_one_or_none()

@router.post("/register")
async def register_agent(
    agent_data: AgentRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register or update agent information."""
    if not verify_api_key(agent_data.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Check if server already exists
    server = await get_server_by_hostname_and_key(
        db, agent_data.hostname, agent_data.api_key
    )

    if server:
        # Update existing server
        await db.execute(
            update(Server).where(Server.id == server.id).values(
                ip_address=agent_data.ip_address,
                status="online",
                last_heartbeat=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
        await db.commit()
        logger.info(f"Updated existing server: {agent_data.hostname}")
    else:
        # Create new server
        tenant_id = get_agent_tenant_id(agent_data.api_key)
        new_server = Server(
            name=agent_data.hostname,
            hostname=agent_data.hostname,
            ip_address=agent_data.ip_address,
            agent_api_key=agent_data.api_key,
            tenant_id=tenant_id,
            status="online",
            last_heartbeat=datetime.utcnow()
        )
        db.add(new_server)
        await db.commit()
        await db.refresh(new_server)
        logger.info(f"Registered new server: {agent_data.hostname}")

    return {"status": "registered", "message": "Agent registered successfully"}

@router.post("/heartbeat")
async def agent_heartbeat(
    heartbeat_data: AgentHeartbeat,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
):
    """Receive heartbeat from agent."""
    server = await get_server_by_hostname_and_key(
        db, heartbeat_data.hostname, x_api_key
    )

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found or invalid API key"
        )

    # Update server status and heartbeat
    await db.execute(
        update(Server).where(Server.id == server.id).values(
            status=heartbeat_data.status,
            last_heartbeat=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()

    return {"status": "ok", "timestamp": datetime.utcnow()}

@router.post("/metrics")
async def submit_metrics(
    metrics_data: MetricsPayload,
    db: AsyncSession = Depends(get_db)
):
    """Receive metrics from agent."""
    server = await get_server_by_hostname_and_key(
        db, metrics_data.hostname, metrics_data.api_key
    )

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found or invalid API key"
        )

    # Insert metrics
    for metric_data in metrics_data.metrics:
        metric = Metric(
            server_id=server.id,
            metric_type=metric_data.metric_type,
            metric_name=metric_data.metric_name,
            value=metric_data.value,
            unit=metric_data.unit,
            metadata=metric_data.metadata,
            collected_at=datetime.utcnow()
        )
        db.add(metric)

    await db.commit()
    logger.info(f"Received {len(metrics_data.metrics)} metrics from {metrics_data.hostname}")

    return {"status": "ok", "metrics_received": len(metrics_data.metrics)}

@router.get("/commands", response_model=List[CommandResponse])
async def get_pending_commands(
    hostname: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
):
    """Get pending commands for agent."""
    server = await get_server_by_hostname_and_key(db, hostname, x_api_key)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found or invalid API key"
        )

    # Get pending commands from Redis queue
    commands = []
    command_count = await redis_client.get_command_count(server.id)

    for _ in range(command_count):
        command_data = await redis_client.pop_command(server.id)
        if command_data:
            # Create command record in database
            command = Command(
                server_id=server.id,
                command=command_data["command"],
                status="running",
                executed_at=datetime.utcnow()
            )
            db.add(command)
            await db.commit()
            await db.refresh(command)
            commands.append(command)

    return commands

@router.post("/command-result")
async def submit_command_result(
    result_data: CommandResult,
    hostname: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
):
    """Receive command execution result from agent."""
    server = await get_server_by_hostname_and_key(db, hostname, x_api_key)

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found or invalid API key"
        )

    # Update command with result
    result = await db.execute(
        select(Command).where(
            Command.id == result_data.command_id,
            Command.server_id == server.id
        )
    )
    command = result.scalar_one_or_none()

    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found"
        )

    # Update command status
    await db.execute(
        update(Command).where(Command.id == command.id).values(
            status="completed" if result_data.exit_code == 0 else "failed",
            exit_code=result_data.exit_code,
            stdout=result_data.stdout,
            stderr=result_data.stderr,
            completed_at=datetime.utcnow()
        )
    )
    await db.commit()

    logger.info(f"Command {command.id} completed with exit code {result_data.exit_code}")

    return {"status": "ok", "command_id": command.id}
