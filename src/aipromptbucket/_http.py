"""HTTP transport layer with retry, logging, and connection pooling."""

from __future__ import annotations

import json
import logging
import time

logger = logging.getLogger("aipromptbucket")

_MAX_RETRIES = 3
_INITIAL_BACKOFF = 0.5  # seconds; doubles each retry
_USER_AGENT = "AIPromptBucket-Python/0.1.0"
_LOG_PREFIX = "AIPROMPTBUCKET_UNSENT_REQUEST"

_client = None


def _get_client():
    import httpx

    global _client
    if _client is None or _client.is_closed:
        _client = httpx.Client(
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0),
            headers={"User-Agent": _USER_AGENT},
        )
    return _client


def _is_retryable(status_code: int) -> bool:
    return status_code in (429, 500, 502, 503, 504)


def _log_unsent(method: str, url: str, reason: str, body: dict | None = None) -> None:
    logger.warning(
        "%s method=%s url=%s reason=%s payload=%s",
        _LOG_PREFIX,
        method,
        url,
        reason,
        json.dumps(body, separators=(",", ":")) if body else "null",
    )


def request(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    json_body: dict | None = None,
    params: dict | None = None,
) -> tuple[int, dict | None]:
    """Make an HTTP request with retry on transient failures.

    Returns (status_code, parsed_json_or_None).
    """
    import httpx

    client = _get_client()
    last_err = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = client.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
            )

            if _is_retryable(resp.status_code) and attempt < _MAX_RETRIES:
                logger.info(
                    "Server returned %d, retrying (%d/%d)",
                    resp.status_code,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                time.sleep(_INITIAL_BACKOFF * (2**attempt))
                continue

            try:
                data = resp.json()
            except Exception:
                data = None

            return resp.status_code, data

        except httpx.TransportError as e:
            last_err = e
            if attempt < _MAX_RETRIES:
                logger.info(
                    "Request failed (%s), retrying (%d/%d)",
                    e,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                time.sleep(_INITIAL_BACKOFF * (2**attempt))
                continue

    reason = f"unreachable:{type(last_err).__name__}:{last_err}" if last_err else "unreachable:unknown"
    _log_unsent(method, url, reason, json_body)
    return 0, {"detail": f"Server unreachable after {_MAX_RETRIES} retries ({type(last_err).__name__})" if last_err else "Server unreachable"}
