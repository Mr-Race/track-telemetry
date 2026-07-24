import type { Configuration } from "@azure/msal-browser";

const clientId = import.meta.env.VITE_MSAL_CLIENT_ID;
const authority = import.meta.env.VITE_MSAL_AUTHORITY;
const tenantId = import.meta.env.VITE_MSAL_TENANT_ID;
const apiScope = import.meta.env.VITE_API_SCOPE;

if (!clientId || !authority || !tenantId || !apiScope) {
  throw new Error(
    "Missing VITE_MSAL_CLIENT_ID, VITE_MSAL_AUTHORITY, VITE_MSAL_TENANT_ID, or VITE_API_SCOPE env vars",
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

// Requesting the API scope alongside openid/profile at sign-in means
// consent for it happens in the same initial redirect, rather than a
// second redirect the first time the dashboard calls the API.
export const loginRequest = {
  scopes: ["openid", "profile", apiScope],
};

export const apiRequest = {
  scopes: [apiScope],
};
