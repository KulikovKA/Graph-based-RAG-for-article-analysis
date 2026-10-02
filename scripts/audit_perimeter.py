"""Аудит опубликованных Docker-портов без чтения env и секретов контейнеров."""

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def violations(containers: list[dict[str, Any]]) -> list[dict[str, str]]:
    findings = []
    for container in containers:
        labels = container.get("labels") or {}
        project = labels.get("com.docker.compose.project") == "article-analysis"
        proxy = project and labels.get("com.docker.compose.service") in {"caddy-dev", "caddy-prod"}
        if container.get("network_mode") == "host":
            findings.append({"container": container["name"], "reason": "host_network"})
        for port, bindings in (container.get("ports") or {}).items():
            for binding in bindings or []:
                host = binding.get("HostIp", "")
                if (project and (not proxy or port not in {"80/tcp", "443/tcp"})) or (
                    not project and host not in {"127.0.0.1", "::1"}
                ):
                    findings.append(
                        {
                            "container": container["name"],
                            "port": port,
                            "host_ip": host,
                            "host_port": binding["HostPort"],
                            "reason": "project_non_caddy_port" if project else "host_public_port",
                        }
                    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    ids = subprocess.check_output(["docker", "ps", "-q"], text=True).split()
    containers = []
    template = (
        '{"name":{{json .Name}},"labels":{{json .Config.Labels}},'
        '"ports":{{json .NetworkSettings.Ports}},"network_mode":{{json .HostConfig.NetworkMode}}}'
    )
    for identifier in ids:
        containers.append(
            json.loads(
                subprocess.check_output(
                    ["docker", "inspect", "--format", template, identifier], text=True
                )
            )
        )
    findings = violations(containers)
    report = {"scope": "running_docker_containers", "passed": not findings, "findings": findings}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
