import type { CornerDelta } from "../api/client";

function DeltaCell({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="muted">—</span>;
  const sign = delta > 0 ? "+" : "";
  const className = delta > 0 ? "delta-good" : delta < 0 ? "delta-bad" : "muted";
  const arrow = delta > 0 ? "▲" : delta < 0 ? "▼" : "";
  return (
    <span className={className}>
      {arrow} {sign}
      {delta.toFixed(1)} mph
    </span>
  );
}

export function CornerDeltaTable({ deltas }: { deltas: CornerDelta[] }) {
  if (deltas.length === 0) {
    return <p className="muted">No prior session at this track to compare against.</p>;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Corner</th>
          <th>This session</th>
          <th>Prior session</th>
          <th>Delta</th>
        </tr>
      </thead>
      <tbody>
        {deltas.map((d) => (
          <tr key={d.corner_code}>
            <td>{d.corner_code}</td>
            <td className="tabular">{d.min_speed_mph.toFixed(1)} mph</td>
            <td className="tabular">
              {d.prior_min_speed_mph !== null ? `${d.prior_min_speed_mph.toFixed(1)} mph` : "—"}
            </td>
            <td className="tabular">
              <DeltaCell delta={d.delta_mph} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
