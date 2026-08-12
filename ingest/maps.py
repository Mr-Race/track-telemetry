"""Azure Maps proxy: satellite static image for a track, framed from its
corners' apex coordinates. Kept server-side (rather than calling Azure
Maps from the browser) so the Maps account is accessed only via the
Function App's managed identity - no key ever reaches the client.
"""

import math
import urllib.parse
import urllib.request

from azure.identity import DefaultAzureCredential

MAPS_SCOPE = "https://atlas.microsoft.com/.default"

# How much to pad the corner bounding box before framing, and the
# quantization safety margin baked into compute_zoom (see its docstring).
PADDING_FACTOR = 2.0


def track_bbox(cnx, track_id):
    """(min_lat, max_lat, min_lon, max_lon) from a track's corner apexes."""
    cur = cnx.cursor()
    cur.execute("""
        SELECT MIN(CAST(apex_lat AS FLOAT)), MAX(CAST(apex_lat AS FLOAT)),
               MIN(CAST(apex_lon AS FLOAT)), MAX(CAST(apex_lon AS FLOAT))
        FROM dbo.corners WHERE track_id = ?""", track_id)
    row = cur.fetchone()
    if row is None or row[0] is None:
        raise ValueError(f"No corner coordinates for track_id={track_id}")
    return row[0], row[1], row[2], row[3]


def compute_zoom(min_lat, max_lat, min_lon, max_lon, width, height,
                  padding=PADDING_FACTOR, max_zoom=17):
    """Highest integer zoom level at which the padded bbox still fits
    within width x height, using the standard Web Mercator meters-per-
    pixel formula. `padding` >= ~2.0 also absorbs the fact that zoom is
    quantized to an integer (floor), so the true margin is never razor
    thin - validated empirically against NJMP Lightning and Thunderbolt.
    """
    lat_center = (min_lat + max_lat) / 2
    lon_range = (max_lon - min_lon) * padding
    lat_range = (max_lat - min_lat) * padding
    lat_rad = math.radians(lat_center)

    meters_per_deg_lon = 111320 * math.cos(lat_rad)
    meters_per_deg_lat = 110540

    mpp_lon = (lon_range * meters_per_deg_lon) / width
    mpp_lat = (lat_range * meters_per_deg_lat) / height

    base = 156543.03392 * math.cos(lat_rad)
    zoom_lon = math.log2(base / mpp_lon)
    zoom_lat = math.log2(base / mpp_lat)
    return min(max_zoom, math.floor(min(zoom_lon, zoom_lat)))


def _maps_token():
    # Reuses the process-wide credential from cloud.py: a fresh
    # DefaultAzureCredential per call discards its own token cache and
    # re-fetches every time (issue #16).
    from ingest.cloud import _get_credential

    return _get_credential().get_token(MAPS_SCOPE).token


def fetch_satellite_image(client_id, min_lat, max_lat, min_lon, max_lon,
                           width=600, height=400):
    """PNG bytes from Azure Maps' Get Map Static Image API, centered and
    zoomed to fit the given bounding box."""
    zoom = compute_zoom(min_lat, max_lat, min_lon, max_lon, width, height)
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2

    params = {
        "api-version": "2024-04-01",
        "tilesetId": "microsoft.imagery",
        "zoom": zoom,
        "center": f"{center_lon},{center_lat}",
        "width": width,
        "height": height,
    }
    url = "https://atlas.microsoft.com/map/static?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {_maps_token()}",
        "x-ms-client-id": client_id,
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()
