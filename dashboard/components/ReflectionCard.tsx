"use client"

import { useState } from "react"
import type { RunStep } from "@/lib/api"
import { antipatternBadge, qualityBadge } from "./Badge"

const FAILURE_COLOR: Record<string, string> = {
  logic_error:      "var(--accent)",
  format_error:     "var(--amber)",
  misunderstanding: "var(--purple)",
  overcomplication: "var(--red)",
  partial_solution: "var(--green)",
  tool_misuse:      "var(--text-2)",
}

const CONFIDENCE_COLOR: Record<string, string> = {
  high:   "var(--green)",
  medium: "var(--amber)",
  low:    "var(--text-3)",
}

function scoreColor(v: number) {
  if (v >= 0.9) return "var(--green)"
  if (v >= 0.5) return "var(--accent)"
  if (v >= 0.25) return "var(--amber)"
  return "var(--red)"
}

export function ReflectionCard({ step, isLast }: { step: RunStep; isLast: boolean }) {
  const [expanded, setExpanded] = useState(isLast)
  const r = step.reflection
  const sc = scoreColor(step.score_composite)

  return (
    <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: 16, position: "relative" }}>
      {/* timeline dot */}
      <div style={{
        position: "absolute", left: -5, top: 14,
        width: 9, height: 9, borderRadius: "50%",
        background: step.reward_hacked ? "var(--red)" : sc,
        border: "2px solid var(--bg)",
      }} />

      {/* header */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: "100%", textAlign: "left", background: "none", border: "none",
          padding: "10px 0", display: "flex", alignItems: "center", gap: 10, cursor: "pointer",
        }}
      >
        <span className="mono" style={{ color: "var(--text-3)", minWidth: 54, fontSize: 11 }}>
          iter {step.iteration}
        </span>
        <span className="mono" style={{ color: sc, minWidth: 40, fontWeight: 600, fontSize: 12 }}>
          {(step.score_composite * 100).toFixed(0)}%
        </span>
        {r && (
          <span className="mono" style={{
            fontSize: 10, padding: "2px 6px", borderRadius: 4,
            background: "var(--surface-2)",
            color: FAILURE_COLOR[r.failure_type] ?? "var(--text-2)",
            border: "1px solid var(--border-2)",
          }}>
            {r.failure_type.replace("_", " ")}
          </span>
        )}
        {r && (
          <span className="mono" style={{ fontSize: 10, color: CONFIDENCE_COLOR[r.confidence] ?? "var(--text-3)" }}>
            {r.confidence} conf
          </span>
        )}
        <div style={{ display: "flex", gap: 6, marginLeft: "auto", alignItems: "center" }}>
          {antipatternBadge(step.antipattern)}
          {r && qualityBadge(step.reflection_quality)}
          {step.reward_hacked && <span className="mono" style={{ fontSize: 10, color: "var(--red)" }}>hacked</span>}
          {!r && <span className="mono" style={{ fontSize: 10, color: "var(--green)" }}>solved</span>}
        </div>
        <span style={{ color: "var(--text-3)", fontSize: 10 }}>{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div style={{ paddingBottom: 20 }}>
          {/* score breakdown */}
          <div className="mono" style={{ fontSize: 11, display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 10, color: "var(--text-2)" }}>
            {Object.entries(step.score_breakdown).map(([k, v]) => (
              <span key={k}>{k} <span style={{ color: "var(--text)" }}>{(v * 100).toFixed(0)}%</span></span>
            ))}
          </div>

          {/* attempt */}
          <div className="mono" style={{
            fontSize: 11.5, borderRadius: 8, padding: "10px 12px", marginBottom: 10,
            background: "var(--surface)", border: "1px solid var(--border)",
            color: "var(--text)", whiteSpace: "pre-wrap", wordBreak: "break-word",
            maxHeight: 220, overflowY: "auto", lineHeight: 1.65,
          }}>
            {step.attempt}
          </div>

          {/* reflection */}
          {r && !step.reflection_parse_failed && (
            <div style={{
              borderRadius: 8, overflow: "hidden",
              border: "1px solid var(--border)", fontSize: 12,
            }}>
              <ReflRow label="root cause"  value={r.root_cause} />
              <ReflRow label="what worked" value={r.what_worked} dim />
              <div style={{ padding: "10px 12px", background: "var(--surface-2)", borderLeft: "2px solid var(--accent)" }}>
                <div className="mono" style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-3)", marginBottom: 4 }}>
                  strategy
                </div>
                <p style={{ color: "var(--text)", lineHeight: 1.6, margin: 0 }}>{r.strategy_update}</p>
              </div>
            </div>
          )}
          {step.reflection_parse_failed && (
            <p className="mono" style={{ fontSize: 11, color: "var(--red)", opacity: 0.7 }}>
              reflection parse failed
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function ReflRow({ label, value, dim }: { label: string; value: string; dim?: boolean }) {
  return (
    <div style={{ padding: "10px 12px", background: "var(--surface)", borderBottom: "1px solid var(--border)" }}>
      <div className="mono" style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-3)", marginBottom: 3 }}>
        {label}
      </div>
      <p style={{ color: dim ? "var(--text-2)" : "var(--text)", lineHeight: 1.6, margin: 0 }}>{value}</p>
    </div>
  )
}
