"""
Servers router for dashboard API endpoints.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
import logging

from core.database import get_db
from core.auth import get_current_user, get_current_tenant_id
from database.redis_client import redis_client
from models.models import Server, Metric, Command, User
from core.schemas import (
    ServerCreate, ServerUpdate, ServerResponse,
    CommandCreate, CommandResponse, MetricData
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[ServerResponse])
async def get_servers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Get list of servers."""
    result = await db.execute(
        select(Server).where(Server.tenant_id == tenant_id)
        .offset(skip).limit(limit)
    )
    servers = result.scalars().all()
    return servers

@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Get server by ID."""
    result = await db.execute(
        select(Server).where(
            Server.id == server_id,
            Server.tenant_id == tenant_id
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    return server

@router.post("/", response_model=ServerResponse)
async def create_server(
    server_data: ServerCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new server."""
    # Check if hostname already exists
    result = await db.execute(
        select(Server).where(Server.hostname == server_data.hostname)
    )
    existing_server = result.scalar_one_or_none()

    if existing_server:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server with this hostname already exists"
        )

    new_server = Server(
        name=server_data.name,
        hostname=server_data.hostname,
        ip_address=server_data.ip_address,
        agent_api_key=server_data.agent_api_key,
        tenant_id=tenant_id,
        status="offline"
    )

    db.add(new_server)
    await db.commit()
    await db.refresh(new_server)

    logger.info(f"Created new server: {new_server.hostname}")
    return new_server

@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: int,
    server_data: ServerUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Update server information."""
    result = await db.execute(
        select(Server).where(
            Server.id == server_id,
            Server.tenant_id == tenant_id
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    # Update fields
    update_data = server_data.dict(exclude_unset=True)
    if update_data:
        await db.execute(
            update(Server).where(Server.id == server_id).values(**update_data)
        )
        await db.commit()
        await db.refresh(server)

    return server

@router.delete("/{server_id}")
async def delete_server(
    server_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a server."""
    result = await db.execute(
        select(Server).where(
            Server.id == server_id,
            Server.tenant_id == tenant_id
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    await db.delete(server)
    await db.commit()

    logger.info(f"Deleted server: {server.hostname}")
    return {"status": "ok", "message": "Server deleted successfully"}

@router.get("/{server_id}/metrics")
async def get_server_metrics(
    server_id: int,
    metric_type: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Get metrics for a server."""
    # Verify server exists and belongs to tenant
    result = await db.execute(
        select(Server).where(
            Server.id == server_id,
            Server.tenant_id == tenant_id
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    # Calculate time range
    since = datetime.utcnow() - timedelta(hours=hours)

    # Build query
    query = select(Metric).where(
        Metric.server_id == server_id,
        Metric.collected_at >= since
    )

    if metric_type:
        query = query.where(Metric.metric_type == metric_type)

    query = query.order_by(desc(Metric.collected_at))

    result = await db.execute(query)
    metrics = result.scalars().all()

    return {
        "server_id": server_id,
        "server_name": server.name,
        "metrics": [MetricData.from_orm(metric) for metric in metrics],
        "count": len(metrics)
    }

@router.post("/{server_id}/command", response_model=CommandResponse)
async def send_command(
    server_id: int,
    command_data: CommandCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Send command to server."""
    # Verify server exists and belongs to tenant
    result = await db.execute(
        select(Server).where(
            Server.id == server_id,
            Server.tenant_id == tenant_id
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    # Create command record
    command = Command(
        server_id=server_id,
        command=command_data.command,
        status="pending"
    )

    db.add(command)
    await db.commit()
    await db.refresh(command)

    # Add to Redis queue
    await redis_client.push_command(server_id, {
        "command_id": command.id,
        "command": command_data.command
    })

    logger.info(f"Command queued for server {server.hostname}: {command_data.command}")
    return command

@router.get("/{server_id}/commands", response_model=List[CommandResponse])
async def get_server_commands(
    server_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Get command history for a server."""
    # Verify server exists and belongs to tenant
    result = await db.execute(
        select(Server).where(
            Server.id == server_id,
            Server.tenant_id == tenant_id
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    # Get commands
    result = await db.execute(
        select(Command).where(Command.server_id == server_id)
        .order_by(desc(Command.created_at))
        .offset(skip).limit(limit)
    )
    commands = result.scalars().all()

    return commands

@router.get("/commands/{command_id}/status", response_model=CommandResponse)
async def get_command_status(
    command_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Get command execution status."""
    result = await db.execute(
        select(Command).join(Server).where(
            Command.id == command_id,
            Server.tenant_id == tenant_id
        )
    )
    command = result.scalar_one_or_none()

    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found"
        )

    return command
