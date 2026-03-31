from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

import httpx


async def retry_http_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    retries: int = 2,
    backoff_seconds: float = 1.25,
    retry_statuses: Iterable[int] = (429, 500, 502, 503, 504),
    **kwargs: Any,
) -> httpx.Response:
    attempt = 0
    last_error: Exception | None = None

    while attempt <= retries:
        try:
            response = await client.request(method=method, url=url, **kwargs)
            if response.status_code in retry_statuses and attempt < retries:
                await asyncio.sleep(backoff_seconds * (attempt + 1))
                attempt += 1
                continue
            response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_error = exc
            if attempt >= retries:
                break
            await asyncio.sleep(backoff_seconds * (attempt + 1))
            attempt += 1

    raise RuntimeError(f"HTTP request failed after {retries + 1} attempts: {url}") from last_error


def extract_json_object(raw_text: str) -> dict[str, Any]:
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = strip_code_fences(raw_text)

    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("Model response JSON is not an object.")
    return parsed


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


def coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        pieces = [piece.strip() for piece in value.split(",")]
        return [piece for piece in pieces if piece]
    return [str(value).strip()] if str(value).strip() else []


def coerce_int(value: Any, fallback: int = 0) -> int:
    if value is None:
        return fallback
    try:
        if isinstance(value, str):
            value = value.replace(",", "").strip()
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def elapsed_ms(start: float) -> int:
    """Return milliseconds elapsed since a perf_counter() start time."""
    return int((perf_counter() - start) * 1000)


def format_bullet_list(items: list[str], bullet: str = "- ") -> str:
    """Join a list of strings as a bullet-point block."""
    return "\n".join(f"{bullet}{item}" for item in items)


def save_json_file(data: dict[str, Any], output_dir: Path, file_name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / file_name
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, default=_json_serializer)
    return path


def _json_serializer(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
