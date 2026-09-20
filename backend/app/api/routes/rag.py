from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.schemas.rag import RAGSearchRequest, RAGSearchResponseOut
from app.services.rag.service import search_security_knowledge

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/search", response_model=RAGSearchResponseOut)
def rag_search(payload: RAGSearchRequest, _user=Depends(get_current_user)):
    response = search_security_knowledge(payload.query, top_k=payload.top_k)
    return RAGSearchResponseOut(
        available=response.available,
        message=response.message,
        results=[
            {"content": r.content, "source": r.source, "title": r.title, "category": r.category, "score": r.score}
            for r in response.results
        ],
    )
