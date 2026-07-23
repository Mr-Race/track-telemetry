/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_MSAL_CLIENT_ID: string;
  readonly VITE_MSAL_AUTHORITY: string;
  readonly VITE_MSAL_TENANT_ID: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
