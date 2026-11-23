from pydantic import BaseModel


class KnowledgeDocumentOut(BaseModel):
    id: str  # relative path inside data/knowledge_base, e.g. "custom/my_runbook.md"
    title: str
    category: str  # the top-level folder, e.g. response_playbooks, nist, custom
    source: str  # where the content came from (frontmatter `source`, usually a URL)
    file_type: str = "md"  # md | txt | pdf | json
    chunk_count: int
    uploaded_at: str | None = None
    indexed: bool = True
    deletable: bool = False  # only analyst uploads (custom/) can be deleted


class KnowledgeUploadResult(KnowledgeDocumentOut):
    message: str = ""
