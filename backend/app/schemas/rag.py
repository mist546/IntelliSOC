from pydantic import BaseModel


class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 4


class RAGResultOut(BaseModel):
    content: str
    source: str
    title: str
    category: str
    score: float


class RAGSearchResponseOut(BaseModel):
    available: bool
    message: str = ""
    results: list[RAGResultOut]
