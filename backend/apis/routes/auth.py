from fastapi import APIRouter, HTTPException
from auth.schemas import RegisterRequest, LoginRequest, TokenResponse
from auth.service import register_user, login_user
 
router = APIRouter()
 
 
@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest):
    try:
        return register_user(data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    try:
        return login_user(data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 