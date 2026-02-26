"""Drop-in get_prompt() function for zero-ceremony prompt fetching."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import time
from typing import Any

from .client import Client

logger = logging.getLogger("aipromptbucket")

# ── Module-level state ──

_client: Client | None = None
_client_config: tuple[str, str] = ("", "")  # (api_key, base_url) for singleton
_defaults: dict[str, Any] = {}
_cache: dict[str, tuple[str, float]] = {}  # key → (text, expiry_timestamp)
_cache_loaded = False


def _cache_file_path() -> Path:
    custom_path = os.environ.get("AIPROMPTBUCKET_CACHE_PATH")
    if custom_path:
        return Path(custom_path).expanduser()
    return Path.home() / ".cache" / "aipromptbucket" / "prompts.json"


def _load_cache_from_disk() -> None:
    global _cache_loaded
    if _cache_loaded:
        return

    cache_path = _cache_file_path()
    if not cache_path.exists():
        _cache_loaded = True
        return

    try:
        import json

        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            for key, value in payload.items():
                if not isinstance(value, dict):
                    continue
                text = value.get("text")
                expiry = value.get("expiry")
                if isinstance(text, str) and isinstance(expiry, (int, float)):
                    _cache[key] = (text, float(expiry))
    except Exception as exc:
        logger.warning("aipromptbucket: failed to load disk cache: %s", exc)

    _cache_loaded = True


def _save_cache_to_disk() -> None:
    cache_path = _cache_file_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        key: {"text": text, "expiry": expiry}
        for key, (text, expiry) in _cache.items()
    }

    try:
        import json

        cache_path.write_text(json.dumps(payload), encoding="utf-8")
    except Exception as exc:
        logger.warning("aipromptbucket: failed to save disk cache: %s", exc)


def configure(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    default_label: str | None = None,
    default_fallback_label: str | None = None,
    default_ttl: int | None = None,
) -> None:
    """Set defaults for all subsequent get_prompt() calls.

    Replaces the singleton client if api_key or base_url differ from current.
    """
    global _client, _client_config, _defaults, _cache

    if api_key is not None:
        _defaults["api_key"] = api_key
    if base_url is not None:
        _defaults["base_url"] = base_url
    if default_label is not None:
        _defaults["default_label"] = default_label
    if default_fallback_label is not None:
        _defaults["default_fallback_label"] = default_fallback_label
    if default_ttl is not None:
        _defaults["default_ttl"] = default_ttl

    # Rebuild singleton with new config
    resolved_key = _defaults.get("api_key", "")
    resolved_url = _defaults.get("base_url", "")
    new_config = (resolved_key, resolved_url)
    if new_config != _client_config:
        _client = Client(api_key=resolved_key or None, base_url=resolved_url or None)
        _client_config = new_config
        _cache.clear()


def _get_client(api_key: str | None, base_url: str | None) -> Client:
    """Return the singleton client, or a one-off client if overrides differ."""
    global _client, _client_config

    resolved_key = api_key or _defaults.get("api_key", "")
    resolved_url = base_url or _defaults.get("base_url", "")
    requested = (resolved_key, resolved_url)

    if _client is not None and requested == _client_config:
        return _client

    # First call or config matches defaults — create/update singleton
    if not api_key and not base_url:
        if _client is None:
            _client = Client(
                api_key=resolved_key or None,
                base_url=resolved_url or None,
            )
            _client_config = requested
        return _client

    # Per-call overrides differ from singleton — use a separate client
    return Client(api_key=resolved_key or None, base_url=resolved_url or None)


def _cache_key(slug: str, label: str, variables: dict[str, str] | None) -> str:
    """Build a deterministic cache key."""
    var_part = ""
    if variables:
        var_part = str(sorted(variables.items()))
    return f"{slug}:{label}:{var_part}"


def get_prompt(
    slug: str,
    *,
    variables: dict[str, str] | None = None,
    label: str | None = None,
    fallback_label: str | None = None,
    fallback: str | None = None,
    ttl: int | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> str | None:
    """Fetch a rendered prompt by slug. Returns text, fallback, or None.

    This is the simplest way to use AI Prompt Bucket — a single function call
    that handles client lifecycle, caching, and error recovery internally.

    Args:
        slug: The prompt slug to fetch.
        variables: Template variables to render with. If provided, calls
            the render endpoint; otherwise returns raw template text.
        label: Label to fetch (e.g. "production", "staging"). Defaults to
            AIPROMPTBUCKET_DEFAULT_LABEL env var, then "production".
        fallback_label: Backup label to try if the primary label fetch fails.
        fallback: Text to return if the fetch fails and no cached prompt exists.
        ttl: Cache duration in seconds. 0 or None disables caching.
        api_key: Override the API key for this call only.
        base_url: Override the base URL for this call only.

    Returns:
        The rendered prompt text, stale cached prompt, fallback string, or None.
    """
    resolved_label = (
        label
        or _defaults.get("default_label")
        or os.environ.get("AIPROMPTBUCKET_DEFAULT_LABEL")
        or "production"
    )
    resolved_ttl = ttl if ttl is not None else _defaults.get("default_ttl")
    resolved_fallback_label = fallback_label or _defaults.get("default_fallback_label")
    _load_cache_from_disk()

    # Check cache
    key = _cache_key(slug, resolved_label, variables)
    stale_text: str | None = None
    if resolved_ttl:
        entry = _cache.get(key)
        if entry is not None:
            text, expiry = entry
            if time.time() < expiry:
                return text
            stale_text = text

    try:
        client = _get_client(api_key, base_url)

        resp = client.render(slug, label=resolved_label, variables=variables)
        if resp.ok and resp.data:
            text = resp.data.rendered_text
        else:
            if resolved_fallback_label and resolved_fallback_label != resolved_label:
                logger.warning(
                    "aipromptbucket: fetch failed for '%s' on label '%s': %s; trying fallback label '%s'",
                    slug,
                    resolved_label,
                    resp.error,
                    resolved_fallback_label,
                )
                resp = client.render(slug, label=resolved_fallback_label, variables=variables)

            if resp.ok and resp.data:
                text = resp.data.rendered_text
            else:
                logger.warning("aipromptbucket: fetch failed for '%s': %s", slug, resp.error)
                return stale_text or fallback

        # Store in cache
        if resolved_ttl:
            _cache[key] = (text, time.time() + resolved_ttl)
            _save_cache_to_disk()

        return text

    except Exception as exc:
        logger.warning("aipromptbucket: unexpected error for '%s': %s", slug, exc)
        return stale_text or fallback
