"""Клиент EPO OPS для поиска и получения публичных патентных публикаций."""

import asyncio
import os
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import date
from typing import Any
from urllib.parse import quote

import httpx

from app.domain.source import FieldStatus, PatentDocument, PatentResult, SourceStatus

OPS_BASE = "https://ops.epo.org/3.2"
_DOCDB = re.compile(r"^([A-Z]{2})\.([A-Z0-9]+)\.([A-Z][0-9]?)$")
_THROTTLE = re.compile(r"(?:^|[, (])(search|retrieval)=(green|yellow|red|black):(\d+)")
_MAX_XML_BYTES = 2_000_000


@dataclass(frozen=True)
class _Failure:
    code: str
    retry_after_seconds: float | None = None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in node if _local(child.tag) == name]


def _descendants(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in node.iter() if _local(child.tag) == name]


def _text(node: ET.Element | None) -> str | None:
    if node is None:
        return None
    value = " ".join(" ".join(node.itertext()).split())
    return value or None


def _first_text(node: ET.Element, name: str) -> str | None:
    return next((_text(child) for child in _descendants(node, name) if _text(child)), None)


def _language_text(nodes: list[ET.Element]) -> str | None:
    ordered = sorted(nodes, key=lambda item: item.get("lang", "").lower() != "en")
    return next((_text(node) for node in ordered if _text(node)), None)


def _parse_xml(content: bytes) -> ET.Element:
    if (
        len(content) > _MAX_XML_BYTES
        or b"<!DOCTYPE" in content.upper()
        or b"<!ENTITY" in content.upper()
    ):
        raise ValueError("unsafe_xml")
    try:
        return ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError("invalid_xml") from exc


def _publication_parts(node: ET.Element) -> tuple[str, str, str] | None:
    country, number, kind = (node.get(key) for key in ("country", "doc-number", "kind"))
    if not all((country, number, kind)):
        references = _descendants(node, "publication-reference")
        for reference in references:
            for doc_id in _descendants(reference, "document-id"):
                if doc_id.get("document-id-type") == "docdb":
                    country = country or _first_text(doc_id, "country")
                    number = number or _first_text(doc_id, "doc-number")
                    kind = kind or _first_text(doc_id, "kind")
                    break
            if all((country, number, kind)):
                break
    if not all((country, number, kind)):
        return None
    match = _DOCDB.fullmatch(f"{country}.{number}.{kind}".upper())
    return (match.group(1), match.group(2), match.group(3)) if match else None


def _date(node: ET.Element) -> date | None:
    references = _descendants(node, "publication-reference")
    for reference in references:
        for doc_id in _descendants(reference, "document-id"):
            raw = _first_text(doc_id, "date")
            if raw and re.fullmatch(r"\d{8}", raw):
                try:
                    return date.fromisoformat(f"{raw[:4]}-{raw[4:6]}-{raw[6:]}")
                except ValueError:
                    pass
    return None


def _field(value: str | None) -> FieldStatus:
    return FieldStatus.AVAILABLE if value else FieldStatus.MISSING


def _document(node: ET.Element) -> PatentDocument | None:
    parts = _publication_parts(node)
    if parts is None:
        return None
    country, number, kind = parts
    external_id = f"{country}.{number}.{kind}"
    title = _language_text(_descendants(node, "invention-title"))
    abstract = _language_text(_descendants(node, "abstract"))
    published = _date(node)
    return PatentDocument(
        source="epo_ops",
        external_id=external_id,
        country=country,
        publication_number=number,
        kind=kind,
        source_url=f"https://worldwide.espacenet.com/patent/search?q=pn%3D{country}{number}{kind}",
        title=title,
        abstract=abstract,
        publication_date=published,
        field_status={
            "title": _field(title),
            "abstract": _field(abstract),
            "publication_date": FieldStatus.AVAILABLE if published else FieldStatus.MISSING,
            "claims": FieldStatus.NOT_REQUESTED,
            "description": FieldStatus.NOT_REQUESTED,
        },
    )


def parse_documents(content: bytes) -> tuple[PatentDocument, ...]:
    """Нормализовать exchange-document, сохранив точный код публикации и пропуски полей."""
    root = _parse_xml(content)
    found: dict[str, PatentDocument] = {}
    for node in _descendants(root, "exchange-document"):
        document = _document(node)
        if document is not None:
            found[document.external_id] = document
    return tuple(found.values())


def _parse_fulltext(content: bytes, part: str) -> str | None:
    root = _parse_xml(content)
    nodes = _descendants(root, part)
    if not nodes:
        return None
    paragraphs: list[str] = []
    for node in nodes:
        parts = _descendants(node, "claim") if part == "claims" else _descendants(node, "p")
        if not parts:
            parts = [node]
        paragraphs.extend(value for item in parts if (value := _text(item)))
    return "\n".join(paragraphs) or None


class EpoOpsClient:
    """Клиент с явной деградацией, ограничением запросов и обновлением OAuth token."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        consumer_key: str | None,
        consumer_secret: str | None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1 or max_attempts > 5:
            raise ValueError("max_attempts must be between 1 and 5")
        self.client = client
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.sleep = sleep
        self.clock = clock
        self.max_attempts = max_attempts
        self._token: str | None = None
        self._token_until = 0.0
        self._blocked_until = 0.0
        self._next_request: dict[str, float] = {}
        self._limits: dict[str, int] = {}
        self._token_lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()

    @classmethod
    def from_environment(cls, client: httpx.AsyncClient) -> "EpoOpsClient":
        """Прочитать учётные данные из окружения без вывода их в логи."""
        return cls(
            client,
            consumer_key=os.getenv("EPO_CONSUMER_KEY"),
            consumer_secret=os.getenv("EPO_CONSUMER_SECRET"),
        )

    @property
    def configured(self) -> bool:
        return bool(self.consumer_key and self.consumer_secret)

    @property
    def quota_used(self) -> dict[str, int]:
        return self._limits.copy()

    async def _token_value(self, *, refresh: bool = False) -> str | _Failure:
        async with self._token_lock:
            if refresh:
                self._token = None
            if self._token and self.clock() < self._token_until:
                return self._token
            try:
                response = await self.client.post(
                    f"{OPS_BASE}/auth/accesstoken",
                    data={"grant_type": "client_credentials"},
                    auth=(self.consumer_key or "", self.consumer_secret or ""),
                    headers={"Accept": "application/json"},
                    follow_redirects=False,
                )
            except httpx.RequestError:
                return _Failure("auth_network_error")
            if response.status_code != 200:
                return _Failure("auth_rejected")
            try:
                data: dict[str, Any] = response.json()
                token = data["access_token"]
                expires_in = float(data["expires_in"])
                if not isinstance(token, str) or not token or expires_in <= 0:
                    raise ValueError("invalid token")
            except (ValueError, KeyError, TypeError):
                return _Failure("auth_invalid_response")
            self._token = token
            self._token_until = self.clock() + max(1.0, expires_in - 30.0)
            return token

    def _record_limits(self, response: httpx.Response, service: str) -> None:
        baseline_delay = 6.0 if service == "search" else 0.5
        self._next_request[service] = max(
            self._next_request.get(service, 0), self.clock() + baseline_delay
        )
        for name in (
            "X-IndividualQuotaPerHour-Used",
            "X-RegisteredQuotaPerWeek-Used",
            "X-RegisteredPayingQuotaPerWeek-Used",
        ):
            raw = response.headers.get(name)
            if raw and raw.isdigit():
                self._limits[name] = int(raw)
        control = response.headers.get("X-Throttling-Control", "")
        for matched_service, color, limit in _THROTTLE.findall(control):
            if matched_service != service:
                continue
            if color == "black" or int(limit) == 0:
                delay = self._retry_after(response) or 60.0
            else:
                delay = 60.0 / int(limit)
                if color == "red":
                    delay = max(delay, 6.0)
            self._next_request[service] = max(
                self._next_request.get(service, 0), self.clock() + delay
            )

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        raw = response.headers.get("Retry-After")
        if not raw:
            return None
        try:
            value = float(raw)
        except ValueError:
            return None
        if value < 0:
            return None
        return value / 1000 if value > 1000 else value

    async def _request(
        self,
        path: str,
        *,
        service: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response | _Failure:
        async with self._request_lock:
            return await self._request_locked(
                path, service=service, params=params, headers=headers
            )

    async def _request_locked(
        self,
        path: str,
        *,
        service: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response | _Failure:
        if self.clock() < self._blocked_until:
            return _Failure("quota_exhausted", self._blocked_until - self.clock())
        refreshed = False
        for attempt in range(self.max_attempts):
            delay = self._next_request.get(service, 0) - self.clock()
            if delay > 0:
                await self.sleep(delay)
            token = await self._token_value(refresh=refreshed)
            refreshed = False
            if isinstance(token, _Failure):
                return token
            try:
                accept = (
                    "application/fulltext+xml"
                    if path.endswith(("/fulltext", "/claims", "/description"))
                    else "application/exchange+xml"
                )
                response = await self.client.get(
                    f"{OPS_BASE}/rest-services/{path}",
                    params=params,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": accept,
                        **(headers or {}),
                    },
                    follow_redirects=False,
                )
            except httpx.RequestError:
                if attempt + 1 == self.max_attempts:
                    return _Failure("network_error")
                await self.sleep(min(2**attempt, 8))
                continue
            self._record_limits(response, service)
            if response.status_code == 401 and not refreshed:
                self._token = None
                refreshed = True
                if attempt + 1 < self.max_attempts:
                    continue
            reason = response.headers.get("X-Rejection-Reason")
            if response.status_code == 403:
                if reason:
                    wait = self._retry_after(response) or (
                        604800.0 if "week" in reason.lower() else 3600.0
                    )
                    self._blocked_until = self.clock() + wait
                    return _Failure("quota_exhausted", wait)
                return _Failure("forbidden")
            if response.status_code == 429 or response.status_code in (500, 502, 503, 504):
                wait = min(60.0, max(2**attempt, self._retry_after(response) or 0.0))
                self._next_request[service] = max(
                    self._next_request.get(service, 0), self.clock() + wait
                )
                if attempt + 1 == self.max_attempts:
                    return _Failure(
                        "rate_limited" if response.status_code == 429 else "server_error", wait
                    )
                continue
            if response.status_code in (200, 404):
                return response
            return _Failure("http_error")
        return _Failure("auth_rejected")

    async def search(
        self,
        query: str,
        *,
        limit: int = 25,
        offset: int = 0,
        filters: str | None = None,
    ) -> PatentResult:
        if not self.configured:
            return PatentResult(SourceStatus.NOT_CONFIGURED)
        if not query.strip() or limit < 1 or limit > 100 or offset < 0 or offset >= 2000:
            raise ValueError("query, limit (1-100), or offset (0-1999) is invalid")
        escaped = query.strip().replace("\\", "\\\\").replace('"', '\\"')
        expression = f'txt="{escaped}"'
        if filters:
            if not filters.strip() or len(filters) > 2000:
                raise ValueError("filter must contain 1-2000 characters")
            expression = f"({expression}) AND ({filters.strip()})"
        start = offset + 1
        end_requested = min(2000, offset + limit)
        response = await self._request(
            "published-data/search/abstract,biblio",
            service="search",
            params={"q": expression},
            headers={"X-OPS-Range": f"{start}-{end_requested}"},
        )
        if isinstance(response, _Failure):
            return PatentResult(
                SourceStatus.UNAVAILABLE,
                error_code=response.code,
                retry_after_seconds=response.retry_after_seconds,
            )
        if response.status_code == 404:
            return PatentResult(SourceStatus.EMPTY)
        try:
            documents = parse_documents(response.content)[:limit]
            root = _parse_xml(response.content)
            search_nodes = _descendants(root, "biblio-search")
            if not search_nodes:
                raise ValueError("missing search response")
            count_raw = search_nodes[0].get("total-result-count")
            count = int(count_raw) if count_raw and count_raw.isdigit() else None
            ranges = _descendants(search_nodes[0], "range")
            end_raw = ranges[0].get("end") if ranges else None
            end = int(end_raw) if end_raw and end_raw.isdigit() else offset + len(documents)
            if not documents and count != 0:
                raise ValueError("missing publications")
        except ValueError:
            return PatentResult(SourceStatus.UNAVAILABLE, error_code="invalid_xml")
        next_offset = (
            end if documents and count is not None and end < count and end < 2000 else None
        )
        return PatentResult(
            SourceStatus.OK if documents else SourceStatus.EMPTY,
            documents,
            next_offset=next_offset,
            total_count=count,
        )

    async def fetch(self, external_id: str, *, include_fulltext: bool = False) -> PatentResult:
        if not self.configured:
            return PatentResult(SourceStatus.NOT_CONFIGURED)
        matched = _DOCDB.fullmatch(external_id.upper())
        if matched is None:
            raise ValueError("external_id must be a DOCDB publication identifier")
        canonical = ".".join(matched.groups())
        path = f"published-data/publication/docdb/{quote(canonical, safe='.')}/"
        biblio = await self._request(path + "biblio", service="retrieval")
        if isinstance(biblio, _Failure):
            return PatentResult(
                SourceStatus.UNAVAILABLE,
                error_code=biblio.code,
                retry_after_seconds=biblio.retry_after_seconds,
            )
        if biblio.status_code == 404:
            return PatentResult(SourceStatus.EMPTY)
        try:
            documents = parse_documents(biblio.content)
            document = next((item for item in documents if item.external_id == canonical), None)
            if document is None:
                raise ValueError("publication not found in response")
        except ValueError:
            return PatentResult(SourceStatus.UNAVAILABLE, error_code="invalid_xml")
        abstract = await self._request(path + "abstract", service="retrieval")
        if isinstance(abstract, _Failure):
            return PatentResult(
                SourceStatus.UNAVAILABLE,
                error_code=abstract.code,
                retry_after_seconds=abstract.retry_after_seconds,
            )
        if abstract.status_code == 200:
            try:
                candidates = parse_documents(abstract.content)
                supplement = next(
                    (item for item in candidates if item.external_id == canonical), None
                )
                abstract_text = supplement.abstract if supplement else None
            except ValueError:
                return PatentResult(SourceStatus.UNAVAILABLE, error_code="invalid_xml")
            if abstract_text:
                document = replace(document, abstract=abstract_text)
        fields = document.field_status.copy()
        fields["abstract"] = _field(document.abstract)
        if include_fulltext:
            inquiry = await self._request(path + "fulltext", service="retrieval")
            if isinstance(inquiry, _Failure):
                return PatentResult(
                    SourceStatus.UNAVAILABLE,
                    error_code=inquiry.code,
                    retry_after_seconds=inquiry.retry_after_seconds,
                )
            available: set[str] = set()
            if inquiry.status_code == 200:
                try:
                    root = _parse_xml(inquiry.content)
                    available = {
                        node.get("desc", "") for node in _descendants(root, "fulltext-instance")
                    }
                except ValueError:
                    return PatentResult(SourceStatus.UNAVAILABLE, error_code="invalid_xml")
            for part in ("claims", "description"):
                fields[part] = FieldStatus.MISSING
                if part not in available:
                    continue
                response = await self._request(path + part, service="retrieval")
                if isinstance(response, _Failure):
                    return PatentResult(
                        SourceStatus.UNAVAILABLE,
                        error_code=response.code,
                        retry_after_seconds=response.retry_after_seconds,
                    )
                if response.status_code == 404:
                    continue
                try:
                    value = _parse_fulltext(response.content, part)
                except ValueError:
                    return PatentResult(SourceStatus.UNAVAILABLE, error_code="invalid_xml")
                fields[part] = _field(value)
                if part == "claims":
                    document = replace(document, claims=value)
                else:
                    document = replace(document, description=value)
        return PatentResult(SourceStatus.OK, (replace(document, field_status=fields),))
