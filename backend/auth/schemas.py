from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
 
 
# ── Request schemas ──────────────────────────────────────────────
 
class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
 
 
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
 
 
# ── Response schemas ─────────────────────────────────────────────
 
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
 
 
class TokenResponse(BaseModel):
    success: bool
    access_token: str
    token_type: str = "bearer"
    user: UserResponse