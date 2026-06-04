from __future__ import annotations
from datetime import date
from typing import Optional
from pydantic import BaseModel

class Member(BaseModel):
    """An insured member (employee or dependent) on a policy."""
    member_id: str
    name: str
    email: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    join_date: date
    relationship: str = "SELF"
    policy_id: str = ""
    is_active: bool = True