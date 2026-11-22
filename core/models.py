"""Shared data models passed between agents.

Every agent receives a ResearchState and returns an updated ResearchState.
That object is the "handoff" between roles.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Source(BaseModel):
    id: int
    title: str
    url: str
    snippet: str = ""
    content: str = ""
    scraped: bool = False


class Finding(BaseModel):
    fact: str
    source_ids: list[int] = Field(default_factory=list)


class ResearchFindings(BaseModel):
    search_queries: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    search_provider: str = ""
    scraped_count: int = 0
    is_sample_data: bool = False


class Competitor(BaseModel):
    name: str
    description: str
    source_ids: list[int] = Field(default_factory=list)


class Brief(BaseModel):
    summary: str
    competitors: list[Competitor] = Field(default_factory=list, max_length=2)
    key_observations: list[str] = Field(default_factory=list)
    source_ids: list[int] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class CriticFeedback(BaseModel):
    approved: bool
    issues: list[str] = Field(default_factory=list)
    revision_instructions: str = ""


class ResearchState(BaseModel):
    query: str
    findings: ResearchFindings | None = None
    draft: Brief | None = None
    feedback: CriticFeedback | None = None
    revised_draft: Brief | None = None
    revision_count: int = 0
    final_brief: Brief | None = None
    log: list[str] = Field(default_factory=list)

    def add_log(self, agent: str, message: str) -> None:
        self.log.append(f"[{agent}] {message}")
