from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Stage(StrEnum):
    PLANNED = "planned"
    CAPTURED = "captured"
    WRITTEN = "written"
    CHECKED = "checked"
    RENDERED = "rendered"
    UPLOADED = "uploaded"
    HANDED_OFF = "handed_off"
    RECORDED = "recorded"
    PUBLISHED = "published"
    NEEDS_REVIEW = "needs_review"
    NEEDS_RECONCILE = "needs_reconcile"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
