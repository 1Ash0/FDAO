"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { LiveRun } from "@/components/LiveRun"
import type { AggregateMetrics, ExperimentSummary } from "@/lib/api"

/* ── Loop diagram: shows the FDAO concept ── */
function LoopDiagram() {
  const steps = [
    { icon: "⟳", label: "attempt",  color: "#5b8aff", desc: "LLM generates a solution" },
    { icon: "◈", label: "score",    color: "#00e87a", desc: "Reward function evaluates" },
    { icon: "◉", label: "reflect",  color: "#b06aff", desc: "Agent reasons over failure" },
    { icon: "↑", label: "improve",  color: "#ffb020", desc: "Better strategy injected" },
  ]
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 56 }}>
      {steps.map((s, i) => (
        <div key={s.label} style={{ display: "flex", alignItems: "center" }}>
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
            animation: `float-up 3s ease-in-out ${i * 0.4}s infinite`,
          }}>
            <div style={{
              width: 48, height: 48, borderRadius: 14,
              border: `1px solid ${s.color}40`,
              background: `${s.color}0e`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 20, color: s.color,
              boxShadow: `0 0 20px ${s.color}25, inset 0 1px 0 ${s.color}20`,
            }}>
              {s.icon}
            </div>
            <span className="mono" style={{
              fontSize: 9, textTransform: "uppercase", letterSpacing: "0.12em",
              color: s.color, fontWeight: 700,
            }}>
              {s.label}
            </span>
            <span style={{ fontSize: 10, color: "var(--text-3)", textAlign: "center", maxWidth: 72, lineHeight: 1.5 }}>
              {s.desc}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div style={{
              width: 48, height: 1, flexShrink: 0, margin: "-28px 0 0",
              background: `linear-gradient(90deg, ${steps[i].color}60, ${steps[i+1].color}60)`,
              position: "relative",
            }}>
              <span style={{
                position: "absolute", right: -4, top: -5,
                color: steps[i+1].color, fontSize: 10, opacity: 0.7,
              }}>›</span>
            </div>
          )}
        </div>
      ))}
      {/* loop back arrow */}
      <div style={{
        marginLeft: 8, fontSize: 11, color: "var(--text-3)",
        fontFamily: "var(--font-geist-mono)",
        borderLeft: "1px solid rgba(91,138,255,0.15)",
        paddingLeft: 12,
      }}>
        <span style={{ color: "var(--accent)", opacity: 0.6 }}>∞</span>
        <span style={{ marginLeft: 6, fontSize: 10 }}>no weight updates</span>
      </div>
    </div>
  )
}

/* ── Stat card ── */
function StatCard({ label, value, sub, color }: {
  label: string; value: string; sub?: string; color: string
}) {
  return (
    <div style={{
      flex: "1 1 150px",
      background: "rgba(8,12,26,0.7)",
      border: `1px solid ${color}25`,
      borderRadius: 14,
      padding: "18px 20px",
      position: "relative", overflow: "hidden",
      backdropFilter: "blur(16px)",
    }}>
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
        opacity: 0.6,
      }} />
      <div style={{
        position: "absolute", top: -30, right: -30, width: 80, height: 80,
        borderRadius: "50%",
        background: `radial-gradient(circle, ${color}18 0%, transparent 70%)`,
      }} />
      <div className="mono" style={{
        fontSize: 9, textTransform: "uppercase", letterSpacing: "0.14em",
        color: "var(--text-3)", marginBottom: 10,
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 30, fontWeight: 800, letterSpacing: "-0.05em", lineHeight: 1,
        color: color,
        textShadow: `0 0 30px ${color}60`,
      }}>
        {value}
      </div>
      {sub && (
        <div className="mono" style={{ fontSize: 10, color: "var(--text-3)", marginTop: 6 }}>{sub}</div>
      )}
    </div>
  )
}

function StatCardSk() {
  return (
    <div style={{
      flex: "1 1 150px", background: "rgba(8,12,26,0.7)",
      border: "1px solid rgba(91,138,255,0.08)", borderRadius: 14, padding: "18px 20px",
    }}>
      <div className="skeleton" style={{ width: 52, height: 8 }} />
      <div className="skeleton" style={{ width: 64, height: 30, marginTop: 12 }} />
      <div className="skeleton" style={{ width: 48, height: 8, marginTop: 8 }} />
    </div>
  )
}

/* ── Experiments table ── */
function ExperimentsTable({ experiments }: { experiments: ExperimentSummary[] | null }) {
  const scoreColor = (v: number) =>
    v >= 0.7 ? "var(--green)" : v >= 0.4 ? "var(--accent)" : "var(--amber)"

  return (
    <div>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16,
      }}>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>
            Experiments
          </h2>
          <p style={{ fontSize: 11, color: "var(--text-3)", marginTop: 2 }}>
            Each row is a full agent-optimization run across a task suite
          </p>
        </div>
        {experiments && experiments.length > 0 && (
          <Link href="/experiments" style={{
            textDecoration: "none", fontSize: 11, fontFamily: "var(--font-geist-mono)",
            color: "var(--accent)", display: "flex", alignItems: "center", gap: 4,
            border: "1px solid rgba(91,138,255,0.2)", borderRadius: 7,
            padding: "5px 12px", background: "rgba(91,138,255,0.06)",
          }}>
            view all →
          </Link>
        )}
      </div>

      <div style={{
        border: "1px solid rgba(91,138,255,0.15)",
        borderRadius: 14, overflow: "hidden",
        background: "rgba(6,8,18,0.8)",
        backdropFilter: "blur(16px)",
        boxShadow: "0 4px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(91,138,255,0.05) inset",
      }}>
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 56px 88px 96px 48px",
          padding: "10px 18px",
          borderBottom: "1px solid rgba(91,138,255,0.1)",
          background: "rgba(91,138,255,0.04)",
        }}>
          {["experiment", "runs", "converged", "avg score", "APs"].map(h => (
            <span key={h} className="mono" style={{
              fontSize: 9, textTransform: "uppercase",
              letterSpacing: "0.13em", color: "var(--text-3)",
            }}>
              {h}
            </span>
          ))}
        </div>

        {!experiments && [1, 2].map(i => (
          <div key={i} style={{
            display: "flex", gap: 16, padding: "14px 18px", alignItems: "center",
            borderBottom: "1px solid rgba(91,138,255,0.05)",
          }}>
            {[120, 28, 48, 64, 24].map((w, j) => (
              <div key={j} className="skeleton" style={{ width: w, height: 10 }} />
            ))}
          </div>
        ))}

        {experiments?.length === 0 && (
          <div style={{ padding: "48px 18px", textAlign: "center" }}>
            <div style={{ fontSize: 24, marginBottom: 12, opacity: 0.3 }}>◎</div>
            <p className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>
              No experiments yet —{" "}
              <code style={{ color: "var(--accent)" }}>python scripts/run_phase3.py</code>
            </p>
          </div>
        )}

        {experiments?.map((exp, i) => {
          const rate    = exp.n_runs > 0 ? exp.converged / exp.n_runs : 0
          const apCount = Object.values(exp.antipattern_breakdown).reduce((a, b) => a + b, 0)
          return (
            <Link key={exp.experiment_name}
              href={`/experiments/${encodeURIComponent(exp.experiment_name)}`}
              style={{ textDecoration: "none", display: "block" }}>
              <div className="trow" style={{
                display: "grid", gridTemplateColumns: "1fr 56px 88px 96px 48px",
                padding: "13px 18px", alignItems: "center",
                borderBottom: i < experiments.length - 1 ? "1px solid rgba(91,138,255,0.06)" : "none",
                cursor: "pointer",
              }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
                    {exp.experiment_name}
                  </div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--text-3)", marginTop: 2 }}>
                    {exp.n_tasks} tasks
                  </div>
                </div>
                <span className="mono" style={{ fontSize: 12, color: "var(--text-2)" }}>{exp.n_runs}</span>
                <div>
                  <span className="mono" style={{
                    fontSize: 12, color: rate > 0.5 ? "var(--green)" : "var(--text-2)",
                    textShadow: rate > 0.5 ? "0 0 10px rgba(0,232,122,0.4)" : "none",
                  }}>
                    {exp.converged}/{exp.n_runs}
                  </span>
                  <div style={{ marginTop: 5, height: 2, width: 44, background: "rgba(255,255,255,0.06)", borderRadius: 1 }}>
                    <div style={{
                      height: "100%", width: `${rate * 100}%`, borderRadius: 1,
                      background: rate > 0.5 ? "var(--green)" : "var(--amber)",
                      boxShadow: `0 0 6px ${rate > 0.5 ? "rgba(0,232,122,0.6)" : "rgba(255,176,32,0.5)"}`,
                    }} />
                  </div>
                </div>
                <span className="mono" style={{
                  fontSize: 12, color: scoreColor(exp.avg_final_score),
                  textShadow: `0 0 10px ${scoreColor(exp.avg_final_score)}60`,
                }}>
                  {(exp.avg_final_score * 100).toFixed(0)}%
                </span>
                <span className="mono" style={{
                  fontSize: 12,
                  color: apCount > 0 ? "var(--amber)" : "var(--text-3)",
                  textShadow: apCount > 0 ? "0 0 8px rgba(255,176,32,0.4)" : "none",
                }}>
                  {apCount || "—"}
                </span>
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

/* ── Page ── */
export default function Home() {
  const [metrics,     setMetrics]     = useState<AggregateMetrics | null>(null)
  const [experiments, setExperiments] = useState<ExperimentSummary[] | null>(null)

  useEffect(() => {
    fetch("http://localhost:8000/api/metrics/aggregate")
      .then(r => r.json()).then(setMetrics).catch(() => {})
    fetch("http://localhost:8000/api/experiments")
      .then(r => r.json()).then(setExperiments).catch(() => setExperiments([]))
  }, [])

  const apTotal = metrics
    ? Object.values(metrics.antipattern_breakdown).reduce((a, b) => a + b, 0)
    : 0

  return (
    <main style={{ maxWidth: 860, margin: "0 auto", padding: "64px 28px 120px" }}>

      {/* ── Hero ── */}
      <div style={{ marginBottom: 52 }}>
        <div className="mono" style={{
          fontSize: 10, letterSpacing: "0.2em", textTransform: "uppercase",
          color: "var(--accent)", marginBottom: 20, opacity: 0.8,
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <span style={{
            display: "inline-block", width: 6, height: 6, borderRadius: "50%",
            background: "var(--accent)", boxShadow: "0 0 8px var(--accent)",
          }} />
          Feedback-Driven Agent Optimizer
        </div>

        <h1 className="grad-text" style={{
          fontSize: 52, fontWeight: 900,
          letterSpacing: "-0.05em", lineHeight: 1.0,
          marginBottom: 24, maxWidth: 620,
        }}>
          LLMs that learn<br />without training
        </h1>

        <p style={{ fontSize: 15, color: "var(--text-2)", lineHeight: 1.75, maxWidth: 500, marginBottom: 40 }}>
          FDAO proves that a model can improve its task performance purely through
          structured reward signals and in-context reflection —{" "}
          <span style={{ color: "var(--text)" }}>zero gradient steps.</span>
        </p>

        <LoopDiagram />
      </div>

      {/* ── Live runner ── */}
      <div style={{ marginBottom: 72 }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 10, marginBottom: 20,
        }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, color: "var(--text)", letterSpacing: "-0.01em" }}>
            Try it live
          </h2>
          <span className="mono" style={{
            fontSize: 9, color: "var(--green)", border: "1px solid rgba(0,232,122,0.2)",
            background: "rgba(0,232,122,0.06)", borderRadius: 4, padding: "2px 7px",
            letterSpacing: "0.08em", textTransform: "uppercase",
          }}>
            streaming
          </span>
        </div>
        <LiveRun />
      </div>

      {/* ── Divider ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 28 }}>
        <div style={{ flex: 1, height: 1, background: "linear-gradient(90deg, transparent, rgba(91,138,255,0.15))" }} />
        <span className="mono" style={{
          fontSize: 9, textTransform: "uppercase", letterSpacing: "0.18em", color: "var(--text-3)",
        }}>
          research metrics
        </span>
        <div style={{ flex: 1, height: 1, background: "linear-gradient(90deg, rgba(91,138,255,0.15), transparent)" }} />
      </div>

      {/* ── Stats ── */}
      <div style={{ display: "flex", gap: 12, marginBottom: 52, flexWrap: "wrap" }}>
        {metrics ? (
          <>
            <StatCard label="total runs"     value={String(metrics.total_runs)}                              sub={`across ${metrics.total_steps} steps`}  color="#5b8aff" />
            <StatCard label="convergence"    value={`${(metrics.overall_convergence_rate*100).toFixed(0)}%`} sub="tasks solved"                           color="#00e87a" />
            <StatCard label="avg final score" value={`${(metrics.avg_final_score*100).toFixed(0)}%`}         sub="reward at convergence"                  color="#b06aff" />
            <StatCard label="anti-patterns"  value={String(apTotal)}                                         sub="detected & logged"                      color={apTotal > 0 ? "#ffb020" : "#3a4470"} />
          </>
        ) : (
          [0,1,2,3].map(i => <StatCardSk key={i} />)
        )}
      </div>

      {/* ── Experiments ── */}
      <ExperimentsTable experiments={experiments} />

    </main>
  )
}
