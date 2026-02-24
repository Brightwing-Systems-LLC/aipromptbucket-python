"""AI Prompt Bucket — Python SDK for managing prompts via API."""

__version__ = "0.1.0"

from .client import Client
from .drop_in import configure, get_prompt
from .scanner import Scanner
from .types import (
    AnalysisFinding,
    AnalysisResult,
    APIResponse,
    HealthCheck,
    HealthScore,
    ImpactResult,
    LabelInfo,
    Prompt,
    PromptLabel,
    PromptSummary,
    PromptVersion,
    RenderResult,
    ScanFinding,
    Snapshot,
    TeamLabel,
)

__all__ = [
    "Client",
    "Scanner",
    "configure",
    "get_prompt",
    "APIResponse",
    "AnalysisFinding",
    "AnalysisResult",
    "HealthCheck",
    "HealthScore",
    "ImpactResult",
    "LabelInfo",
    "Prompt",
    "PromptLabel",
    "PromptSummary",
    "PromptVersion",
    "RenderResult",
    "ScanFinding",
    "Snapshot",
    "TeamLabel",
]
