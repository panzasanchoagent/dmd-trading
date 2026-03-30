"""
Principles Router - Trading rules and belief system.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import personal_db
from models import PrincipleCreate

router = APIRouter()


class PrincipleResponse(BaseModel):
    """Trading principle with tracking stats."""
    id: UUID
    title: str
    description: str
    category: Optional[str] = None
    rule_type: Optional[str] = None
    quantifiable: bool = False
    metric: Optional[str] = None
    threshold: Optional[float] = None
    times_followed: int = 0
    times_violated: int = 0
    last_violated_at: Optional[datetime] = None
    active: bool = True
    priority: int = 5
    created_at: datetime
    updated_at: datetime


class RecordEventRequest(BaseModel):
    """Request to record principle follow/violation."""
    followed: bool
    notes: Optional[str] = None
    trade_id: Optional[UUID] = None


@router.post("")
async def create_principle(principle: PrincipleCreate):
    """
    Create a new trading principle.
    
    Categories: risk, entry, exit, sizing, psychology
    Rule types: hard (never break), soft (guideline)
    """
    try:
        principle_data = principle.model_dump(exclude_none=True)
        
        # Convert Decimal to float
        if "threshold" in principle_data and principle_data["threshold"]:
            principle_data["threshold"] = float(principle_data["threshold"])
        
        result = await personal_db.create_principle(principle_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_principles(
    active_only: bool = Query(True),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """List all trading principles."""
    try:
        principles = await personal_db.list_principles(active_only=active_only)
        
        if category:
            principles = [p for p in principles if p.get("category") == category]
        
        # Calculate adherence rate
        for p in principles:
            total = p.get("times_followed", 0) + p.get("times_violated", 0)
            p["adherence_rate"] = (p.get("times_followed", 0) / total * 100) if total > 0 else None
        
        return {
            "principles": principles,
            "count": len(principles),
            "categories": list(set(p.get("category") for p in principles if p.get("category")))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/violations")
async def get_recent_violations(days: int = Query(30, ge=1, le=90)):
    """Get principles violated in the last N days."""
    try:
        violations = await personal_db.get_recent_violations(days=days)
        
        return {
            "violations": violations,
            "count": len(violations),
            "period_days": days,
            "message": f"{len(violations)} principles violated in last {days} days" if violations else "No recent violations"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_principles_dashboard():
    """
    Get principles dashboard with adherence summary.
    
    Shows overall discipline metrics.
    """
    try:
        principles = await personal_db.list_principles(active_only=True)
        
        if not principles:
            return {
                "total_principles": 0,
                "overall_adherence": None,
                "categories": {},
                "worst_performers": [],
                "best_performers": []
            }
        
        # Calculate overall stats
        total_followed = sum(p.get("times_followed", 0) for p in principles)
        total_violated = sum(p.get("times_violated", 0) for p in principles)
        total_events = total_followed + total_violated
        
        # Calculate per-principle adherence
        for p in principles:
            events = p.get("times_followed", 0) + p.get("times_violated", 0)
            p["adherence_rate"] = (p.get("times_followed", 0) / events * 100) if events > 0 else None
            p["total_events"] = events
        
        # Filter to those with enough data
        with_data = [p for p in principles if p.get("total_events", 0) >= 3]
        
        # Sort for best/worst
        with_adherence = [p for p in with_data if p.get("adherence_rate") is not None]
        worst = sorted(with_adherence, key=lambda p: p["adherence_rate"])[:5]
        best = sorted(with_adherence, key=lambda p: p["adherence_rate"], reverse=True)[:5]
        
        # By category
        categories = {}
        for p in principles:
            cat = p.get("category", "uncategorized") or "uncategorized"
            if cat not in categories:
                categories[cat] = {"followed": 0, "violated": 0, "count": 0}
            categories[cat]["followed"] += p.get("times_followed", 0)
            categories[cat]["violated"] += p.get("times_violated", 0)
            categories[cat]["count"] += 1
        
        for cat, stats in categories.items():
            total = stats["followed"] + stats["violated"]
            stats["adherence_rate"] = (stats["followed"] / total * 100) if total > 0 else None
        
        return {
            "total_principles": len(principles),
            "overall_adherence": (total_followed / total_events * 100) if total_events > 0 else None,
            "total_events": total_events,
            "categories": categories,
            "worst_performers": [
                {"title": p["title"], "adherence": p["adherence_rate"], "events": p["total_events"]}
                for p in worst
            ],
            "best_performers": [
                {"title": p["title"], "adherence": p["adherence_rate"], "events": p["total_events"]}
                for p in best
            ],
            "hard_rules_status": _check_hard_rules(principles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _check_hard_rules(principles):
    """Check status of hard rules (should never be violated)."""
    hard_rules = [p for p in principles if p.get("rule_type") == "hard"]
    
    violated_hard = [p for p in hard_rules if p.get("times_violated", 0) > 0]
    
    return {
        "total_hard_rules": len(hard_rules),
        "violated_count": len(violated_hard),
        "violated_rules": [p["title"] for p in violated_hard],
        "status": "clean" if not violated_hard else "violations"
    }


@router.get("/{principle_id}")
async def get_principle(principle_id: UUID):
    """Get a single principle by ID."""
    try:
        principle = await personal_db.get_principle(str(principle_id))
        if not principle:
            raise HTTPException(status_code=404, detail="Principle not found")
        
        # Calculate adherence
        total = principle.get("times_followed", 0) + principle.get("times_violated", 0)
        principle["adherence_rate"] = (principle.get("times_followed", 0) / total * 100) if total > 0 else None
        
        return principle
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{principle_id}")
async def update_principle(principle_id: UUID, principle: PrincipleCreate):
    """Update a principle."""
    try:
        principle_data = principle.model_dump(exclude_none=True)
        
        if "threshold" in principle_data and principle_data["threshold"]:
            principle_data["threshold"] = float(principle_data["threshold"])
        
        result = await personal_db.update_principle(str(principle_id), principle_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{principle_id}/record")
async def record_principle_event(principle_id: UUID, event: RecordEventRequest):
    """
    Record a principle follow or violation.
    
    Use this to track adherence over time.
    """
    try:
        result = await personal_db.record_principle_event(
            str(principle_id),
            followed=event.followed
        )
        
        action = "followed" if event.followed else "violated"
        return {
            "status": "recorded",
            "principle_id": str(principle_id),
            "action": action,
            "new_stats": {
                "times_followed": result.get("times_followed"),
                "times_violated": result.get("times_violated")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{principle_id}")
async def deactivate_principle(principle_id: UUID):
    """
    Deactivate a principle (soft delete).
    
    Principles are not deleted, just marked inactive.
    """
    try:
        result = await personal_db.update_principle(
            str(principle_id),
            {"active": False}
        )
        return {"status": "deactivated", "principle_id": str(principle_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Default principles template
DEFAULT_PRINCIPLES = [
    {
        "title": "Never risk more than 2% per trade",
        "description": "Maximum loss on any single trade should not exceed 2% of portfolio value",
        "category": "risk",
        "rule_type": "hard",
        "quantifiable": True,
        "metric": "max_loss_pct",
        "threshold": 2.0,
        "priority": 10
    },
    {
        "title": "Always use stop losses",
        "description": "Every position must have a defined stop loss before entry",
        "category": "risk",
        "rule_type": "hard",
        "priority": 10
    },
    {
        "title": "No revenge trading",
        "description": "Wait at least 2 hours after a loss before entering a new trade",
        "category": "psychology",
        "rule_type": "hard",
        "priority": 9
    },
    {
        "title": "Size positions according to conviction",
        "description": "Higher conviction = larger size, but never exceed max position limits",
        "category": "sizing",
        "rule_type": "soft",
        "priority": 7
    },
    {
        "title": "Journal every trading day",
        "description": "Write a journal entry on every day you make a trade",
        "category": "psychology",
        "rule_type": "soft",
        "priority": 6
    }
]


@router.post("/seed-defaults")
async def seed_default_principles():
    """
    Seed the default trading principles.
    
    Use this to initialize principles for a new user.
    """
    try:
        created = []
        for p in DEFAULT_PRINCIPLES:
            result = await personal_db.create_principle(p)
            created.append(result)
        
        return {
            "status": "seeded",
            "count": len(created),
            "principles": created
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
