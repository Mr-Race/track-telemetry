/**
 * Demo build flag (ADR-012).
 *
 * `demo.mr-race.com` serves this same app compiled with VITE_DEMO_MODE=1,
 * reading static JSON from `public/demo-api` instead of the real API.
 * Fictional data never shares a database with real GPS traces, so the
 * isolation problem is deleted rather than solved.
 *
 * Two consequences follow, and both are enforced here rather than left
 * to each caller to remember:
 *   - no bearer token is requested, and sign-in is bypassed entirely
 *   - writes are refused, because there is no backend to write to
 */
export const IS_DEMO = import.meta.env.VITE_DEMO_MODE === "1";

/** Thrown if a write is attempted in the demo. The UI hides these
 * controls, so reaching this means one was missed. */
export class DemoReadOnlyError extends Error {
  constructor(path: string) {
    super(
      `This is a read-only demo — ${path} is not available. ` +
        `See www.mr-race.com for the real thing.`,
    );
    this.name = "DemoReadOnlyError";
  }
}
