from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps.auth import get_current_user
from app.models.user import User
from app.services.ai_service import ai_pipeline

router = APIRouter(prefix="/ai", tags=["ai"])

class AIQueryRequest(BaseModel):
    query: str

class AIQueryResponse(BaseModel):
    type: str # table, card, chart
    title: str
    columns: list[str] | None = None
    data: list[dict] | None = None
    summary: str | None = None
    chart: dict | None = None

@router.post("/query", response_model=AIQueryResponse)
async def api_ai_query(
    body: AIQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process natural language queries securely preventing direct LLM SQL access. 
    Overrides store parameters via JWT natively.
    """
    try:
        response_dict = await ai_pipeline(body.query, current_user, db)
        return AIQueryResponse(**response_dict)
    except Exception as e:
        # Generic graceful fallback if everything fails
        return AIQueryResponse(
            type="card",
            title="Service Unavailable",
            summary=f"An internal error prevented the AI from answering: {str(e)}"
        )
