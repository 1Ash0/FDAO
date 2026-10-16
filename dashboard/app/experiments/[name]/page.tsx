"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import Link from "next/link"
import { ScoreBar } from "@/components/ScoreBar"
import type { RunSummary } from "@/lib/api"

function Sk({ w, h = 12 }: { w: number | string; h?: number }) {
  return <div className="skeleton" style={{ width: w, height: h }} />
}

export default function ExperimentPage() {
  const { name } = useParams<{ name: string }>()
  const expName   = decodeURIComponent(name)
  const [runs, setRuns] = useState<RunSummary[] | null>(null)

  useEffect(() => {
    fetch(`http://localhost:8000/api/experiments/${encodeURIComponent(expName)}`)
      .then(r => r.json()).then(setRuns).catch(() => setRuns([]))
  }, [expName])

  const converged = runs?.filter(r => r.converged).length ?? 0
  const avgScore  = runs?.length ? runs.reduce((s, r) => s + r.final_score, 0) / runs.length : 0

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "32px 24px 80px" }}>

      {/* breadcrumb */}
      <div className="mono" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-3)", marginBottom: 28 }}>
        <Link href="/experiments" style={{ color: "var(--text-3)", textDecoration: "none" }}>experiments</Link>
        <span>/</span>
        <span style={{ color: "var(--text-2)" }}>{expName}</span>
      </div>

      {/* header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.03em", color: "var(--text)", marginBottom: 16 }}>
          {expName}
        </h1>
        <div style={{ display: "flex", gap: 32 }}>
          {runs ? [
            { label: "runs",      value: String(runs.length) },
            { label: "converged", value: `${converged}/${runs.length}` },
            { label: "avg score", value: `${(avgScore * 100).toFixed(1)}%` },
          ].map(({ label, value }) => (
            <div key={label}>
              <div className="mono" style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-3)", marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.03em", color: "var(--text)" }}>{value}</div>
            </div>
          )) : (
            [72, 56, 64].map((w, i) => (
              <div key={i}><Sk w={40} h={8} /><div style={{ marginTop: 6 }}><Sk w={w} h={18} /></div></div>
            ))
          )}
        </div>
      </div>

      {/* runs table */}
      <div style={{ border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden" }}>
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 180px 56px 140px 100px 120px",
          padding: "8px 16px", background: "var(--surface-2)", borderBottom: "1px solid var(--border)",
        }}>
          {["task", "run id", "iters", "final score", "status", "anti-patterns"].map(h => (
            <span key={h} className="mono" style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-3)" }}>{h}</span>
          ))}
        </div>

        {!runs && [1,2,3].map(i => (
          <div key={i} style={{ display: "flex", gap: 16, padding: "13px 16px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
            <Sk w="25%" /><Sk w={96} /><Sk w={24} /><Sk w={100} /><Sk w={64} /><Sk w={80} />
          </div>
        ))}

        {runs?.length === 0 && (
          <div style={{ padding: "32px 16px", textAlign: "center" }}>
            <p className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>No runs found for this experiment.</p>
          </div>
        )}

        {runs?.map((run, i) => (
          <Link key={run.run_id} href={`/runs/${run.run_id}`} style={{ textDecoration: "none", display: "block" }}>
            <div className="trow" style={{
              display: "grid", gridTemplateColumns: "1fr 180px 56px 140px 100px 120px",
              padding: "11px 16px", alignItems: "center",
              borderBottom: i < runs.length - 1 ? "1px solid var(--border)" : "none",
              cursor: "pointer",
            }}>
              <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text)" }}>{run.task_id}</span>
              <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>{run.run_id.slice(0, 14)}…</span>
              <span className="mono" style={{ fontSize: 12, color: "var(--text-2)" }}>{run.n_iterations}</span>
              <ScoreBar value={run.final_score} size="sm" />
              <span className="mono" style={{ fontSize: 11, color: run.converged ? "var(--green)" : "var(--text-3)" }}>
                {run.converged ? "converged" : "open"}
              </span>
              <span className="mono" style={{ fontSize: 11, color: run.antipattern_count > 0 ? "var(--amber)" : "var(--text-3)" }}>
                {run.antipattern_count > 0 ? `${run.antipattern_count} detected` : "—"}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </main>
  )
}
