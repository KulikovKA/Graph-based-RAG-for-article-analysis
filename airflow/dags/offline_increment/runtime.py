"""Намеренно отключённая точка сборки до интеграционной проверки I-AIR."""

from .pipeline import Ports


def configured_ports() -> Ports:
    raise RuntimeError("offline_ports_not_configured")
