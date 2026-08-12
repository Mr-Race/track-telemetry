import { useEffect, useState } from "react";

// The free-tier database auto-pauses, and the first request after that
// takes 30-60s to resume it. A bare "Loading..." for the best part of a
// minute is indistinguishable from the app being broken - which is
// exactly how a fixed app looked during the 2026-08-10 incident. So
// after a few seconds, say what is actually happening.
const EXPLAIN_AFTER_MS = 4000;

export function Loading({ what = "" }: { what?: string }) {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), EXPLAIN_AFTER_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="muted">
      <p>Loading{what ? ` ${what}` : ""}…</p>
      {slow && (
        <p className="loading-note">
          Waking the database — the first request after an idle period can
          take up to a minute. Later ones are fast.
        </p>
      )}
    </div>
  );
}
