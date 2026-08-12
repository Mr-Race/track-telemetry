import { describe, expect, it, vi } from "vitest";

import { restoreActiveAccount } from "./msalInstance";

/** The three methods restoreActiveAccount actually touches. */
function fakeInstance(accounts: { username: string }[], active: unknown = null) {
  let current = active;
  return {
    getAllAccounts: () => accounts,
    getActiveAccount: () => current,
    setActiveAccount: vi.fn((a: unknown) => { current = a; }),
    get active() { return current; },
  };
}

describe("restoreActiveAccount", () => {
  it("adopts a cached account when none is active", () => {
    // The production bug, 2026-08-10: MSAL only raises LOGIN_SUCCESS on
    // a *fresh* sign-in, so a reloaded session had accounts but no
    // active one. The UI rendered as signed in while every API call went
    // out with no bearer token and came back 401.
    const instance = fakeInstance([{ username: "me@example.com" }]);

    const adopted = restoreActiveAccount(instance as never);

    expect(instance.setActiveAccount).toHaveBeenCalledOnce();
    expect(adopted).toEqual({ username: "me@example.com" });
    expect(instance.active).toEqual({ username: "me@example.com" });
  });

  it("leaves an already-active account alone", () => {
    const active = { username: "first@example.com" };
    const instance = fakeInstance(
      [{ username: "second@example.com" }], active);

    expect(restoreActiveAccount(instance as never)).toBeNull();
    expect(instance.setActiveAccount).not.toHaveBeenCalled();
    expect(instance.active).toBe(active);
  });

  it("does nothing when signed out", () => {
    // Runs before the first render, so throwing here would blank the
    // whole app for a signed-out visitor.
    const instance = fakeInstance([]);

    expect(restoreActiveAccount(instance as never)).toBeNull();
    expect(instance.setActiveAccount).not.toHaveBeenCalled();
  });

  it("takes the first account when several are cached", () => {
    const instance = fakeInstance([
      { username: "first@example.com" },
      { username: "second@example.com" },
    ]);

    expect(restoreActiveAccount(instance as never))
      .toEqual({ username: "first@example.com" });
  });
});
