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

// The unit lives in the column header, not in every cell - repeating
// "mph" ten times down a narrow phone column forces the numbers to wrap.
function SpeedCell({ mph }: { mph: number | null }) {
  return <td className="tabular nowrap">{mph !== null ? mph.toFixed(1) : "—"}</td>;
}

// "T9 Lightbulb" where the corner has a curated name, bare "T2" where
// it doesn't.
function cornerLabel(d: CornerDelta): string {
  return d.corner_name ? `T${d.corner_code} ${d.corner_name}` : `T${d.corner_code}`;
}

interface CornerDeltaLabels {
  current: string;
  prior: string;
}

const DEFAULT_LABELS: CornerDeltaLabels = { current: "This session", prior: "Prior session" };

export function CornerDeltaTable({
  deltas,
  labels = DEFAULT_LABELS,
  className,
  // The session page reads "this vs prior"; the event page's day arc
  // reads left-to-right in time ("S1 MIN, S2 MIN"), so the two columns
  // swap rather than the page forking the component.
  columnOrder = "current-first",
}: {
  deltas: CornerDelta[];
  labels?: CornerDeltaLabels;
  className?: string;
  columnOrder?: "current-first" | "prior-first";
}) {
  if (deltas.length === 0) {
    return <p className="muted">No prior session at this track to compare against.</p>;
  }

  const priorFirst = columnOrder === "prior-first";

  return (
    <table className={className ? `data-table ${className}` : "data-table"}>
      <thead>
        <tr>
          <th>Corner</th>
          <th>{priorFirst ? labels.prior : labels.current} (mph)</th>
          <th>{priorFirst ? labels.current : labels.prior} (mph)</th>
          <th>Delta</th>
        </tr>
      </thead>
      <tbody>
        {deltas.map((d) => (
          <tr key={d.corner_code}>
            <td className="corner-cell">{cornerLabel(d)}</td>
            <SpeedCell mph={priorFirst ? d.prior_min_speed_mph : d.min_speed_mph} />
            <SpeedCell mph={priorFirst ? d.min_speed_mph : d.prior_min_speed_mph} />
            <td className="tabular">
              <DeltaCell delta={d.delta_mph} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
