from fastapi import APIRouter

from core.model_router import ModelRouter

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/info")
async def models_info():
    return ModelRouter.list_all()
