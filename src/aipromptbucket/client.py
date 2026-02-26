"""AI Prompt Bucket API client."""

from __future__ import annotations

import dataclasses
import logging
import os
from typing import Any

from . import _http
from .types import (
    APIResponse,
    AnalysisFinding,
    AnalysisResult,
    HealthCheck,
    HealthScore,
    ImpactResult,
    LabelInfo,
    Prompt,
    PromptLabel,
    PromptSummary,
    PromptVersion,
    RenderResult,
    Snapshot,
    TeamLabel,
)


logger = logging.getLogger("aipromptbucket")


def _build(cls, data: dict) -> Any:
    """Construct a dataclass, silently dropping unknown fields.

    Prevents TypeError when the server adds new response fields that this
    SDK version doesn't know about yet.
    """
    known = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


class Client:
    """Synchronous client for the AI Prompt Bucket API.

    Configuration via constructor args or environment variables:
        AIPROMPTBUCKET_API_KEY  — required API key
        AIPROMPTBUCKET_URL      — base URL (default: https://aipromptbucket.com)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("AIPROMPTBUCKET_API_KEY", "")
        self.base_url = (
            base_url or os.environ.get("AIPROMPTBUCKET_URL", "https://aipromptbucket.com")
        ).rstrip("/")

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
    ) -> tuple[int, dict | None]:
        return _http.request(
            method,
            self._url(path),
            headers=self._headers(),
            json_body=json_body,
            params=params,
        )

    @staticmethod
    def _error(status_code: int, data: dict | None) -> str:
        if data and "detail" in data:
            return data["detail"]
        return f"HTTP {status_code}"

    # ── Prompts ──

    def list_prompts(
        self, *, tag: str | None = None, search: str | None = None
    ) -> APIResponse[list[PromptSummary]]:
        params: dict[str, str] = {}
        if tag:
            params["tag"] = tag
        if search:
            params["search"] = search
        status, data = self._request("GET", "/prompts/", params=params or None)
        if status == 200 and isinstance(data, list):
            return APIResponse(ok=True, status_code=status, data=[
                _build(PromptSummary, item) for item in data
            ])
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def get_prompt(self, slug: str) -> APIResponse[Prompt]:
        status, data = self._request("GET", f"/prompts/{slug}")
        if status == 200 and data:
            data["labels"] = [_build(LabelInfo, lb) for lb in data.get("labels", [])]
            return APIResponse(ok=True, status_code=status, data=_build(Prompt, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def create_prompt(
        self,
        *,
        name: str,
        slug: str,
        template_text: str,
        description: str = "",
        template_format: str = "jinja2",
        tags: list[str] | None = None,
        change_note: str = "Initial version",
        variable_schema: dict | None = None,
        parent_prompt_slug: str | None = None,
    ) -> APIResponse[Prompt]:
        body: dict[str, Any] = {
            "name": name,
            "slug": slug,
            "template_text": template_text,
            "description": description,
            "template_format": template_format,
            "tags": tags or [],
            "change_note": change_note,
        }
        if variable_schema:
            body["variable_schema"] = variable_schema
        if parent_prompt_slug:
            body["parent_prompt_slug"] = parent_prompt_slug

        status, data = self._request("POST", "/prompts/", json_body=body)
        if status == 201 and data:
            data["labels"] = [_build(LabelInfo, lb) for lb in data.get("labels", [])]
            return APIResponse(ok=True, status_code=status, data=_build(Prompt, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def update_prompt(
        self,
        slug: str,
        *,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        variable_schema: dict | None = None,
    ) -> APIResponse[Prompt]:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if tags is not None:
            body["tags"] = tags
        if variable_schema is not None:
            body["variable_schema"] = variable_schema

        status, data = self._request("PUT", f"/prompts/{slug}", json_body=body)
        if status == 200 and data:
            data["labels"] = [_build(LabelInfo, lb) for lb in data.get("labels", [])]
            return APIResponse(ok=True, status_code=status, data=_build(Prompt, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def delete_prompt(self, slug: str) -> APIResponse[None]:
        status, data = self._request("DELETE", f"/prompts/{slug}")
        if status == 204:
            return APIResponse(ok=True, status_code=status, data=None)
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    # ── Versions ──

    def list_versions(self, slug: str) -> APIResponse[list[PromptVersion]]:
        status, data = self._request("GET", f"/prompts/{slug}/versions")
        if status == 200 and isinstance(data, list):
            return APIResponse(ok=True, status_code=status, data=[
                _build(PromptVersion, v) for v in data
            ])
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def get_version(self, slug: str, version_number: int) -> APIResponse[PromptVersion]:
        status, data = self._request("GET", f"/prompts/{slug}/versions/{version_number}")
        if status == 200 and data:
            return APIResponse(ok=True, status_code=status, data=_build(PromptVersion, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def create_version(
        self,
        slug: str,
        *,
        template_text: str,
        change_note: str = "",
    ) -> APIResponse[PromptVersion]:
        body = {"template_text": template_text, "change_note": change_note}
        status, data = self._request("POST", f"/prompts/{slug}/versions", json_body=body)
        if status == 201 and data:
            return APIResponse(ok=True, status_code=status, data=_build(PromptVersion, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    # ── Rendering ──

    def render(
        self,
        slug: str,
        *,
        label: str = "latest",
        variables: dict[str, str] | None = None,
    ) -> APIResponse[RenderResult]:
        body: dict[str, Any] = {"label": label, "variables": variables or {}}
        status, data = self._request("POST", f"/prompts/{slug}/render", json_body=body)
        if status == 200 and data:
            return APIResponse(ok=True, status_code=status, data=_build(RenderResult, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    # ── Promote / Rollback ──

    def promote(
        self, slug: str, *, version: int, label: str
    ) -> APIResponse[Prompt]:
        body = {"version": version, "label": label}
        status, data = self._request("POST", f"/prompts/{slug}/promote", json_body=body)
        if status == 200 and data:
            data["labels"] = [_build(LabelInfo, lb) for lb in data.get("labels", [])]
            return APIResponse(ok=True, status_code=status, data=_build(Prompt, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def rollback(self, slug: str, *, label: str) -> APIResponse[Prompt]:
        body = {"label": label}
        status, data = self._request("POST", f"/prompts/{slug}/rollback", json_body=body)
        if status == 200 and data:
            data["labels"] = [_build(LabelInfo, lb) for lb in data.get("labels", [])]
            return APIResponse(ok=True, status_code=status, data=_build(Prompt, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    # ── Labels ──

    def list_labels(self) -> APIResponse[list[TeamLabel]]:
        status, data = self._request("GET", "/labels/")
        if status == 200 and isinstance(data, list):
            return APIResponse(ok=True, status_code=status, data=[
                _build(TeamLabel, lb) for lb in data
            ])
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def create_label(
        self,
        *,
        name: str,
        is_protected: bool = False,
        description: str = "",
    ) -> APIResponse[TeamLabel]:
        body = {"name": name, "is_protected": is_protected, "description": description}
        status, data = self._request("POST", "/labels/", json_body=body)
        if status == 201 and data:
            return APIResponse(ok=True, status_code=status, data=_build(TeamLabel, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def delete_label(self, name: str) -> APIResponse[None]:
        status, data = self._request("DELETE", f"/labels/{name}")
        if status == 204:
            return APIResponse(ok=True, status_code=status, data=None)
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def list_prompt_labels(self, slug: str) -> APIResponse[list[PromptLabel]]:
        status, data = self._request("GET", f"/labels/prompts/{slug}")
        if status == 200 and isinstance(data, list):
            return APIResponse(ok=True, status_code=status, data=[
                _build(PromptLabel, pl) for pl in data
            ])
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def assign_label(
        self, slug: str, *, label: str, version: int
    ) -> APIResponse[PromptLabel]:
        body = {"label": label, "version": version}
        status, data = self._request("POST", f"/labels/prompts/{slug}", json_body=body)
        if status == 200 and data:
            return APIResponse(ok=True, status_code=status, data=_build(PromptLabel, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def label_impact(self, slug: str) -> APIResponse[ImpactResult]:
        status, data = self._request("GET", f"/labels/prompts/{slug}/impact")
        if status == 200 and data:
            return APIResponse(ok=True, status_code=status, data=_build(ImpactResult, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    # ── Snapshots ──

    def list_snapshots(self) -> APIResponse[list[Snapshot]]:
        status, data = self._request("GET", "/snapshots/")
        if status == 200 and isinstance(data, list):
            return APIResponse(ok=True, status_code=status, data=[
                _build(Snapshot, s) for s in data
            ])
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def create_snapshot(
        self, *, name: str, description: str = ""
    ) -> APIResponse[Snapshot]:
        body = {"name": name, "description": description}
        status, data = self._request("POST", "/snapshots/", json_body=body)
        if status == 201 and data:
            return APIResponse(ok=True, status_code=status, data=_build(Snapshot, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def restore_snapshot(self, snapshot_id: str) -> APIResponse[Snapshot]:
        status, data = self._request("POST", f"/snapshots/{snapshot_id}/restore")
        if status == 200 and data:
            return APIResponse(ok=True, status_code=status, data=_build(Snapshot, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    # ── Health Score ──

    def get_health(self, slug: str) -> APIResponse[HealthScore]:
        status, data = self._request("GET", f"/prompts/{slug}/health")
        if status == 200 and data:
            return APIResponse(ok=True, status_code=status, data=_build(HealthScore, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def refresh_health(self, slug: str) -> APIResponse[HealthScore]:
        status, data = self._request("POST", f"/prompts/{slug}/health/refresh")
        if status == 200 and data:
            return APIResponse(ok=True, status_code=status, data=_build(HealthScore, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    # ── Analysis ──

    def list_analysis(self, *, limit: int = 5) -> APIResponse[list[AnalysisResult]]:
        status, data = self._request("GET", "/analysis/", params={"limit": str(limit)})
        if status == 200 and isinstance(data, list):
            results = []
            for item in data:
                item["findings"] = [_build(AnalysisFinding, f) for f in item.get("findings", [])]
                results.append(_build(AnalysisResult, item))
            return APIResponse(ok=True, status_code=status, data=results)
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    def run_analysis(self) -> APIResponse[AnalysisResult]:
        status, data = self._request("POST", "/analysis/run")
        if status == 200 and data:
            data["findings"] = [_build(AnalysisFinding, f) for f in data.get("findings", [])]
            return APIResponse(ok=True, status_code=status, data=_build(AnalysisResult, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))

    # ── System ──

    def health_check(self) -> APIResponse[HealthCheck]:
        status, data = self._request("GET", "/health")
        if status == 200 and data:
            return APIResponse(ok=True, status_code=status, data=_build(HealthCheck, data))
        return APIResponse(ok=False, status_code=status, error=self._error(status, data))
