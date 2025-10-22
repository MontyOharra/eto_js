from dataclasses import dataclass
from typing import List, Optional
from pydantic import BaseModel


@dataclass
class FilterRule:
    field: str
    operation: str
    value: str
    case_sensitive: bool


@dataclass
class EmailAccount:
    email_address: str
    display_name: Optional[str] = None