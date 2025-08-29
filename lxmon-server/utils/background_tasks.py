"""
Background task system for processing metrics and alerts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, delete

from core.database import get_background_db_session
from models.models import Metric, AlertRule, Alert, Server
from database.redis_client import redis_client
from utils.exceptions import ServerConnectionError

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manager for background tasks."""

    def __init__(self):
        self.tasks: List[asyncio.Task] = []
        self.is_running = False

    async def start(self):
        """Start all background tasks."""
        if self.is_running:
            return

        self.is_running = True
        logger.info("Starting background task manager")

        # Start metric processing task
        self.tasks.append(asyncio.create_task(self.process_metrics()))
        self.tasks.append(asyncio.create_task(self.check_alerts()))
        self.tasks.append(asyncio.create_task(self.cleanup_old_data()))
        self.tasks.append(asyncio.create_task(self.update_server_status()))

        logger.info(f"Started {len(self.tasks)} background tasks")

    async def stop(self):
        """Stop all background tasks."""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Stopping background task manager")

        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

        logger.info("Background task manager stopped")

    async def process_metrics(self):
        """Process and aggregate metrics in the background."""
        while self.is_running:
            try:
                await self._process_metrics_batch()
                await asyncio.sleep(60)  # Process every minute
            except Exception as e:
                logger.error(f"Error in metric processing: {e}")
                await asyncio.sleep(60)

    async def check_alerts(self):
        """Check alert rules and create alerts if needed."""
        while self.is_running:
            try:
                await self._check_alert_rules()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in alert checking: {e}")
                await asyncio.sleep(30)

    async def cleanup_old_data(self):
        """Clean up old metrics and alerts."""
        while self.is_running:
            try:
                await self._cleanup_old_metrics()
                await asyncio.sleep(3600)  # Clean up every hour
            except Exception as e:
                logger.error(f"Error in data cleanup: {e}")
                await asyncio.sleep(3600)

    async def update_server_status(self):
        """Update server online/offline status based on heartbeats."""
        while self.is_running:
            try:
                await self._update_server_status()
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                logger.error(f"Error in server status update: {e}")
                await asyncio.sleep(60)

    async def _process_metrics_batch(self):
        """Process a batch of recent metrics."""
        db = await get_background_db_session()
        try:
            # Get metrics from the last 5 minutes
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

            result = await db.execute(
                select(Metric).where(Metric.collected_at >= five_minutes_ago)
                .order_by(Metric.collected_at.desc())
                .limit(1000)
            )
            recent_metrics = result.scalars().all()

            if not recent_metrics:
                return

            # Group metrics by server and type for aggregation
            server_metrics: Dict[int, Dict[str, List[Metric]]] = {}

            for metric in recent_metrics:
                if metric.server_id not in server_metrics:
                    server_metrics[metric.server_id] = {}
                if metric.metric_type not in server_metrics[metric.server_id]:
                    server_metrics[metric.server_id][metric.metric_type] = []
                server_metrics[metric.server_id][metric.metric_type].append(metric)

            # Cache aggregated metrics in Redis
            for server_id, metrics_by_type in server_metrics.items():
                cache_key = f"server:{server_id}:latest_metrics"
                latest_metrics = {}

                for metric_type, metrics in metrics_by_type.items():
                    if metrics:
                        # Get the most recent metric of each type
                        latest_metric = max(metrics, key=lambda m: m.collected_at)
                        latest_metrics[metric_type] = {
                            "value": latest_metric.value,
                            "unit": latest_metric.unit,
                            "timestamp": latest_metric.collected_at.isoformat()
                        }

                await redis_client.set_cache(cache_key, latest_metrics, expire=300)  # 5 minutes

            logger.info(f"Processed {len(recent_metrics)} metrics for {len(server_metrics)} servers")
        finally:
            await db.close()

    async def _check_alert_rules(self):
        """Check all active alert rules against recent metrics."""
        db = await get_background_db_session()
        try:
            # Get all enabled alert rules
            result = await db.execute(
                select(AlertRule).where(AlertRule.enabled == True)
            )
            alert_rules = result.scalars().all()

            for rule in alert_rules:
                await self._check_single_alert_rule(db, rule)
        finally:
            await db.close()

    async def _check_single_alert_rule(self, db: AsyncSession, rule: AlertRule):
        """Check a single alert rule."""
        # Get recent metrics for this rule
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)

        result = await db.execute(
            select(Metric).join(Server).where(
                and_(
                    Metric.metric_type == rule.metric_type,
                    Metric.metric_name == rule.metric_name,
                    Metric.collected_at >= ten_minutes_ago,
                    Server.tenant_id == rule.tenant_id
                )
            ).order_by(Metric.collected_at.desc())
        )
        recent_metrics = result.scalars().all()

        if not recent_metrics:
            return

        # Check if any metric violates the rule
        violations = []
        for metric in recent_metrics:
            if self._check_threshold(metric.value, rule.threshold, rule.condition):
                violations.append(metric)

        if violations:
            # Check if alert already exists for this rule and server
            latest_violation = max(violations, key=lambda m: m.collected_at)

            result = await db.execute(
                select(Alert).where(
                    and_(
                        Alert.alert_rule_id == rule.id,
                        Alert.server_id == latest_violation.server_id,
                        Alert.status == "active"
                    )
                )
            )
            existing_alert = result.scalar_one_or_none()

            if not existing_alert:
                # Create new alert
                alert = Alert(
                    alert_rule_id=rule.id,
                    server_id=latest_violation.server_id,
                    message=f"{rule.name}: {rule.metric_name} is {rule.condition} {rule.threshold}",
                    severity=rule.severity,
                    status="active",
                    triggered_at=datetime.utcnow()
                )
                db.add(alert)
                await db.commit()

                logger.warning(f"Alert triggered: {alert.message}")

    def _check_threshold(self, value: float, threshold: float, condition: str) -> bool:
        """Check if value violates threshold based on condition."""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "ne":
            return value != threshold
        return False

    async def _cleanup_old_metrics(self):
        """Clean up old metrics to prevent database bloat."""
        db = await get_background_db_session()
        try:
            # Delete metrics older than 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            result = await db.execute(
                select(func.count(Metric.id)).where(Metric.collected_at < thirty_days_ago)
            )
            old_metrics_count = result.scalar()

            if old_metrics_count > 0:
                await db.execute(
                    delete(Metric).where(Metric.collected_at < thirty_days_ago)
                )
                await db.commit()
                logger.info(f"Cleaned up {old_metrics_count} old metrics")

        finally:
            await db.close()

    async def _update_server_status(self):
        """Update server status based on heartbeat timestamps."""
        db = await get_background_db_session()
        try:
            # Mark servers as offline if no heartbeat in last 5 minutes
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

            result = await db.execute(
                select(Server).where(
                    and_(
                        Server.last_heartbeat < five_minutes_ago,
                        Server.status != "offline"
                    )
                )
            )
            offline_servers = result.scalars().all()

            for server in offline_servers:
                server.status = "offline"
                server.updated_at = datetime.utcnow()
                logger.warning(f"Server {server.hostname} marked as offline")

            if offline_servers:
                await db.commit()
        finally:
            await db.close()


# Global background task manager
background_tasks = BackgroundTaskManager()
