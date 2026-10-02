"""Export only filenames, hashes, timestamp ranges; never provider/log bodies."""

import csv
import hashlib
import json
import os
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent
base = Path(os.environ["LOCALAPPDATA"]) / "Ollama"
pattern = re.compile(
    r'time="?(\d{4}-\d\d-\d\dT[^\s"]+)|\[GIN\]\s+(\d{4}/\d\d/\d\d - \d\d:\d\d:\d\d)'
)
rows = []
for path in sorted(base.glob("server*.log")):
    content = path.read_bytes()
    timestamps = sorted(
        {
            m.group(1) or m.group(2)
            for m in pattern.finditer(content.decode("utf-8", errors="replace"))
        }
    )
    rows.append(
        {
            "file": path.name,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "first_timestamp": timestamps[0] if timestamps else None,
            "last_timestamp": timestamps[-1] if timestamps else None,
        }
    )
(OUT / "log_inventory.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
print(json.dumps(rows, indent=2))

# Ollama may flush its active server log later. Inspect it again for allowlisted
# runtime metadata, never print entire lines (server config contains environment).
content = (base / "server.log").read_text(encoding="utf-8", errors="replace")
chat = []
for line in content.splitlines():
    match = re.search(
        r"\[GIN\]\s+(\d{4}/\d\d/\d\d - \d\d:\d\d:\d\d)"
        r'\s*\|\s*(\d+)\s*\|\s*([^|]+)\|.*POST\s+"/api/chat"',
        line,
    )
    if match and "2026/10/02 - 18:25:10" <= match[1] <= "2026/10/02 - 22:01:40":
        chat.append(
            {
                "local_timestamp": match[1],
                "http_status": int(match[2]),
                "duration_reported": match[3].strip(),
                "endpoint": "/api/chat",
                "document_id": "",
                "run_id": "",
                "attribution": "TIME_WINDOW_ONLY_NO_REQUEST_ID",
            }
        )
with (OUT / "inference_http_window.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(
        stream,
        fieldnames=[
            "local_timestamp",
            "http_status",
            "duration_reported",
            "endpoint",
            "document_id",
            "run_id",
            "attribution",
        ],
    )
    writer.writeheader()
    writer.writerows(chat)
metadata = {
    "window_local": ["2026-10-02 18:25:10 Europe/Moscow", "2026-10-02 22:01:40 Europe/Moscow"],
    "http_chat_completions_in_window": len(chat),
    "http_status_counts": {
        str(code): sum(r["http_status"] == code for r in chat)
        for code in sorted({r["http_status"] for r in chat})
    },
    "server_context_env_values": sorted(set(re.findall(r"OLLAMA_CONTEXT_LENGTH:(\d+)", content))),
    "server_parallel_env_values": sorted(set(re.findall(r"OLLAMA_NUM_PARALLEL:(\d+)", content))),
    "runner_context_values": sorted(
        set(re.findall(r"(?:n_ctx\s*=\s*|--ctx-size\s+|context_length[=: ]+)(\d+)", content))
    ),
    "input_truncation_warning_count_whole_log": content.count("truncating input prompt"),
    "done_reason_length_literal_count_whole_log": len(
        re.findall(r'done_reason[=: ]+["\x27]?length', content)
    ),
    "document_or_run_id_retained": False,
    "warning": (
        "HTTP 200 is not proof of valid JSON or terminal done_reason=stop. "
        "Context values cover the entire active server log; "
        "request association is not available."
    ),
}
(OUT / "runtime_log_metadata.json").write_text(
    json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(metadata, indent=2))
