import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { createReplay, getRun, listRunEvents } from "../api";

const modeColor: Record<string, string> = {
  live: "live",
  exact: "exact",
  cached: "cached",
  simulated: "simulated",
};

export function RunDetailPage() {
  const { runId = "" } = useParams();
  const navigate = useNavigate();

  const runQuery = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId),
  });

  const eventsQuery = useQuery({
    queryKey: ["events", runId],
    queryFn: () => listRunEvents(runId),
    refetchInterval: 5000,
  });

  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [forkStepId, setForkStepId] = useState("");
  const [promptTemplateId, setPromptTemplateId] = useState("");
  const [promptTemplateVersion, setPromptTemplateVersion] = useState("");
  const [modelProvider, setModelProvider] = useState("");
  const [modelId, setModelId] = useState("");
  const [retrieverTopK, setRetrieverTopK] = useState("");

  const selectedEvent = useMemo(() => {
    const items = eventsQuery.data?.items ?? [];
    if (!items.length) {
      return null;
    }
    if (!selectedEventId) {
      return items[0];
    }
    return items.find((item) => item.event_id === selectedEventId) ?? items[0];
  }, [eventsQuery.data, selectedEventId]);

  const replayMutation = useMutation({
    mutationFn: () =>
      createReplay({
        source_run_id: runId,
        fork_step_id: forkStepId || undefined,
        override_profile: {
          prompt_override:
            promptTemplateId || promptTemplateVersion
              ? {
                  template_id: promptTemplateId || undefined,
                  template_version: promptTemplateVersion || undefined,
                }
              : undefined,
          model_override:
            modelProvider || modelId
              ? {
                  provider: modelProvider || undefined,
                  model_id: modelId || undefined,
                }
              : undefined,
          retriever_override:
            retrieverTopK
              ? {
                  top_k: Number(retrieverTopK),
                }
              : undefined,
        },
      }),
    onSuccess: (result) => {
      navigate(`/replays/${result.replay_session_id}`);
    },
  });

  const canReplay = Boolean(runId);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    replayMutation.mutate();
  }

  return (
    <section className="cockpit">
      <aside className="panel timeline-panel" aria-label="Timeline panel">
        <h2>Timeline</h2>
        <div className="timeline-list" role="list" tabIndex={0}>
          {(eventsQuery.data?.items ?? []).map((evt) => (
            <button
              key={evt.event_id}
              type="button"
              role="listitem"
              className={`timeline-item ${selectedEvent?.event_id === evt.event_id ? "selected" : ""}`}
              onClick={() => {
                setSelectedEventId(evt.event_id);
                setForkStepId(evt.step_id);
              }}
            >
              <span className={`mode-dot ${modeColor[evt.determinism_mode] ?? "live"}`} />
              <strong>{evt.sequence_no}</strong>
              <span>{evt.event_type}</span>
            </button>
          ))}
        </div>
      </aside>

      <article className="panel inspector-panel" aria-label="Step inspector">
        <h2>Step Inspector</h2>
        {runQuery.data ? (
          <div className="meta-block">
            <h3>Run</h3>
            <p>
              <code>{runQuery.data.run.run_id}</code>
            </p>
            <p>Status: {runQuery.data.run.status}</p>
          </div>
        ) : null}

        {selectedEvent ? (
          <div className="meta-block">
            <h3>{selectedEvent.event_type}</h3>
            <p>Step: {selectedEvent.step_id}</p>
            <p>Mode: {selectedEvent.determinism_mode}</p>
            <p>Redaction: {selectedEvent.redaction_status}</p>
            <pre>{JSON.stringify(selectedEvent.payload, null, 2)}</pre>
          </div>
        ) : (
          <p>No events yet.</p>
        )}
      </article>

      <aside className="panel fork-panel" aria-label="Fork configuration panel">
        <h2>Fork + Replay</h2>
        <form onSubmit={onSubmit} className="fork-form">
          <label>
            Fork Step ID
            <input
              value={forkStepId}
              onChange={(event) => setForkStepId(event.target.value)}
              placeholder="step_id"
            />
          </label>
          <label>
            Prompt Template ID
            <input
              value={promptTemplateId}
              onChange={(event) => setPromptTemplateId(event.target.value)}
              placeholder="new template"
            />
          </label>
          <label>
            Prompt Template Version
            <input
              value={promptTemplateVersion}
              onChange={(event) => setPromptTemplateVersion(event.target.value)}
              placeholder="v2"
            />
          </label>
          <label>
            Model Provider
            <input
              value={modelProvider}
              onChange={(event) => setModelProvider(event.target.value)}
              placeholder="openai"
            />
          </label>
          <label>
            Model ID
            <input
              value={modelId}
              onChange={(event) => setModelId(event.target.value)}
              placeholder="gpt-4.1"
            />
          </label>
          <label>
            Retriever Top-K
            <input
              value={retrieverTopK}
              onChange={(event) => setRetrieverTopK(event.target.value)}
              placeholder="10"
              inputMode="numeric"
            />
          </label>

          <button type="submit" disabled={!canReplay || replayMutation.isPending}>
            {replayMutation.isPending ? "Starting replay..." : "Start replay"}
          </button>
        </form>

        {replayMutation.error ? <p className="error">Replay request failed.</p> : null}
      </aside>
    </section>
  );
}
