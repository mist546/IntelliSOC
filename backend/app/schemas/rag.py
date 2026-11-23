from pydantic import BaseModel


class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 4
    categories: list[str] | None = None  # restrict to top-level folders, e.g. ["response_playbooks"]


class RAGResultOut(BaseModel):
    content: str
    source: str
    title: str
    category: str
    score: float
    page: int | None = None
    heading: str | None = None
    match: str = "semantic"


class RAGSearchResponseOut(BaseModel):
    available: bool
    message: str = ""
    results: list[RAGResultOut]
