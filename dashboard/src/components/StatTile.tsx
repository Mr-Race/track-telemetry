// Colour on a tile value is semantic, never decorative: purple marks a
// fastest/optimal time (timing-tower convention), green/red an
// improvement or a regression. See docs/specs/event-summary-page.md.
export type StatTone = "fastest" | "good" | "bad";

interface StatTileProps {
  label: string;
  value: string;
  sublabel?: string;
  tone?: StatTone;
  // "hero" is the event page's big label/value/caption stack; the
  // default is the compact tile the session pages already use.
  variant?: "hero";
}

export function StatTile({ label, value, sublabel, tone, variant }: StatTileProps) {
  const valueClass = ["stat-tile-value", tone && `tone-${tone}`].filter(Boolean).join(" ");

  return (
    <div className={variant === "hero" ? "stat-tile hero" : "stat-tile"}>
      <div className="stat-tile-label">{label}</div>
      <div className={valueClass}>{value}</div>
      {sublabel && <div className="stat-tile-sublabel">{sublabel}</div>}
    </div>
  );
}
