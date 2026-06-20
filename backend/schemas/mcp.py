from pydantic import BaseModel, field_validator


class SearchKnowledgeInput(BaseModel):
    query: str
    mode: str = "mix"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()

    @field_validator("mode")
    @classmethod
    def mode_valid(cls, v: str) -> str:
        if v not in {"mix", "local", "global"}:
            raise ValueError("mode must be one of: mix, local, global")
        return v


class GetEntityOutput(BaseModel):
    name: str
    type: str
    description: str | None = None
    relations: list = []
    sources: list = []


class PushKnowledgeInput(BaseModel):
    entity_name: str
    entity_type: str
    description: str
    relations: list
    source: str


class PushKnowledgeOutput(BaseModel):
    ok: bool
    entity_name: str
    relations_added: int
