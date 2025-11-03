# types_eto_run_extraction.py
from __future__ import annotations

from typing import Annotated
from datetime import datetime, timezone

from pydantic import BeforeValidator

def _as_utc(v: object) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        # Accept ISO strings; treat 'Z' as UTC
        v = v.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    raise TypeError("Invalid datetime value")

UtcDateTime = Annotated[datetime, BeforeValidator(_as_utc)]
