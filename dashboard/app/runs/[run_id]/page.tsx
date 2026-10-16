"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import Link from "next/link"
import { ScoreChart } from "@/components/ScoreChart"
import { ReflectionCard } from "@/components/ReflectionCard"
import type { RunDetail } from "@/lib/api"

function Sk({ w, h = 12 }: { w: number | string; h?: number }) {
  return <div className="skeleton" style={{ width: w, height: h }} />
}

function scoreColor(v: number) {
  if (v >= 0.9) return "var(--green)"
  if (v >= 0.5) return "var(--accent)"
  if (v >= 0.25) return "var(--amber)"
  return "var(--red)"
}

const SIGNAL_COLORS: Record<string, string> = {
  correctness: "#4f7cff", progress: "#a855f7", conciseness: "#22c55e", format: "#f59e0b",
}

export default function RunPage() {
  const { run_id } = useParams<{ run_id: string }>()
  const [run, setRun]     = useState<RunDetail | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetch(`http://localhost:8000/api/runs/${run_id}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setRun).catch(() => setError(true))
  }, [run_id])

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "32px 24px 80px" }}>

      {/* breadcrumb */}
      <div className="mono" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-3)", marginBottom: 28 }}>
        <Link href="/experiments" style={{ color: "var(--text-3)", textDecoration: "none" }}>experiments</Link>
        <span>/</span>
        {run
          ? <Link href={`/experiments/${encodeURIComponent(run.experiment_name)}`}
              style={{ color: "var(--text-3)", textDecoration: "none" }}>{run.experiment_name}</Link>
          : <Sk w={80} h={10} />
        }
        <span>/</span>
        <span style={{ color: "var(--text-2)" }}>{run?.task_id ?? run_id.slice(0, 8)}</span>
      </div>

      {error && (
        <p className="mono" style={{ fontSize: 12, color: "var(--red)" }}>
          Failed to load run. Make sure the API is running at localhost:8000.
        </p>
      )}

      {/* skeleton */}
      {!run && !error && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <Sk w={200} h={22} /><Sk w={300} h={12} />
            </div>
            <Sk w={80} h={48} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 1, background: "var(--border)", borderRadius: 10, overflow: "hidden" }}>
            {[1,2,3,4,5].map(i => (
              <div key={i} style={{ background: "var(--surface)", padding: "14px 16px" }}>
                <Sk w={56} h={8} /><div style={{ marginTop: 10 }}><Sk w={40} h={16} /></div>
              </div>
            ))}
          </div>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
            <Sk w={120} h={8} /><div style={{ marginTop: 16 }}><Sk w="100%" h={160} /></div>
          </div>
        </div>
      )}

      {run && (() => {
        const steps  = run.steps
        const first  = steps[0]
        const last   = steps[steps.length - 1]
        const delta  = steps.length > 1 ? last.score_composite - first.score_composite : 0
        const scored = steps.filter(s => s.reflection_quality != null)
        const avgQ   = scored.length ? scored.reduce((a,s) => a + (s.reflection_quality ?? 0), 0) / scored.length : null
        const signals= first ? Object.keys(first.score_breakdown) : []

        return (
          <>
            {/* hero */}
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 28 }}>
              <div>
                <h1 style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.03em", color: "var(--text)", marginBottom: 8 }}>
                  {run.task_id}
                </h1>
                <p style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.7, margin: 0 }}>
                  {steps.length} iteration{steps.length !== 1 ? "s" : ""} · {run.experiment_name}
                  {delta !== 0 && (
                    <> · <span style={{ color: delta > 0 ? "var(--green)" : "var(--red)" }}>
                      {delta > 0 ? "+" : ""}{(delta * 100).toFixed(0)}pp
                    </span> across run</>
                  )}
                </p>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{
                  fontSize: 44, fontWeight: 700, letterSpacing: "-0.04em",
                  color: scoreColor(last.score_composite), lineHeight: 1,
                  fontFamily: "var(--font-geist-mono)",
                }}>
                  {(last.score_composite * 100).toFixed(0)}
                  <span style={{ fontSize: 18, color: "var(--text-3)" }}>%</span>
                </div>
                <div className="mono" style={{ fontSize: 10, color: "var(--text-3)", marginTop: 4 }}>final score</div>
              </div>
            </div>

            {/* stat strip */}
            <div style={{
              display: "grid", gridTemplateColumns: "repeat(5,1fr)",
              gap: 1, background: "var(--border)", borderRadius: 10,
              overflow: "hidden", marginBottom: 24,
            }}>
              {[
                { label: "iterations",    value: String(steps.length) },
                { label: "refl quality",  value: avgQ != null ? `${avgQ.toFixed(1)}/3` : "—" },
                { label: "anti-patterns", value: String(steps.filter(s => s.antipattern !== "none").length) },
                { label: "parse fails",   value: String(steps.filter(s => s.reflection_parse_failed).length) },
                { label: "reward hacked", value: steps.some(s => s.reward_hacked) ? "yes" : "no" },
              ].map(({ label, value }) => (
                <div key={label} style={{ background: "var(--surface)", padding: "12px 16px" }}>
                  <div className="mono" style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-3)", marginBottom: 6 }}>
                    {label}
                  </div>
                  <div className="mono" style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>{value}</div>
                </div>
              ))}
            </div>

            {/* chart */}
            {steps.length > 1 && (
              <div style={{
                background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: 10, padding: "18px 12px 12px", marginBottom: 10,
              }}>
                <div className="mono" style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-3)", paddingLeft: 8, marginBottom: 14 }}>
                  score trajectory
                </div>
                <ScoreChart steps={steps} />
              </div>
            )}

            {/* chart legend */}
            {steps.length > 1 && (
              <div style={{ display: "flex", gap: 20, marginBottom: 28, paddingLeft: 4, flexWrap: "wrap" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div style={{ width: 18, height: 2, background: "var(--text)", borderRadius: 1 }} />
                  <span className="mono" style={{ fontSize: 10, color: "var(--text-2)" }}>composite</span>
                </div>
                {signals.map(sig => (
                  <div key={sig} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div style={{ width: 18, height: 1, background: SIGNAL_COLORS[sig] ?? "var(--text-3)", opacity: 0.7, borderRadius: 1 }} />
                    <span className="mono" style={{ fontSize: 10, color: "var(--text-2)" }}>{sig}</span>
                  </div>
                ))}
              </div>
            )}

            {/* iteration trace */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <span className="mono" style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-3)" }}>
                iteration trace
              </span>
              <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>click to expand</span>
            </div>
            <div style={{ paddingLeft: 8 }}>
              {steps.map((step, i) => (
                <ReflectionCard key={step.iteration} step={step} isLast={i === steps.length - 1} />
              ))}
            </div>
          </>
        )
      })()}
    </main>
  )
}
