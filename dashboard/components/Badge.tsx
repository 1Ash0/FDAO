type Variant = "green" | "red" | "amber" | "purple" | "blue" | "muted"

const MAP: Record<Variant, { bg: string; color: string; border: string; shadow?: string }> = {
  green:  { bg: "rgba(34,212,110,0.10)",  color: "var(--green)",  border: "rgba(34,212,110,0.25)",  shadow: "0 0 8px rgba(34,212,110,0.15)" },
  red:    { bg: "rgba(240,68,68,0.10)",   color: "var(--red)",    border: "rgba(240,68,68,0.25)" },
  amber:  { bg: "rgba(240,160,32,0.10)",  color: "var(--amber)",  border: "rgba(240,160,32,0.25)" },
  purple: { bg: "rgba(168,85,247,0.10)",  color: "var(--purple)", border: "rgba(168,85,247,0.25)" },
  blue:   { bg: "rgba(79,126,255,0.10)",  color: "var(--accent)", border: "rgba(79,126,255,0.25)" },
  muted:  { bg: "rgba(255,255,255,0.04)", color: "var(--text-2)", border: "rgba(255,255,255,0.08)" },
}

export function Badge({ label, variant }: { label: string; variant: Variant }) {
  const s = MAP[variant]
  return (
    <span className="mono" style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 6px", borderRadius: 4,
      fontSize: 10, fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase",
      background: s.bg, color: s.color,
      border: `1px solid ${s.border}`,
      boxShadow: s.shadow,
    }}>
      {label}
    </span>
  )
}

export function antipatternBadge(ap: string) {
  if (ap === "circular")    return <Badge key={ap} label="circular"    variant="amber" />
  if (ap === "overcorrect") return <Badge key={ap} label="overcorrect" variant="red"   />
  if (ap === "drift")       return <Badge key={ap} label="drift"       variant="purple"/>
  return null
}

export function qualityBadge(q: number | null) {
  if (q === null) return <Badge label="unscored" variant="muted" />
  if (q === 3)    return <Badge label="3/3"      variant="green" />
  if (q === 2)    return <Badge label="2/3"      variant="blue"  />
  if (q === 1)    return <Badge label="1/3"      variant="amber" />
  return           <Badge label="0/3"            variant="red"   />
}
