"use client"

import { useState } from "react"

interface StepEvent {
  iteration: number
  attempt: string
  score_composite: number
  score_breakdown: Record<string, number>
  reward_hacked: boolean
  reflection: {
    failure_type: string
    root_cause: string
    what_worked: string
    strategy_update: string
    confidence: string
  } | null
  antipattern: string
  converged: boolean
}

const FT_LABEL: Record<string, string> = {
  logic_error: "logic", format_error: "format", misunderstanding: "intent",
  overcomplication: "overfit", partial_solution: "partial", tool_misuse: "tool",
}
const FT_COLOR: Record<string, string> = {
  logic_error: "#5b8aff", format_error: "#ffb020", misunderstanding: "#b06aff",
  overcomplication: "#ff6b6b", partial_solution: "#00e87a", tool_misuse: "#8892c8",
}
const AP_COLOR: Record<string, string> = {
  circular: "#ffb020", overcorrect: "#ff4d6a", drift: "#b06aff",
}
const CONF_COLOR: Record<string, string> = {
  high: "#00e87a", medium: "#ffb020", low: "#8892c8",
}

function scoreColor(v: number) {
  if (v >= 0.9) return "#00e87a"
  if (v >= 0.65) return "#5b8aff"
  if (v >= 0.35) return "#ffb020"
  return "#ff4d6a"
}

/* ── Score trajectory sparkline ── */
function Trajectory({ steps }: { steps: StepEvent[] }) {
  if (steps.length < 2) return null
  const W = 260, H = 52, PAD = 10
  const scores = steps.map(s => s.score_composite)
  const max = Math.max(...scores, 0.3)
  const pts = scores.map((s, i) => {
    const x = PAD + (i / Math.max(scores.length - 1, 1)) * (W - PAD * 2)
    const y = H - PAD - (s / max) * (H - PAD * 2)
    return [x, y] as [number, number]
  })
  const lastPt = pts[pts.length - 1]
  const lastScore = scores[scores.length - 1]
  const c = scoreColor(lastScore)
  const ptStr = pts.map(([x, y]) => `${x},${y}`).join(" ")

  return (
    <div style={{
      background: "rgba(6,8,18,0.85)", border: "1px solid rgba(91,138,255,0.12)",
      borderRadius: 10, padding: "12px 14px", marginBottom: 14,
      display: "flex", alignItems: "center", gap: 20,
    }}>
      <div style={{ flex: 1 }}>
        <div className="mono" style={{
          fontSize: 9, color: "var(--text-3)", letterSpacing: "0.12em",
          marginBottom: 8, textTransform: "uppercase",
        }}>
          Score trajectory
        </div>
        <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: "block", overflow: "visible" }}>
          <defs>
            <linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={c} stopOpacity="0.28" />
              <stop offset="100%" stopColor={c} stopOpacity="0" />
            </linearGradient>
          </defs>
          <polygon
            points={`${PAD},${H - PAD} ${ptStr} ${W - PAD},${H - PAD}`}
            fill="url(#tg)"
          />
          <polyline points={ptStr} fill="none" stroke={c} strokeWidth={2}
            strokeLinejoin="round" strokeLinecap="round" />
          {pts.map(([x, y], i) => {
            const dc = scoreColor(scores[i])
            return (
              <g key={i}>
                <circle cx={x} cy={y} r={4} fill={dc} />
                <circle cx={x} cy={y} r={7} fill={dc} fillOpacity={0.15} />
                <text x={x} y={y - 9} textAnchor="middle"
                  fontSize={8} fill={dc} fontFamily="var(--font-geist-mono)" fontWeight={700}>
                  {(scores[i] * 100).toFixed(0)}%
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      {/* deltas column */}
      <div style={{ display: "flex", flexDirection: "column", gap: 5, flexShrink: 0 }}>
        {steps.map((s, i) => {
          const prev = i > 0 ? steps[i - 1].score_composite : null
          const delta = prev !== null ? s.score_composite - prev : null
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className="mono" style={{ fontSize: 10, color: "var(--text-3)", minWidth: 16 }}>i{i}</span>
              <span className="mono" style={{ fontSize: 11, fontWeight: 700, color: scoreColor(s.score_composite), minWidth: 32 }}>
                {(s.score_composite * 100).toFixed(0)}%
              </span>
              {delta !== null && (
                <span className="mono" style={{
                  fontSize: 9,
                  color: delta > 0.005 ? "#00e87a" : delta < -0.005 ? "#ff4d6a" : "var(--text-3)",
                }}>
                  {delta > 0.005 ? `+${(delta * 100).toFixed(0)}` : delta < -0.005 ? (delta * 100).toFixed(0) : "—"}
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── Single iteration card ── */
type Tab = "code" | "score" | "reflect"

function IterCard({ step, idx, prev, isActive, onSelect }: {
  step: StepEvent; idx: number; prev: StepEvent | null
  isActive: boolean; onSelect: () => void
}) {
  const [tab, setTab] = useState<Tab>("code")
  const delta = prev ? step.score_composite - prev.score_composite : null
  const c = scoreColor(step.score_composite)
  const r = step.reflection

  return (
    <div className="fade-in" style={{
      border: `1px solid ${isActive ? `${c}35` : "rgba(91,138,255,0.1)"}`,
      borderRadius: 12, overflow: "hidden", marginBottom: 8,
      background: isActive ? `${c}06` : "rgba(6,8,18,0.7)",
      transition: "border-color 0.2s, background 0.2s",
      backdropFilter: "blur(12px)",
    }}>
      <button onClick={onSelect} style={{
        width: "100%", display: "flex", alignItems: "center", gap: 10,
        padding: "10px 14px", background: "transparent",
        border: "none", cursor: "pointer", textAlign: "left",
        borderBottom: isActive ? `1px solid ${c}20` : "none",
      }}>
        <span style={{
          width: 26, height: 26, borderRadius: 8, flexShrink: 0,
          background: isActive ? `${c}20` : "rgba(255,255,255,0.04)",
          border: `1px solid ${isActive ? `${c}40` : "rgba(255,255,255,0.08)"}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: "var(--font-geist-mono)", fontSize: 10, fontWeight: 700,
          color: isActive ? c : "var(--text-3)",
        }}>
          {idx}
        </span>

        <span className="mono" style={{
          fontSize: 13, fontWeight: 800, color: c,
          textShadow: isActive ? `0 0 16px ${c}80` : "none",
        }}>
          {(step.score_composite * 100).toFixed(0)}%
        </span>

        {delta !== null && Math.abs(delta) > 0.005 && (
          <span className="mono" style={{
            fontSize: 10, fontWeight: 600,
            color: delta > 0 ? "#00e87a" : "#ff4d6a",
            background: delta > 0 ? "rgba(0,232,122,0.10)" : "rgba(255,77,106,0.10)",
            border: `1px solid ${delta > 0 ? "rgba(0,232,122,0.2)" : "rgba(255,77,106,0.2)"}`,
            borderRadius: 4, padding: "1px 6px",
          }}>
            {delta > 0 ? "↑" : "↓"}{Math.abs(delta * 100).toFixed(0)}%
          </span>
        )}

        <div style={{ flex: 1, height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
          <div style={{
            width: `${step.score_composite * 100}%`, height: "100%", borderRadius: 2,
            background: `linear-gradient(90deg, ${c}80, ${c})`,
            boxShadow: isActive ? `0 0 10px ${c}60` : "none",
            transition: "width 0.5s ease",
          }} />
        </div>

        {r && (
          <span className="mono" style={{
            fontSize: 9, padding: "2px 7px", borderRadius: 4, whiteSpace: "nowrap",
            color: FT_COLOR[r.failure_type] ?? "var(--text-3)",
            background: `${FT_COLOR[r.failure_type] ?? "#fff"}10`,
            border: `1px solid ${FT_COLOR[r.failure_type] ?? "#fff"}25`,
          }}>
            {FT_LABEL[r.failure_type] ?? r.failure_type}
          </span>
        )}

        {step.converged && (
          <span className="mono" style={{
            fontSize: 10, color: "#00e87a", whiteSpace: "nowrap",
            textShadow: "0 0 12px rgba(0,232,122,0.7)",
          }}>✓ solved</span>
        )}

        {step.antipattern !== "none" && (
          <span className="mono" style={{
            fontSize: 9, padding: "2px 7px", borderRadius: 4,
            color: AP_COLOR[step.antipattern],
            background: `${AP_COLOR[step.antipattern]}12`,
            border: `1px solid ${AP_COLOR[step.antipattern]}30`,
          }}>
            {step.antipattern}
          </span>
        )}

        <span style={{ color: "var(--text-3)", fontSize: 10, marginLeft: 4 }}>
          {isActive ? "▲" : "▼"}
        </span>
      </button>

      {isActive && (
        <div style={{ padding: "0 14px 14px" }}>
          <div style={{ display: "flex", gap: 2, marginTop: 12, marginBottom: 12 }}>
            {(["code", "score", "reflect"] as Tab[]).map(t => (
              <button key={t} onClick={() => setTab(t)} className="mono" style={{
                fontSize: 10, padding: "4px 12px", borderRadius: 6, border: "none",
                cursor: "pointer", letterSpacing: "0.06em", textTransform: "uppercase",
                background: tab === t ? `${c}18` : "rgba(255,255,255,0.04)",
                color: tab === t ? c : "var(--text-3)",
                borderBottom: tab === t ? `2px solid ${c}` : "2px solid transparent",
                transition: "all 0.15s",
              }}>
                {t}
              </button>
            ))}
          </div>

          {tab === "code" && (
            <div className="mono" style={{
              fontSize: 12, lineHeight: 1.7,
              background: "rgba(4,5,14,0.9)",
              border: "1px solid rgba(91,138,255,0.1)",
              borderRadius: 8, padding: "12px 14px",
              color: "var(--text)", whiteSpace: "pre-wrap", wordBreak: "break-word",
              maxHeight: 280, overflowY: "auto",
            }}>
              {step.attempt.replace(/```python\n?|```/g, "").trim()}
            </div>
          )}

          {tab === "score" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {Object.entries(step.score_breakdown).map(([k, v]) => {
                const bc = scoreColor(v)
                return (
                  <div key={k} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span className="mono" style={{
                      fontSize: 10, color: "var(--text-3)", minWidth: 130, textTransform: "capitalize",
                    }}>
                      {k.replace(/_/g, " ")}
                    </span>
                    <div style={{ flex: 1, height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
                      <div style={{
                        width: `${v * 100}%`, height: "100%", borderRadius: 2,
                        background: `linear-gradient(90deg, ${bc}80, ${bc})`,
                        boxShadow: `0 0 8px ${bc}50`,
                        transition: "width 0.5s ease",
                      }} />
                    </div>
                    <span className="mono" style={{
                      fontSize: 11, fontWeight: 700, color: bc, minWidth: 36, textAlign: "right",
                    }}>
                      {(v * 100).toFixed(0)}%
                    </span>
                  </div>
                )
              })}
              <div style={{
                marginTop: 4, paddingTop: 10,
                borderTop: "1px solid rgba(255,255,255,0.06)",
                display: "flex", alignItems: "center", gap: 10,
              }}>
                <span className="mono" style={{
                  fontSize: 10, color: "var(--text-2)", minWidth: 130, fontWeight: 600,
                }}>composite</span>
                <div style={{ flex: 1, height: 5, background: "rgba(255,255,255,0.06)", borderRadius: 3 }}>
                  <div style={{
                    width: `${step.score_composite * 100}%`, height: "100%", borderRadius: 3,
                    background: `linear-gradient(90deg, ${c}80, ${c})`,
                    boxShadow: `0 0 12px ${c}60`,
                  }} />
                </div>
                <span className="mono" style={{
                  fontSize: 13, fontWeight: 800, color: c, minWidth: 36, textAlign: "right",
                  textShadow: `0 0 12px ${c}60`,
                }}>
                  {(step.score_composite * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          )}

          {tab === "reflect" && (
            r ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <span className="mono" style={{
                    fontSize: 10, padding: "3px 10px", borderRadius: 6,
                    color: FT_COLOR[r.failure_type] ?? "var(--text-2)",
                    background: `${FT_COLOR[r.failure_type] ?? "#fff"}12`,
                    border: `1px solid ${FT_COLOR[r.failure_type] ?? "#fff"}25`,
                  }}>
                    {r.failure_type.replace(/_/g, " ")}
                  </span>
                  <span className="mono" style={{
                    fontSize: 10, padding: "3px 10px", borderRadius: 6,
                    color: CONF_COLOR[r.confidence] ?? "var(--text-3)",
                    background: `${CONF_COLOR[r.confidence] ?? "#fff"}10`,
                    border: `1px solid ${CONF_COLOR[r.confidence] ?? "#fff"}20`,
                  }}>
                    {r.confidence} confidence
                  </span>
                </div>
                <ReflRow icon="✗" label="root cause" value={r.root_cause} color="#ff4d6a" />
                <ReflRow icon="✓" label="what worked" value={r.what_worked} color="#00e87a" />
                <div style={{
                  background: "rgba(91,138,255,0.07)",
                  border: "1px solid rgba(91,138,255,0.18)",
                  borderLeft: "3px solid #5b8aff",
                  borderRadius: "0 8px 8px 0", padding: "10px 14px",
                }}>
                  <div className="mono" style={{
                    fontSize: 9, color: "#5b8aff", textTransform: "uppercase",
                    letterSpacing: "0.12em", marginBottom: 6,
                  }}>→ next strategy</div>
                  <p style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.7, margin: 0 }}>
                    {r.strategy_update}
                  </p>
                </div>
              </div>
            ) : (
              <p className="mono" style={{ fontSize: 11, color: "var(--text-3)", padding: "10px 0" }}>
                No reflection — task solved on first attempt.
              </p>
            )
          )}
        </div>
      )}
    </div>
  )
}

function ReflRow({ icon, label, value, color }: {
  icon: string; label: string; value: string; color: string
}) {
  return (
    <div style={{
      background: "rgba(6,8,18,0.8)", border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 8, padding: "10px 12px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5 }}>
        <span style={{ fontSize: 10, color, fontWeight: 700 }}>{icon}</span>
        <span className="mono" style={{
          fontSize: 9, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.1em",
        }}>{label}</span>
      </div>
      <p style={{ fontSize: 12, color: "var(--text-2)", lineHeight: 1.65, margin: 0 }}>{value}</p>
    </div>
  )
}

function Thinking() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 4px" }}>
      <div style={{ display: "flex", gap: 5 }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 7, height: 7, borderRadius: "50%",
            background: "#5b8aff",
            boxShadow: "0 0 10px rgba(91,138,255,0.9)",
            animation: `dot-blink 1.2s ease-in-out ${i * 0.22}s infinite`,
          }} />
        ))}
      </div>
      <span className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>agent reasoning…</span>
    </div>
  )
}

const selectStyle: React.CSSProperties = {
  fontSize: 11, fontFamily: "var(--font-geist-mono)",
  background: "rgba(6,8,18,0.9)",
  border: "1px solid rgba(91,138,255,0.15)",
  borderRadius: 7, padding: "5px 9px",
  color: "var(--text-2)", outline: "none", cursor: "pointer",
}

export function LiveRun() {
  const [prompt,   setPrompt]   = useState("")
  const [model,    setModel]    = useState("llama-3.3-70b-versatile")
  const [config,   setConfig]   = useState("experiments/dense_reward.yaml")
  const [maxIter,  setMaxIter]  = useState(4)
  const [running,  setRunning]  = useState(false)
  const [thinking, setThinking] = useState(false)
  const [steps,    setSteps]    = useState<StepEvent[]>([])
  const [active,   setActive]   = useState<number | null>(null)
  const [error,    setError]    = useState("")
  const [done,     setDone]     = useState(false)

  function startRun() {
    if (!prompt.trim() || running) return
    setRunning(true); setThinking(true); setSteps([]); setActive(null)
    setDone(false); setError("")

    fetch("http://localhost:8000/api/live", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, model, config, max_iterations: maxIter }),
    }).then(res => {
      const reader  = res.body!.getReader()
      const decoder = new TextDecoder()
      let buf = ""

      function pump() {
        reader.read().then(({ done: sd, value }) => {
          if (sd) { setRunning(false); setThinking(false); setDone(true); return }
          buf += decoder.decode(value, { stream: true })
          const chunks = buf.split("\n\n")
          buf = chunks.pop() ?? ""
          for (const chunk of chunks) {
            const line = chunk.split("\n").find(l => l.startsWith("data: "))
            if (!line) continue
            try {
              const evt = JSON.parse(line.slice(6))
              if (evt.event === "step") {
                setThinking(false)
                setSteps(prev => {
                  const next = [...prev, evt]
                  setActive(next.length - 1)
                  return next
                })
                if (!evt.converged) setThinking(true)
              }
              if (evt.event === "done") {
                setRunning(false); setThinking(false); setDone(true)
              }
            } catch {}
          }
          pump()
        }).catch(() => { setRunning(false); setThinking(false) })
      }
      pump()
    }).catch(() => {
      setError("Could not reach API at localhost:8000.")
      setRunning(false); setThinking(false)
    })
  }

  const converged  = steps.some(s => s.converged)
  const finalScore = steps.length ? steps[steps.length - 1].score_composite : null

  return (
    <div>
      <div className={running ? "grad-border-running" : "grad-border"} style={{ marginBottom: 14 }}>
        <div style={{
          background: "rgba(8,12,22,0.97)", borderRadius: 15,
          backdropFilter: "blur(12px)",
        }}>
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) startRun() }}
            disabled={running}
            placeholder={"Ask anything — math, logic, coding, or open-ended.\nThe agent attempts, gets scored, reflects on failure, and retries.\n\nTry: \"A bat and ball cost $1.10. The bat costs $1.00 more than the ball.\""}
            style={{
              width: "100%", minHeight: 108, resize: "none",
              background: "transparent", border: "none", outline: "none",
              padding: "16px 18px", fontSize: 13.5, color: "var(--text)",
              lineHeight: 1.7, fontFamily: "inherit", caretColor: "#5b8aff",
            }}
          />
          <div style={{
            display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
            padding: "10px 14px",
            borderTop: "1px solid rgba(91,138,255,0.08)",
            background: "rgba(4,5,14,0.7)",
          }}>
            <select value={model} onChange={e => setModel(e.target.value)} disabled={running} style={selectStyle}>
              <option value="llama-3.3-70b-versatile">llama-3.3-70b</option>
              <option value="llama-3.1-8b-instant">llama-3.1-8b (fast)</option>
              <option value="mixtral-8x7b-32768">mixtral-8x7b</option>
            </select>
            <select value={config} onChange={e => setConfig(e.target.value)} disabled={running} style={selectStyle}>
              <option value="experiments/dense_reward.yaml">dense reward</option>
              <option value="experiments/sparse_reward.yaml">sparse reward</option>
              <option value="experiments/correctness_dominant.yaml">correctness-only</option>
            </select>
            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>iters</span>
              {[2, 3, 4, 5].map(n => (
                <button key={n} onClick={() => setMaxIter(n)} disabled={running} style={{
                  width: 26, height: 26, borderRadius: 6,
                  border: `1px solid ${maxIter === n ? "rgba(91,138,255,0.5)" : "rgba(255,255,255,0.07)"}`,
                  background: maxIter === n ? "rgba(91,138,255,0.15)" : "transparent",
                  color: maxIter === n ? "#5b8aff" : "var(--text-3)",
                  fontSize: 11, fontFamily: "var(--font-geist-mono)", cursor: "pointer",
                  boxShadow: maxIter === n ? "0 0 12px rgba(91,138,255,0.25)" : "none",
                  transition: "all 0.15s",
                }}>{n}</button>
              ))}
            </div>
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
              {prompt && !running && (
                <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>⌘↵</span>
              )}
              <button
                onClick={startRun}
                disabled={!prompt.trim() || running}
                className={!prompt.trim() || running ? "" : "btn-primary"}
                style={{
                  height: 32, padding: "0 20px", borderRadius: 8, border: "none",
                  fontSize: 12, fontWeight: 700,
                  ...(!prompt.trim() || running ? {
                    background: "rgba(255,255,255,0.05)",
                    color: "var(--text-3)", cursor: "not-allowed",
                  } : {}),
                }}
              >
                {running ? "running…" : "Run →"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <p className="mono" style={{ fontSize: 11, color: "#ff4d6a", marginBottom: 12 }}>{error}</p>
      )}

      {(steps.length > 0 || thinking) && (
        <div>
          {done && finalScore !== null && (
            <div style={{
              display: "flex", alignItems: "center", gap: 10, marginBottom: 14,
              padding: "10px 14px",
              background: converged ? "rgba(0,232,122,0.06)" : "rgba(91,138,255,0.06)",
              border: `1px solid ${converged ? "rgba(0,232,122,0.2)" : "rgba(91,138,255,0.15)"}`,
              borderRadius: 10,
            }}>
              <span style={{ fontSize: 18, filter: `drop-shadow(0 0 8px ${converged ? "#00e87a" : "#5b8aff"})` }}>
                {converged ? "✓" : "◎"}
              </span>
              <div>
                <div className="mono" style={{ fontSize: 11, fontWeight: 700, color: converged ? "#00e87a" : "#5b8aff" }}>
                  {converged ? "Task solved" : `Best score: ${(finalScore * 100).toFixed(0)}%`}
                </div>
                <div className="mono" style={{ fontSize: 10, color: "var(--text-3)", marginTop: 1 }}>
                  {steps.length} iteration{steps.length !== 1 ? "s" : ""} · {converged ? "converged" : "did not converge"}
                </div>
              </div>
              {steps.some(s => s.antipattern !== "none") && (
                <span className="mono" style={{
                  fontSize: 9, padding: "3px 8px", borderRadius: 5, marginLeft: "auto",
                  color: "#ffb020", border: "1px solid rgba(255,176,32,0.2)",
                  background: "rgba(255,176,32,0.07)",
                }}>
                  anti-patterns detected
                </span>
              )}
            </div>
          )}

          <Trajectory steps={steps} />

          {steps.map((s, i) => (
            <IterCard
              key={i} step={s} idx={i}
              prev={i > 0 ? steps[i - 1] : null}
              isActive={active === i}
              onSelect={() => setActive(active === i ? null : i)}
            />
          ))}
          {thinking && <Thinking />}
        </div>
      )}
    </div>
  )
}
