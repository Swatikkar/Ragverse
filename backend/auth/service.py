from __future__ import annotations

import sqlite3
import uuid

import bcrypt
from fastapi import HTTPException
from supabase import Client, create_client

import config
from auth.jwt_handler import create_access_token
from auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from utils.local_db import get_connection, utc_now


_supabase: Client | None = None


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _supabase_client() -> Client:
    global _supabase
    if _supabase is None:
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise HTTPException(status_code=503, detail="Supabase auth is not configured.")
        try:
            _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Supabase auth is unavailable: {exc}") from exc
    return _supabase


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["id"]),
        email=user["email"],
        full_name=user.get("full_name"),
        is_active=bool(user.get("is_active", True)),
        created_at=user["created_at"],
    )


def _token_response(user: dict) -> TokenResponse:
    return TokenResponse(
        success=True,
        access_token=create_access_token(str(user["id"]), user["email"]),
        user=_user_response(user),
    )


def _register_local(data: RegisterRequest) -> TokenResponse:
    user_id = str(uuid.uuid4())
    now = utc_now()
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, hashed_password, full_name, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (user_id, data.email, _hash_password(data.password), data.full_name, now, now),
            )
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")

    return _token_response(dict(row))


def _login_local(data: LoginRequest) -> TokenResponse:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (data.email,)).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = dict(row)
    if not bool(user["is_active"]):
        raise HTTPException(status_code=403, detail="Account is disabled")
    if not _verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return _token_response(user)


def _register_supabase(data: RegisterRequest) -> TokenResponse:
    client = _supabase_client()
    try:
        existing = client.table("users").select("id").eq("email", data.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")

        result = client.table("users").insert({
            "id": str(uuid.uuid4()),
            "email": data.email,
            "hashed_password": _hash_password(data.password),
            "full_name": data.full_name,
            "is_active": True,
        }).execute()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Supabase auth is unavailable: {exc}") from exc

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return _token_response(result.data[0])


def _login_supabase(data: LoginRequest) -> TokenResponse:
    client = _supabase_client()
    try:
        result = client.table("users").select("*").eq("email", data.email).execute()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Supabase auth is unavailable: {exc}") from exc

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data[0]
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is disabled")
    if not _verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return _token_response(user)


def register_user(data: RegisterRequest) -> TokenResponse:
    if config.AUTH_PROVIDER == "supabase":
        return _register_supabase(data)
    return _register_local(data)


def login_user(data: LoginRequest) -> TokenResponse:
    if config.AUTH_PROVIDER == "supabase":
        return _login_supabase(data)
    return _login_local(data)
