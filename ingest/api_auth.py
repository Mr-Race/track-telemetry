"""Bearer-token validation for the dashboard's read endpoints.

Verifies MSAL-issued access tokens against the Entra External ID
(CIAM) tenant configured for the dashboard SPA (see
dashboard/src/authConfig.ts). Signature verification and JWKS
fetch/cache/rotation are delegated to PyJWT's PyJWKClient rather than
hand-rolled here - getting that wrong is a real security risk.
"""

import functools
import json
import os

import azure.functions as func
import jwt

TENANT_ID = os.environ["MSAL_TENANT_ID"]
CLIENT_ID = os.environ["MSAL_CLIENT_ID"]

ISSUER = f"https://{TENANT_ID}.ciamlogin.com/{TENANT_ID}/v2.0"
JWKS_URI = (f"https://{TENANT_ID}.ciamlogin.com/{TENANT_ID}"
            "/discovery/v2.0/keys")

_jwks_client = jwt.PyJWKClient(JWKS_URI)


class AuthError(Exception):
    pass


REQUIRED_SCOPE = "access_as_user"


def validate_bearer_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthError("missing bearer token")

    token = auth_header[len("Bearer "):]
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, signing_key, algorithms=["RS256"],
            audience=CLIENT_ID, issuer=ISSUER)
    except jwt.PyJWTError as exc:
        raise AuthError(f"invalid token: {exc}") from exc

    # aud/iss/signature only prove "a token this API's JWKS can verify" -
    # without this, any token scoped to this app registration for any
    # reason would pass, not just ones that actually consented to
    # access_as_user. Delegated scopes land in "scp" as a space-separated
    # string (not a list, per the v2.0 token spec).
    if REQUIRED_SCOPE not in claims.get("scp", "").split():
        raise AuthError(f"token missing required scope: {REQUIRED_SCOPE}")

    return claims


def require_auth(fn):
    @functools.wraps(fn)
    def wrapper(req):
        try:
            validate_bearer_token(req.headers.get("Authorization"))
        except AuthError as exc:
            return func.HttpResponse(
                json.dumps({"error": str(exc)}), status_code=401,
                mimetype="application/json")
        return fn(req)

    return wrapper
