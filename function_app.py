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

from ingest import maps, queries
from ingest.api_auth import require_auth
from ingest.cloud import get_cloud_connection, upload_raw_blob
from ingest.racechrono_parser import (
    compute_corner_metrics, compute_laps, fetch_corners, fmt_ms, load,
    parse_csv,
)

app = func.FunctionApp()

RAW_CONTAINER = "racechrono-raw"


def _connect():
    return get_cloud_connection(os.environ["SQL_SERVER"],
                                 os.environ["SQL_DATABASE"])


def _json_response(payload, status_code):
    return func.HttpResponse(
        json.dumps(payload), status_code=status_code,
        mimetype="application/json")


# Read endpoints for the React dashboard (Block 4). auth_level stays
# ANONYMOUS (that's Azure's function-key mechanism, unrelated) -
# @require_auth validates a real MSAL-issued bearer token instead.
@app.route(route="sessions", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def list_sessions(req: func.HttpRequest) -> func.HttpResponse:
    event_id = req.params.get("event_id")
    try:
        event_id = int(event_id) if event_id is not None else None
    except ValueError:
        return _json_response({"error": "event_id must be an integer"}, 400)

    try:
        return _json_response(queries.list_sessions(_connect(), event_id),
                               200)
    except Exception as exc:
        logging.exception("list_sessions failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="sessions/{session_id:int}", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def get_session_detail(req: func.HttpRequest) -> func.HttpResponse:
    session_id = int(req.route_params["session_id"])
    try:
        return _json_response(
            queries.get_session_detail(_connect(), session_id), 200)
    except ValueError as exc:
        return _json_response({"error": str(exc)}, 404)
    except Exception as exc:
        logging.exception("get_session_detail failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="sessions/{session_id:int}", methods=["PATCH"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def update_session(req: func.HttpRequest) -> func.HttpResponse:
    session_id = int(req.route_params["session_id"])
    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"error": "request body must be JSON"}, 400)

    if "car_id" not in body:
        return _json_response({"error": "car_id is required"}, 400)
    car_id = body["car_id"]
    if car_id is not None:
        try:
            car_id = int(car_id)
        except (TypeError, ValueError):
            return _json_response({"error": "car_id must be an integer or null"}, 400)

    try:
        queries.set_session_car(_connect(), session_id, car_id)
        return _json_response({"session_id": session_id, "car_id": car_id}, 200)
    except ValueError as exc:
        return _json_response({"error": str(exc)}, 404)
    except Exception as exc:
        logging.exception("update_session failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="sessions/{session_id:int}/summary", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def get_session_summary(req: func.HttpRequest) -> func.HttpResponse:
    session_id = int(req.route_params["session_id"])
    try:
        return _json_response(
            queries.session_summary(_connect(), session_id), 200)
    except ValueError as exc:
        return _json_response({"error": str(exc)}, 404)
    except Exception as exc:
        logging.exception("get_session_summary failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="tracks", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def list_tracks(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return _json_response(queries.list_tracks(_connect()), 200)
    except Exception as exc:
        logging.exception("list_tracks failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="tracks/{track_id:int}/satellite", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def get_track_satellite(req: func.HttpRequest) -> func.HttpResponse:
    track_id = int(req.route_params["track_id"])
    try:
        bbox = maps.track_bbox(_connect(), track_id)
        png = maps.fetch_satellite_image(os.environ["MAPS_CLIENT_ID"], *bbox)
        return func.HttpResponse(
            png, status_code=200, mimetype="image/png",
            headers={"Cache-Control": "public, max-age=86400"})
    except ValueError as exc:
        return _json_response({"error": str(exc)}, 404)
    except Exception as exc:
        logging.exception("get_track_satellite failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="tracks/{track_id:int}/benchmarks", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def get_track_benchmarks(req: func.HttpRequest) -> func.HttpResponse:
    track_id = int(req.route_params["track_id"])
    try:
        return _json_response(
            queries.get_track_benchmarks(_connect(), track_id), 200)
    except ValueError as exc:
        return _json_response({"error": str(exc)}, 404)
    except Exception as exc:
        logging.exception("get_track_benchmarks failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="consumables", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def get_consumables(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return _json_response(queries.get_consumables(_connect()), 200)
    except Exception as exc:
        logging.exception("get_consumables failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="consumables/{consumable_id:int}/replace", methods=["POST"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def replace_consumable(req: func.HttpRequest) -> func.HttpResponse:
    consumable_id = int(req.route_params["consumable_id"])
    try:
        body = req.get_json()
    except ValueError:
        body = {}

    install_date = body.get("install_date") or None
    notes = body.get("notes") or None
    install_session_id = body.get("install_session_id") or None
    if install_session_id is not None:
        try:
            install_session_id = int(install_session_id)
        except (TypeError, ValueError):
            return _json_response(
                {"error": "install_session_id must be an integer"}, 400)

    try:
        new_id = queries.replace_consumable(
            _connect(), consumable_id, install_date, install_session_id,
            notes)
        return _json_response({"consumable_id": new_id}, 201)
    except ValueError as exc:
        return _json_response({"error": str(exc)}, 404)
    except Exception as exc:
        logging.exception("replace_consumable failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="organizations", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def list_organizations(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return _json_response(queries.list_organizations(_connect()), 200)
    except Exception as exc:
        logging.exception("list_organizations failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="events", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def list_events(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return _json_response(queries.list_events(_connect()), 200)
    except Exception as exc:
        logging.exception("list_events failed")
        return _json_response({"error": str(exc)}, 500)


# First write-capable dashboard endpoint (Block 6) - protected the same
# way as the read routes, @require_auth validating a real bearer token.
@app.route(route="events", methods=["POST"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def create_event(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"error": "request body must be JSON"}, 400)

    try:
        track_id = int(body["track_id"])
        organization_id = int(body["organization_id"])
        event_name = str(body["event_name"]).strip()
        start_date = str(body["start_date"])
        end_date = body.get("end_date") or None
        end_date = str(end_date) if end_date else None
    except (KeyError, TypeError, ValueError):
        return _json_response(
            {"error": "track_id, organization_id, event_name, and "
                      "start_date are required"}, 400)

    if not event_name:
        return _json_response({"error": "event_name cannot be empty"}, 400)

    try:
        event_id = queries.create_event(
            _connect(), track_id, organization_id, event_name,
            start_date, end_date)
        return _json_response({"event_id": event_id}, 201)
    except Exception as exc:
        logging.exception("create_event failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="cars", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def list_cars(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return _json_response(queries.list_cars(_connect()), 200)
    except Exception as exc:
        logging.exception("list_cars failed")
        return _json_response({"error": str(exc)}, 500)


@app.route(route="cars", methods=["POST"],
           auth_level=func.AuthLevel.ANONYMOUS)
@require_auth
def create_car(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"error": "request body must be JSON"}, 400)

    try:
        display_name = str(body["display_name"]).strip()
    except (KeyError, TypeError):
        return _json_response({"error": "display_name is required"}, 400)
    if not display_name:
        return _json_response({"error": "display_name cannot be empty"}, 400)

    make = body.get("make") or None
    model = body.get("model") or None
    notes = body.get("notes") or None
    year = body.get("year") or None
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            return _json_response({"error": "year must be an integer"}, 400)

    try:
        car_id = queries.create_car(
            _connect(), display_name, make, model, year, notes)
        return _json_response({"car_id": car_id}, 201)
    except Exception as exc:
        logging.exception("create_car failed")
        return _json_response({"error": str(exc)}, 500)


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

    car_id = req.params.get("car_id")
    if car_id is not None:
        try:
            car_id = int(car_id)
        except ValueError:
            return _json_response(
                {"error": "car_id query param must be an integer"}, 400)

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

        cnx = _connect()
        corners = fetch_corners(cnx, event_id)
        metrics = compute_corner_metrics(samples, corners) if corners else []

        summary = {
            "track": meta.get("Track name"),
            "samples": len(samples),
            "blob_name": blob_name,
            "dry_run": dry_run,
            "car_id": car_id,
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
                           meta, samples, laps, metrics, car_id=car_id)
        summary["loaded"] = True
        summary["session_id"] = session_id
        summary["corner_metric_count"] = len(metrics)
        return _json_response(summary, 200)

    except ValueError as exc:
        return _json_response({"error": str(exc)}, 400)
    except Exception as exc:
        logging.exception("ingest failed")
        return _json_response({"error": str(exc)}, 500)
