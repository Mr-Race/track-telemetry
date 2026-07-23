import type { Configuration } from "@azure/msal-browser";

const clientId = import.meta.env.VITE_MSAL_CLIENT_ID;
const authority = import.meta.env.VITE_MSAL_AUTHORITY;
const tenantId = import.meta.env.VITE_MSAL_TENANT_ID;

if (!clientId || !authority || !tenantId) {
  throw new Error(
    "Missing VITE_MSAL_CLIENT_ID, VITE_MSAL_AUTHORITY, or VITE_MSAL_TENANT_ID env vars",
  );
}

export const msalConfig: Configuration = {
  auth: {
    clientId,
    authority,
    // This CIAM tenant's OIDC issuer uses the tenant-GUID subdomain
    // (<tenantId>.ciamlogin.com) rather than the friendly domain we
    // authenticate against, so both hosts must be trusted or MSAL's
    // issuer validation rejects the discovery response.
    knownAuthorities: [new URL(authority).hostname, `${tenantId}.ciamlogin.com`],
    redirectUri: "/",
    postLogoutRedirectUri: "/",
  },
  cache: {
    cacheLocation: "localStorage",
  },
};

export const loginRequest = {
  scopes: ["openid", "profile"],
};
