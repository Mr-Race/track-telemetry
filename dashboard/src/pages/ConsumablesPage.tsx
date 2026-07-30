import { getConsumables, type Consumable } from "../api/client";
import { useFetch } from "../api/useFetch";

function lifeClass(c: Consumable): string {
  if (c.overdue) return "life-critical";
  if (c.remaining_pct !== null && c.remaining_pct < 25) return "life-warning";
  return "life-good";
}

function ConsumableRow({ c }: { c: Consumable }) {
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
      </div>
    </div>
  );
}

export function ConsumablesPage() {
  const state = useFetch(getConsumables, []);

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
        <ConsumableRow key={c.consumable_id} c={c} />
      ))}
    </div>
  );
}
