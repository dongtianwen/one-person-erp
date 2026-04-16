"""v2.1 经营数据自由问答 API。"""
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


class QAAskRequest(BaseModel):
    question: str
    history: Optional[List[dict]] = None


@router.post("/ask")
async def ask_question(
    req: QAAskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """经营数据自由问答。"""
    from app.core.qa_service import ask_question
    result = await ask_question(db, req.question, req.history)
    return {"code": 0, "data": result}
