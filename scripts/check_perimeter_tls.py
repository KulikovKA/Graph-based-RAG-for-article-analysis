"""Проверить TLS и HTTPS proxy без отключения проверки сертификата."""

import argparse
import json
import socket
import ssl
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def check(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("https_origin")
    parser.add_argument("--http-origin", required=True)
    parser.add_argument("--cafile", type=Path, help="Только для локального smoke с тестовым CA")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    parsed = urlsplit(args.https_origin)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path not in {"", "/"}:
        parser.error("Требуется HTTPS origin")
    protocols = []
    for version in (ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3):
        context = ssl.create_default_context(cafile=str(args.cafile) if args.cafile else None)
        context.minimum_version = context.maximum_version = version
        with socket.create_connection((parsed.hostname, parsed.port or 443), timeout=10) as raw:
            with context.wrap_socket(raw, server_hostname=parsed.hostname) as connection:
                protocols.append(connection.version())
    context = ssl.create_default_context(cafile=str(args.cafile) if args.cafile else None)
    with httpx.Client(verify=context, trust_env=False, timeout=10) as client:
        response = client.get(args.https_origin.rstrip("/") + "/health/live")
        response.raise_for_status()
        check(response.json() == {"status": "live"}, "INVALID_HEALTH")
        check(
            response.headers.get("strict-transport-security") == "max-age=31536000", "INVALID_HSTS"
        )
        check(
            response.headers.get("x-content-type-options") == "nosniff",
            "INVALID_CONTENT_TYPE_POLICY",
        )
        check(response.headers.get("x-frame-options") == "DENY", "INVALID_FRAME_POLICY")
        redirect = client.get(args.http_origin.rstrip("/") + "/health/live")
        check(redirect.status_code in {301, 308}, "INVALID_HTTP_REDIRECT")
        destination = urlsplit(redirect.headers["location"])
        check(
            destination.scheme == "https" and destination.hostname == parsed.hostname,
            "INVALID_REDIRECT_TARGET",
        )
    report = {
        "passed": True,
        "protocols": protocols,
        "verified_certificate": True,
        "public_trust_checked": args.cafile is None and parsed.hostname != "localhost",
        "https_health": response.status_code,
        "http_redirect": redirect.status_code,
        "hsts": response.headers["strict-transport-security"],
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
