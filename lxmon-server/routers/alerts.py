"""
Alerts router for alert rule management and alert monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
import logging

from core.database import get_db
from core.auth import get_current_tenant_id
from models.models import AlertRule, Alert, Server
from core.schemas import (
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AlertResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/rules", response_model=List[AlertRuleResponse])
async def get_alert_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    enabled: Optional[bool] = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Get list of alert rules."""
    query = select(AlertRule).where(AlertRule.tenant_id == tenant_id)

    if enabled is not None:
        query = query.where(AlertRule.enabled == enabled)

    result = await db.execute(
        query.order_by(desc(AlertRule.created_at))
        .offset(skip).limit(limit)
    )
    rules = result.scalars().all()
    return rules

@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Get alert rule by ID."""
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == tenant_id
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )

    return rule

@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new alert rule."""
    new_rule = AlertRule(
        name=rule_data.name,
        description=rule_data.description,
        metric_type=rule_data.metric_type,
        metric_name=rule_data.metric_name,
        condition=rule_data.condition,
        threshold=rule_data.threshold,
        severity=rule_data.severity,
        enabled=True,
        tenant_id=tenant_id
    )

    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)

    logger.info(f"Created alert rule: {new_rule.name}")
    return new_rule

@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    rule_data: AlertRuleUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Update alert rule."""
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == tenant_id
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )

    # Update fields
    update_data = rule_data.dict(exclude_unset=True)
    if update_data:
        for field, value in update_data.items():
            setattr(rule, field, value)

        await db.commit()
        await db.refresh(rule)

    return rule

@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete alert rule."""
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == tenant_id
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )

    await db.delete(rule)
    await db.commit()

    logger.info(f"Deleted alert rule: {rule.name}")
    return {"status": "ok", "message": "Alert rule deleted successfully"}

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Get list of alerts."""
    query = select(Alert).join(Server).where(Server.tenant_id == tenant_id)

    if status_filter:
        query = query.where(Alert.status == status_filter)

    if severity:
        query = query.where(Alert.severity == severity)

    result = await db.execute(
        query.order_by(desc(Alert.triggered_at))
        .offset(skip).limit(limit)
    )
    alerts = result.scalars().all()
    return alerts

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Get alert by ID."""
    result = await db.execute(
        select(Alert).join(Server).where(
            Alert.id == alert_id,
            Server.tenant_id == tenant_id
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    return alert

@router.put("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db)
):
    """Resolve an alert."""
    from datetime import datetime
    from sqlalchemy import update

    result = await db.execute(
        select(Alert).join(Server).where(
            Alert.id == alert_id,
            Server.tenant_id == tenant_id
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    if alert.status == "resolved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert is already resolved"
        )

    # Update alert status
    await db.execute(
        update(Alert).where(Alert.id == alert_id).values(
            status="resolved",
            resolved_at=datetime.utcnow()
        )
    )
    await db.commit()

    logger.info(f"Resolved alert {alert_id}")
    return {"status": "ok", "message": "Alert resolved successfully"}
