export type Envelope<T> = {
  request_id: string;
  status: "success" | "error";
  data: T;
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    retryable: boolean;
  } | null;
};

export type RunSummary = {
  run_id: string;
  trace_id: string;
  app_id: string;
  environment: string;
  status: string;
  source_type: string;
  source_run_id: string | null;
  started_at_utc: string;
  ended_at_utc: string | null;
  retention_class: string;
};

export type EventView = {
  event_id: string;
  run_id: string;
  step_id: string;
  sequence_no: number;
  event_type: string;
  timestamp_utc: string;
  determinism_mode: string;
  redaction_status: string;
  payload: Record<string, unknown>;
};

export type ReplayStatus = {
  replay_session_id: string;
  status: string;
  derived_run_id: string | null;
  reason_codes: string[];
  failure_reason_code: string | null;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "content-type": "application/json",
    },
    ...init,
  });
  const payload: Envelope<T> = await response.json();
  if (!response.ok || payload.status === "error") {
    throw new Error(payload.error?.message ?? "request failed");
  }
  return payload.data;
}

export function listRuns() {
  return request<{ items: RunSummary[]; next_page_token: string | null }>("/api/v1/runs");
}

export function getRun(runId: string) {
  return request<{ run: RunSummary; counters: Record<string, number> }>(`/api/v1/runs/${runId}`);
}

export function listRunEvents(runId: string) {
  return request<{ items: EventView[]; next_page_token: string | null }>(`/api/v1/runs/${runId}/events`);
}

export function createReplay(input: {
  source_run_id: string;
  fork_step_id?: string;
  override_profile: Record<string, unknown>;
}) {
  return request<{ replay_session_id: string; status: string }>("/api/v1/replays", {
    method: "POST",
    body: JSON.stringify({
      source_run_id: input.source_run_id,
      fork_step_id: input.fork_step_id,
      override_profile: input.override_profile,
      replay_preferences: {
        preferred_modes: ["exact", "cached", "simulated"],
        fail_on_simulated: false,
      },
    }),
  });
}

export function getReplayStatus(replaySessionId: string) {
  return request<ReplayStatus>(`/api/v1/replays/${replaySessionId}`);
}
