import type { AccountInfo, IPublicClientApplication } from "@azure/msal-browser";
import { EventType, PublicClientApplication } from "@azure/msal-browser";
import { msalConfig } from "./authConfig";

export const msalInstance = new PublicClientApplication(msalConfig);

/** Adopt a cached account as the active one, if there isn't one already.
 *
 * MSAL only raises LOGIN_SUCCESS for a *fresh* sign-in, and the event
 * callback below is what sets the active account. On a page reload the
 * session is restored from cache and no event fires, so without this
 * nothing ever sets it.
 *
 * That mattered because the two ideas of "signed in" disagree:
 * `useIsAuthenticated()` and `AuthenticatedTemplate` look at *all*
 * accounts, so the UI rendered as signed in, while `getAccessToken()`
 * in api/client.ts asks for the *active* account, got null, and sent
 * every request with no Authorization header - a 401 on every call and
 * an app that looked logged in but loaded no data.
 *
 * Takes the instance as a parameter so it can be exercised without a
 * browser. Returns the adopted account, or null if there was nothing to
 * adopt or one was already active.
 */
export function restoreActiveAccount(
  instance: Pick<IPublicClientApplication,
    "getActiveAccount" | "getAllAccounts" | "setActiveAccount">,
): AccountInfo | null {
  if (instance.getActiveAccount()) return null;

  const [first] = instance.getAllAccounts();
  if (!first) return null;

  instance.setActiveAccount(first);
  return first;
}

msalInstance.addEventCallback((event) => {
  if (
    (event.eventType === EventType.LOGIN_SUCCESS ||
      event.eventType === EventType.ACQUIRE_TOKEN_SUCCESS) &&
    event.payload &&
    "account" in event.payload &&
    event.payload.account
  ) {
    msalInstance.setActiveAccount(event.payload.account);
  }
});
