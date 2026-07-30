import { useState } from "react";
import { getConsumables, replaceConsumable, type Consumable } from "../api/client";
import { useFetch } from "../api/useFetch";

function lifeClass(c: Consumable): string {
  if (c.overdue) return "life-critical";
  if (c.remaining_pct !== null && c.remaining_pct < 25) return "life-warning";
  return "life-good";
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function ReplaceForm({
  consumableId,
  onDone,
  onCancel,
}: {
  consumableId: number;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [installDate, setInstallDate] = useState(todayIso());
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await replaceConsumable(consumableId, {
        install_date: installDate,
        notes: notes.trim() || null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <form className="form-row consumable-replace-form" onSubmit={handleSubmit}>
      <label>
        Replacement date
        <input
          className="form-input"
          type="date"
          value={installDate}
          onChange={(e) => setInstallDate(e.target.value)}
          required
        />
      </label>
      <label>
        Notes
        <input
          className="form-input"
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="e.g. Hawk DTC-60, fresh pads"
        />
      </label>
      <div className="consumable-replace-actions">
        <button className="cta-button" type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Confirm replacement"}
        </button>
        <button
          type="button"
          className="link-button"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancel
        </button>
      </div>
      {error && <span className="delta-bad"> {error}</span>}
    </form>
  );
}

function ConsumableRow({
  c,
  onReplaced,
}: {
  c: Consumable;
  onReplaced: () => void;
}) {
  const [replacing, setReplacing] = useState(false);
  const pct = c.remaining_pct;
  return (
    <div className="consumable-row">
      <div className="consumable-header">
        <span>{c.item_name}</span>
        <span className={lifeClass(c)}>
          {c.overdue
            ? "Overdue"
            : pct !== null
              ? `${pct}% remaining`
              : "No service life set"}
        </span>
      </div>
      {pct !== null && (
        <div className="life-bar-track">
          <div
            className={`life-bar-fill ${lifeClass(c)}`}
            style={{ width: `${Math.min(100, pct)}%` }}
          />
        </div>
      )}
      <div className="muted consumable-meta">
        {c.car && `${c.car} · `}
        Installed {c.install_date} &middot; {c.sessions_since_install} session
        {c.sessions_since_install === 1 ? "" : "s"} / {c.months_since_install} month
        {c.months_since_install === 1 ? "" : "s"} since install
        {c.service_life_sessions && ` · service life ${c.service_life_sessions} sessions`}
        {c.service_life_months && ` · ${c.service_life_months} months`}
        {c.notes && ` · ${c.notes}`}
        {" · "}
        <button
          type="button"
          className="link-button"
          onClick={() => setReplacing(true)}
        >
          Log replacement
        </button>
      </div>
      {replacing && (
        <ReplaceForm
          consumableId={c.consumable_id}
          onDone={() => {
            setReplacing(false);
            onReplaced();
          }}
          onCancel={() => setReplacing(false)}
        />
      )}
    </div>
  );
}

export function ConsumablesPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const state = useFetch(getConsumables, [refreshKey]);

  if (state.status === "loading") return <p className="muted">Loading consumables…</p>;
  if (state.status === "error") return <p className="delta-bad">Error: {state.message}</p>;

  const consumables = state.data;
  if (consumables.length === 0) {
    return (
      <p className="muted">
        No consumables tracked yet. Add rows to dbo.consumables (see sql/08_consumables.sql).
      </p>
    );
  }

  return (
    <div>
      {consumables.map((c) => (
        <ConsumableRow
          key={c.consumable_id}
          c={c}
          onReplaced={() => setRefreshKey((k) => k + 1)}
        />
      ))}
    </div>
  );
}
