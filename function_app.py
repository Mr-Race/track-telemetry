"""HTTP ingest endpoint: POST /api/ingest?event_id=&session_number=[&dry_run=1]

Archives the raw RaceChrono CSV to Blob, then parses and loads it into
Azure SQL using the same stdlib-only logic as the local CLI
(ingest/racechrono_parser.py). See sql/04_events.sql for pre-seeded
event_ids and docs/BACKLOG.md for the target architecture.
"""

import json
import logging
import os
import tempfile
import time
import uuid

import azure.functions as func

from ingest.cloud import get_cloud_connection, upload_raw_blob
from ingest.racechrono_parser import (
    compute_corner_metrics, compute_laps, fetch_corners, fmt_ms, load,
    parse_csv,
)

app = func.FunctionApp()

RAW_CONTAINER = "racechrono-raw"


def _json_response(payload, status_code):
    return func.HttpResponse(
        json.dumps(payload), status_code=status_code,
        mimetype="application/json")


@app.route(route="ingest", methods=["POST"],
           auth_level=func.AuthLevel.FUNCTION)
def ingest(req: func.HttpRequest) -> func.HttpResponse:
    try:
        event_id = int(req.params["event_id"])
        session_number = int(req.params["session_number"])
    except (KeyError, ValueError):
        return _json_response(
            {"error": "event_id and session_number query params "
                      "are required integers"}, 400)

    body = req.get_body()
    if not body:
        return _json_response({"error": "empty request body"}, 400)

    dry_run = req.params.get("dry_run") == "1"
    filename = req.params.get("filename") or f"session_{int(time.time())}.csv"
    blob_name = (f"{event_id}/{session_number}_{int(time.time())}"
                 f"_{uuid.uuid4().hex[:8]}_{filename}")

    try:
        upload_raw_blob(os.environ["STORAGE_ACCOUNT_URL"], RAW_CONTAINER,
                         blob_name, body)

        with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
            tmp.write(body)
            tmp.flush()
            meta, samples = parse_csv(tmp.name)

        laps = compute_laps(samples)

        cnx = get_cloud_connection(os.environ["SQL_SERVER"],
                                    os.environ["SQL_DATABASE"])
        corners = fetch_corners(cnx, event_id)
        metrics = compute_corner_metrics(samples, corners) if corners else []

        summary = {
            "track": meta.get("Track name"),
            "samples": len(samples),
            "blob_name": blob_name,
            "dry_run": dry_run,
            "laps": [
                {
                    "lap_number": lap["lap_number"],
                    "lap_time_ms": lap["lap_time_ms"],
                    "lap_time": fmt_ms(lap["lap_time_ms"]),
                    "is_out_lap": bool(lap["is_out_lap"]),
                    "is_in_lap": bool(lap["is_in_lap"]),
                    "is_valid": bool(lap["is_valid"]),
                }
                for lap in laps
            ],
            "corner_coverage": sorted({m["corner_code"] for m in metrics},
                                       key=lambda c: (len(c), c)),
        }

        if dry_run:
            summary["loaded"] = False
            return _json_response(summary, 200)

        session_id = load(cnx, event_id, session_number, filename,
                           meta, samples, laps, metrics)
        summary["loaded"] = True
        summary["session_id"] = session_id
        summary["corner_metric_count"] = len(metrics)
        return _json_response(summary, 200)

    except ValueError as exc:
        return _json_response({"error": str(exc)}, 400)
    except Exception as exc:
        logging.exception("ingest failed")
        return _json_response({"error": str(exc)}, 500)
