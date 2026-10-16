"use client"

interface ScoreBarProps {
  value: number
  size?: "sm" | "md"
}

export function ScoreBar({ value, size = "md" }: ScoreBarProps) {
  const pct = Math.round(value * 100)
  const color =
    value >= 0.9 ? "var(--green)"
    : value >= 0.5 ? "var(--accent)"
    : value >= 0.25 ? "var(--amber)"
    : "var(--red)"

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span className="mono" style={{
        color, minWidth: size === "sm" ? 34 : 40,
        fontSize: size === "sm" ? 11 : 13,
        fontWeight: 600,
        textShadow: `0 0 10px ${color}50`,
      }}>
        {pct}%
      </span>
      <div style={{
        flex: 1, minWidth: 60,
        height: size === "sm" ? 2 : 3,
        background: "rgba(255,255,255,0.06)",
        borderRadius: 2,
      }}>
        <div style={{
          width: `${pct}%`, height: "100%", borderRadius: 2,
          background: `linear-gradient(90deg, ${color}cc, ${color})`,
          boxShadow: `0 0 8px ${color}60`,
          transition: "width 0.4s ease",
        }} />
      </div>
    </div>
  )
}
