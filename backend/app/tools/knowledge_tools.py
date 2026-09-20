from app.services.rag.service import search_security_knowledge as _search


def search_security_knowledge(query: str, top_k: int = 4) -> dict:
    response = _search(query, top_k=top_k)
    return {
        "available": response.available,
        "message": response.message,
        "results": [
            {"content": r.content, "source": r.source, "title": r.title, "category": r.category, "score": r.score}
            for r in response.results
        ],
    }


def get_response_playbook(detection_rule: str) -> dict:
    query = f"response playbook recommended actions for {detection_rule.replace('_', ' ')}"
    response = _search(query, top_k=3)
    return {
        "available": response.available,
        "message": response.message,
        "results": [
            {"content": r.content, "source": r.source, "title": r.title, "category": r.category, "score": r.score}
            for r in response.results
            if r.category in ("playbook", "general")
        ]
        or [
            {"content": r.content, "source": r.source, "title": r.title, "category": r.category, "score": r.score}
            for r in response.results
        ],
    }
