const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface RunStep {
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
  reflection_parse_failed: boolean
  reflection_quality: number | null
  antipattern: string
  timestamp: string
}

export interface RunSummary {
  run_id: string
  task_id: string
  experiment_name: string
  n_iterations: number
  final_score: number
  converged: boolean
  reward_hacked_count: number
  antipattern_count: number
  timestamp: string
}

export interface RunDetail extends Omit<RunSummary, "n_iterations" | "reward_hacked_count" | "antipattern_count"> {
  steps: RunStep[]
}

export interface ExperimentSummary {
  experiment_name: string
  n_runs: number
  n_tasks: number
  converged: number
  avg_final_score: number
  avg_reflection_quality: number | null
  reward_hacked_total: number
  antipattern_breakdown: Record<string, number>
}

export interface AggregateMetrics {
  total_runs: number
  total_steps: number
  overall_convergence_rate: number
  avg_final_score: number
  avg_reflection_quality: number | null
  parse_failure_rate: number
  reward_hacking_rate: number
  antipattern_breakdown: Record<string, number>
}

export interface TaskInfo {
  task_id: string
  category: string
  difficulty: string
  description: string
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate: 0 } })
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

export const api = {
  runs:          () => get<RunSummary[]>("/api/runs"),
  run:           (id: string) => get<RunDetail>(`/api/runs/${id}`),
  runSteps:      (id: string) => get<RunStep[]>(`/api/runs/${id}/steps`),
  experiments:   () => get<ExperimentSummary[]>("/api/experiments"),
  experiment:    (name: string) => get<RunSummary[]>(`/api/experiments/${encodeURIComponent(name)}`),
  metrics:       () => get<AggregateMetrics>("/api/metrics/aggregate"),
  taskLibrary:   () => get<TaskInfo[]>("/api/tasks/library"),
}
