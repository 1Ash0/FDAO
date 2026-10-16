"use client"

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts"
import type { RunStep } from "@/lib/api"

interface Props {
  steps: RunStep[]
}

const SIGNAL_COLORS: Record<string, string> = {
  correctness: "#4f7cff",
  progress:    "#a855f7",
  conciseness: "#22c55e",
  format:      "#f59e0b",
  composite:   "#e2e4ed",
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="mono"
      style={{
        background: "var(--surface-2)",
        border: "1px solid var(--border-bright)",
        borderRadius: 6,
        padding: "8px 12px",
        fontSize: 11,
        minWidth: 140,
      }}
    >
      <div style={{ color: "var(--text-muted)", marginBottom: 6 }}>iter {label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color, display: "flex", justifyContent: "space-between", gap: 16 }}>
          <span>{p.name}</span>
          <span>{(p.value * 100).toFixed(0)}%</span>
        </div>
      ))}
    </div>
  )
}

export function ScoreChart({ steps }: Props) {
  const signals = steps[0]
    ? Object.keys(steps[0].score_breakdown)
    : []

  const data = steps.map((s) => ({
    iter: s.iteration,
    composite: s.score_composite,
    ...s.score_breakdown,
  }))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="iter"
          tick={{ fill: "var(--text-muted)", fontSize: 11, fontFamily: "var(--font-geist-mono)" }}
          axisLine={false}
          tickLine={false}
          label={{ value: "iteration", position: "insideBottom", offset: -2, fill: "var(--text-dim)", fontSize: 10 }}
        />
        <YAxis
          domain={[0, 1]}
          tick={{ fill: "var(--text-muted)", fontSize: 11, fontFamily: "var(--font-geist-mono)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={1} stroke="var(--green)" strokeDasharray="4 4" strokeOpacity={0.4} />
        {/* individual signals as thin lines */}
        {signals.map((sig) => (
          <Line
            key={sig}
            type="monotone"
            dataKey={sig}
            stroke={SIGNAL_COLORS[sig] ?? "var(--text-dim)"}
            strokeWidth={1}
            dot={false}
            strokeOpacity={0.5}
          />
        ))}
        {/* composite as bright line on top */}
        <Line
          type="monotone"
          dataKey="composite"
          stroke="var(--text)"
          strokeWidth={2}
          dot={{ fill: "var(--text)", r: 3, strokeWidth: 0 }}
          activeDot={{ r: 4, fill: "var(--accent)" }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
