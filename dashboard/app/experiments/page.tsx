"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import type { ExperimentSummary } from "@/lib/api"

function Sk({ w, h = 12 }: { w: number | string; h?: number }) {
  return <div className="skeleton" style={{ width: w, height: h }} />
}

function scoreColor(v: number) {
  if (v >= 0.7) return "var(--green)"
  if (v >= 0.4) return "var(--accent)"
  return "var(--amber)"
}

const AP_COLOR: Record<string, string> = {
  circular: "var(--amber)", overcorrect: "var(--red)", drift: "var(--purple)",
}

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<ExperimentSummary[] | null>(null)

  useEffect(() => {
    fetch("http://localhost:8000/api/experiments")
      .then(r => r.json()).then(setExperiments).catch(() => setExperiments([]))
  }, [])

  const totalRuns     = experiments?.reduce((a, e) => a + e.n_runs, 0) ?? 0
  const totalConverged= experiments?.reduce((a, e) => a + e.converged, 0) ?? 0
  const avgScore      = experiments?.length
    ? experiments.reduce((a, e) => a + e.avg_final_score * e.n_runs, 0) / Math.max(totalRuns, 1)
    : 0

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "40px 24px 80px" }}>

      {/* page header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em", color: "var(--text)", marginBottom: 6 }}>
          Experiments
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.7 }}>
          Each experiment runs the agent loop on a task suite under a fixed reward configuration.
          Compare convergence rates across reward structures to see what signal shapes drives improvement.
        </p>
      </div>

      {/* aggregate row */}
      {experiments && experiments.length > 0 && (
        <div style={{ display: "flex", gap: 32, marginBottom: 32 }}>
          {[
            { label: "experiments",  value: String(experiments.length) },
            { label: "total runs",   value: String(totalRuns) },
            { label: "converged",    value: `${totalConverged}/${totalRuns}` },
            { label: "weighted avg", value: `${(avgScore * 100).toFixed(0)}%` },
          ].map(({ label, value }) => (
            <div key={label}>
              <div className="mono" style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-3)", marginBottom: 4 }}>
                {label}
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.03em", color: "var(--text)" }}>
                {value}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* table */}
      <div style={{ border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden" }}>
        {/* header */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 60px 90px 100px 90px 80px 1fr",
          padding: "9px 16px",
          background: "var(--surface-2)",
          borderBottom: "1px solid var(--border)",
        }}>
          {["experiment", "runs", "converged", "avg score", "refl qual", "hacked", "anti-patterns"].map(h => (
            <span key={h} className="mono" style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-3)" }}>
              {h}
            </span>
          ))}
        </div>

        {/* loading */}
        {!experiments && [1, 2, 3].map(i => (
          <div key={i} style={{ display: "flex", gap: 16, padding: "14px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
            <Sk w="30%" /><Sk w={28} /><Sk w={48} /><Sk w={56} /><Sk w={48} /><Sk w={32} /><Sk w={80} />
          </div>
        ))}

        {/* empty */}
        {experiments?.length === 0 && (
          <div style={{ padding: "40px 16px", textAlign: "center" }}>
            <p className="mono" style={{ fontSize: 12, color: "var(--text-3)" }}>
              No experiments yet.{" "}
              <code style={{ color: "var(--text-2)" }}>python scripts/run_phase3.py</code>
            </p>
          </div>
        )}

        {experiments?.map((exp, i) => {
          const rate    = exp.n_runs > 0 ? exp.converged / exp.n_runs : 0
          const apTotal = Object.values(exp.antipattern_breakdown).reduce((a,b) => a+b, 0)
          return (
            <Link key={exp.experiment_name}
              href={`/experiments/${encodeURIComponent(exp.experiment_name)}`}
              style={{ textDecoration: "none", display: "block" }}>
              <div className="trow" style={{
                display: "grid",
                gridTemplateColumns: "1fr 60px 90px 100px 90px 80px 1fr",
                padding: "12px 16px", alignItems: "center",
                borderBottom: i < experiments.length - 1 ? "1px solid var(--border)" : "none",
                cursor: "pointer",
              }}>
                {/* name */}
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>{exp.experiment_name}</div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--text-3)", marginTop: 2 }}>{exp.n_tasks} tasks</div>
                </div>
                {/* runs */}
                <span className="mono" style={{ fontSize: 12, color: "var(--text-2)" }}>{exp.n_runs}</span>
                {/* converged */}
                <div>
                  <span className="mono" style={{ fontSize: 12, color: rate > 0.5 ? "var(--green)" : "var(--text-2)" }}>
                    {exp.converged}/{exp.n_runs}
                  </span>
                  <div style={{ marginTop: 4, height: 2, width: 48, background: "var(--border-2)", borderRadius: 1 }}>
                    <div style={{ height: "100%", width: `${rate * 100}%`, background: rate > 0.5 ? "var(--green)" : "var(--amber)", borderRadius: 1 }} />
                  </div>
                </div>
                {/* avg score */}
                <span className="mono" style={{ fontSize: 12, color: scoreColor(exp.avg_final_score) }}>
                  {(exp.avg_final_score * 100).toFixed(0)}%
                </span>
                {/* refl quality */}
                <span className="mono" style={{ fontSize: 12, color: "var(--text-2)" }}>
                  {exp.avg_reflection_quality != null ? `${exp.avg_reflection_quality.toFixed(1)}/3` : "—"}
                </span>
                {/* hacked */}
                <span className="mono" style={{ fontSize: 12, color: exp.reward_hacked_total > 0 ? "var(--red)" : "var(--text-3)" }}>
                  {exp.reward_hacked_total > 0 ? exp.reward_hacked_total : "—"}
                </span>
                {/* anti-patterns */}
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {Object.keys(exp.antipattern_breakdown).length === 0
                    ? <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>—</span>
                    : Object.entries(exp.antipattern_breakdown).map(([ap, n]) => (
                        <span key={ap} className="mono" style={{
                          fontSize: 10, padding: "2px 6px", borderRadius: 4,
                          background: `${AP_COLOR[ap] ?? "var(--text-3)"}18`,
                          color: AP_COLOR[ap] ?? "var(--text-2)",
                          border: `1px solid ${AP_COLOR[ap] ?? "var(--border-2)"}40`,
                        }}>
                          {ap} {n}
                        </span>
                      ))
                  }
                </div>
              </div>
            </Link>
          )
        })}
      </div>
    </main>
  )
}
