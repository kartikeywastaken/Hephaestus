# -*- coding: utf-8 -*-
"""
Phase 10 — Packet writer.

Writes agent packets to agent_packets/<fn_name>.json
and produces agent_packet_manifest.json.
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path

from src.agent.models import SCHEMA_AGENT_PACKET_MANIFEST

logger = logging.getLogger("agent.packet_writer")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_filename(name: str) -> str:
    """Sanitize function name for use as a filename."""
    safe = "".join(c if (c.isalnum() or c in "_-.") else "_" for c in name)
    return safe[:128] or "unknown"


def write_packets(
    packets: list[dict],
    out_dir: Path,
    diagnostics: list[str] | None = None,
) -> Path:
    """
    Write all packets to agent_packets/ and produce agent_packet_manifest.json.

    Returns the path to agent_packet_manifest.json.
    Never raises — write failures are recorded as diagnostics.
    """
    out_dir = out_dir.resolve()
    packets_dir = out_dir / "agent_packets"
    packets_dir.mkdir(parents=True, exist_ok=True)

    write_diagnostics: list[str] = list(diagnostics or [])
    written: list[dict] = []
    skipped = 0

    for packet in packets:
        fn_name = packet.get("function", "unknown")
        filename = _safe_filename(fn_name) + ".json"
        path = packets_dir / filename

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(packet, f, indent=2, ensure_ascii=False)
            written.append({
                "function": fn_name,
                "filename": filename,
                "path": str(path),
            })
            logger.debug("[packet_writer] wrote %s", path)
        except Exception as e:
            msg = f"packet_writer: failed to write {filename}: {e}"
            logger.warning(msg)
            write_diagnostics.append(msg)
            skipped += 1

    manifest = {
        "schema_version": SCHEMA_AGENT_PACKET_MANIFEST,
        "phase": "10.1",
        "generated_at": _now_iso(),
        "packets_total": len(packets),
        "packets_written": len(written),
        "packets_skipped": skipped,
        "diagnostics": write_diagnostics,
        "packets": written,
    }

    manifest_path = out_dir / "agent_packet_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    logger.info(
        "[packet_writer] manifest written: %d packets, %d skipped",
        len(written), skipped,
    )
    return manifest_path
