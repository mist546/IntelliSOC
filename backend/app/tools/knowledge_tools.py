"""Knowledge tools the investigator calls. Each returns plain dicts:
{"available", "message", "results": [{content, source, title, category,
score, page, heading, match}]}."""
from app.services.rag.rule_knowledge import background_categories, knowledge_for
from app.services.rag.service import RAGSearchResponse
from app.services.rag.service import search_security_knowledge as _search


def _as_dict(response: RAGSearchResponse) -> dict:
    return {
        "available": response.available,
        "message": response.message,
        "results": [
            {
                "content": r.content, "source": r.source, "title": r.title, "category": r.category,
                "score": r.score, "page": r.page, "heading": r.heading, "match": r.match,
            }
            for r in response.results
        ],
    }


def search_security_knowledge(query: str, top_k: int = 4, categories: list[str] | None = None) -> dict:
    return _as_dict(_search(query, top_k=top_k, categories=categories))


def _mapped_or_folder(query: str, sources: tuple[str, ...], folders: list[str]) -> dict:
    """Search the rule's mapped documents (min_score=0: they are relevant by
    definition); if none of them exist, fall back to a normal relevance
    search over the given folders."""
    mapped = _as_dict(_search(query, top_k=3, sources=list(sources), min_score=0.0))
    if not mapped["available"] or mapped["results"]:
        return mapped
    return _as_dict(_search(query, top_k=3, categories=folders))


def get_investigation_playbook(detection_rule: str, context: str = "") -> dict:
    """The sections of this rule's investigation playbook(s) most relevant
    to the alert. Response playbooks are included in the fallback because
    they also carry investigation steps."""
    knowledge = knowledge_for(detection_rule)
    query = f"how to investigate and verify {knowledge.topic}. {context}".strip()
    return _mapped_or_folder(query, knowledge.investigation, ["investigation_playbooks", "response_playbooks"])


def get_response_playbook(detection_rule: str, context: str = "") -> dict:
    """The recommended-response sections for this rule (response playbooks
    only - never general knowledge)."""
    knowledge = knowledge_for(detection_rule)
    query = f"recommended response and containment actions for {knowledge.topic}. {context}".strip()
    return _mapped_or_folder(query, knowledge.response, ["response_playbooks"])


def get_background_knowledge(detection_rule: str, context: str = "", top_k: int = 4) -> dict:
    """What the attack is: attack/vulnerability knowledge, MITRE ATT&CK,
    OWASP, NIST. The rule's IDs (e.g. T1110, CWE-89) are included in the
    query so the matching entries are found by exact identifier."""
    knowledge = knowledge_for(detection_rule)
    query = f"{knowledge.topic} {' '.join(knowledge.identifiers)} {context}".strip()
    wider = _as_dict(_search(query, top_k=top_k, categories=list(background_categories(detection_rule))))
    if not knowledge.background:
        return wider
    # The rule's own attack/vulnerability documents first, then the rest.
    mapped = _as_dict(_search(query, top_k=2, sources=list(knowledge.background), min_score=0.0))
    seen: set[tuple] = set()
    merged = []
    for result in mapped["results"] + wider["results"]:
        key = (result["source"], result["content"])
        if key not in seen:
            seen.add(key)
            merged.append(result)
    return {
        "available": mapped["available"] or wider["available"],
        "message": wider["message"] if not merged else "",
        "results": merged[:top_k],
    }
