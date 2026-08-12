"""Bearer-token verification for the MCP server (OAuth 2.1 Resource Server).

Validates access tokens issued by the same Entra External ID (CIAM)
tenant the dashboard uses, but against a SEPARATE app registration
(track-telemetry-mcp) - a distinct resource with its own client id and
`mcp.access` scope. The signature/issuer/scope logic mirrors the proven
ingest/api_auth.py::validate_bearer_token; the only real difference is
the shape: the MCP SDK's TokenVerifier is async and returns an
AccessToken (or None) rather than raising in an Azure Functions handler.

JWKS fetch/cache/rotation is delegated to PyJWT's PyJWKClient rather
than hand-rolled - getting that wrong is a real security risk.
"""

import logging
import os

import jwt
from mcp.server.auth.provider import AccessToken, TokenVerifier

log = logging.getLogger(__name__)

# Separate from the dashboard's MSAL_TENANT_ID/MSAL_CLIENT_ID even though
# the tenant value is identical: the client id differs (distinct app
# registration) and reusing the dashboard's env vars would be confusing.
TENANT_ID = os.environ["MCP_TENANT_ID"]
CLIENT_ID = os.environ["MCP_CLIENT_ID"]

ISSUER = f"https://{TENANT_ID}.ciamlogin.com/{TENANT_ID}/v2.0"
JWKS_URI = (f"https://{TENANT_ID}.ciamlogin.com/{TENANT_ID}"
            "/discovery/v2.0/keys")

REQUIRED_SCOPE = "mcp.access"

# The fully-qualified scope an OAuth client must REQUEST from Entra
# (api://<client-id>/mcp.access). This is what we advertise in the
# protected-resource metadata's scopes_supported, because Entra only
# recognises the qualified form in an authorize/token request - a bare
# "mcp.access" is rejected as an unknown scope, which silently breaks the
# client's token acquisition. Note the *issued* token's `scp` claim still
# carries only the short name "mcp.access" (REQUIRED_SCOPE), so that's
# what verify_token checks against below.
QUALIFIED_SCOPE = f"api://{CLIENT_ID}/{REQUIRED_SCOPE}"

# Entra issues a custom-API access token with `aud` set to either the
# app's client id (GUID) or its App ID URI (api://<client-id>), depending
# on the registration's requested-token-version. Accept both so this
# verifier does not silently break if that setting is ever changed.
_AUDIENCES = [CLIENT_ID, f"api://{CLIENT_ID}"]

_jwks_client = jwt.PyJWKClient(JWKS_URI)


class EntraTokenVerifier(TokenVerifier):
    """Verifies CIAM-issued bearer tokens for the MCP resource server."""

    async def verify_token(self, token: str) -> AccessToken | None:
        # Diagnostics here are deliberately narrow. They sit at DEBUG so
        # they are off in normal operation, they record the *type* of a
        # decode failure rather than its message (messages can quote
        # token content), and they never record `sub`, `scp` values or
        # any token-derived length. `aud`/`iss` are app-level identifiers
        # and are kept because the open Entra connector problem is an
        # audience mismatch and is undiagnosable without them.
        try:
            signing_key = _jwks_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token, signing_key, algorithms=["RS256"],
                audience=_AUDIENCES, issuer=ISSUER)
        except jwt.PyJWTError as exc:
            # Any failure (bad signature, wrong aud/iss, expired) -> the
            # SDK turns a None here into a 401 with a WWW-Authenticate
            # header pointing at the protected-resource metadata.
            #
            # WARNING, not DEBUG: this was demoted to DEBUG on
            # 2026-08-11 while removing the noisy per-request
            # instrumentation, which made it invisible in production -
            # and then a 401 with no token was indistinguishable from a
            # token that failed validation. Those need opposite fixes.
            # The exception *type* and `aud` are app-level facts, not
            # user data; claim values still stay out.
            log.warning("token rejected at decode: %s", type(exc).__name__)
            return None

        # aud/iss/signature only prove "a token this resource's JWKS can
        # verify". Delegated scopes land in "scp" as a space-separated
        # string (not a list, per the v2.0 token spec). Enforce the scope
        # here rather than relying solely on the SDK's required_scopes so
        # a mis-scoped token is rejected outright.
        scopes = claims.get("scp", "").split()
        if REQUIRED_SCOPE not in scopes:
            log.warning("token rejected: required scope %r absent (aud=%r)",
                        REQUIRED_SCOPE, claims.get("aud"))
            return None

        # Success stays at INFO and names only the audience - enough to
        # confirm which resource the token was issued for, which is the
        # open question with the connector.
        log.info("token accepted (aud=%r)", claims.get("aud"))

        # Return the qualified scope so the SDK's RequireAuthMiddleware,
        # whose required_scopes is set to QUALIFIED_SCOPE (to drive the
        # metadata), finds it in the token's scopes. The real gate is the
        # scp check above; this just keeps the middleware consistent.
        return AccessToken(
            token=token,
            client_id=claims.get("azp", CLIENT_ID),
            scopes=[QUALIFIED_SCOPE, *scopes],
            expires_at=claims.get("exp"),
            subject=claims.get("sub"),
            claims=claims,
        )
