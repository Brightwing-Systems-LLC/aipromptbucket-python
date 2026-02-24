"""Response types for the AI Prompt Bucket API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class APIResponse(Generic[T]):
    """Wrapper for all API responses. Check `ok` before accessing `data`."""

    ok: bool
    status_code: int
    data: T | None = None
    error: str | None = None


# ── Prompt types ──


@dataclass
class LabelInfo:
    label_name: str
    version_number: int
    is_system: bool
    updated_at: str


@dataclass
class Prompt:
    id: str
    slug: str
    name: str
    description: str
    template_format: str
    tags: list[str]
    variable_schema: dict | None
    parent_prompt_slug: str | None
    version_count: int
    labels: list[LabelInfo]
    created_at: str
    updated_at: str


@dataclass
class PromptSummary:
    id: str
    slug: str
    name: str
    description: str
    template_format: str
    tags: list[str]
    version_count: int
    updated_at: str


@dataclass
class PromptVersion:
    id: str
    version_number: int
    template_text: str
    change_note: str
    created_by: str | None
    created_at: str


@dataclass
class RenderResult:
    rendered_text: str
    token_estimate: int
    version_number: int
    label: str


# ── Label types ──


@dataclass
class TeamLabel:
    id: str
    name: str
    is_protected: bool
    is_system: bool
    description: str
    created_at: str


@dataclass
class PromptLabel:
    label_name: str
    version_number: int
    is_system: bool
    updated_at: str


@dataclass
class ImpactResult:
    prompt_slug: str
    affected_prompts: list[dict[str, Any]]
    affected_count: int


# ── Snapshot types ──


@dataclass
class Snapshot:
    id: str
    name: str
    description: str
    created_by: str | None
    created_at: str


# ── Health Score types ──


@dataclass
class HealthScore:
    overall_grade: str
    overall_score: int
    completeness_score: int
    maintenance_score: int
    deployment_score: int
    coverage_score: int
    detail: dict[str, Any]
    computed_at: str


# ── Analysis types ──


@dataclass
class AnalysisFinding:
    type: str
    severity: str
    message: str
    prompt_slugs: list[str]
    detail: dict[str, Any]


@dataclass
class AnalysisResult:
    id: str
    analysis_type: str
    findings: list[AnalysisFinding]
    summary: str
    created_at: str


# ── System types ──


@dataclass
class HealthCheck:
    status: str
    version: str
    timestamp: str


# ── Scanner types ──


@dataclass
class ScanFinding:
    file: str
    line: int
    text: str
    variables: list[str]
    detected_format: str = "jinja2"
