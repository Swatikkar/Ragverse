from fastapi import APIRouter, HTTPException, Depends
from auth.schemas import RegisterRequest, LoginRequest, TokenResponse
from auth.service import register_user, login_user, delete_user_account
from auth.dependencies import get_current_user
 
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


@router.delete("/me")
async def delete_me(current_user: dict = Depends(get_current_user)):
    try:
        delete_user_account(current_user["user_id"])
        return {"success": True, "message": "Account and workspace deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
