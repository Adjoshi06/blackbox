import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { getReplayStatus } from "../api";

export function ReplayPage() {
  const { replayId = "" } = useParams();
  const statusQuery = useQuery({
    queryKey: ["replay", replayId],
    queryFn: () => getReplayStatus(replayId),
    refetchInterval: 1500,
  });

  const status = statusQuery.data;

  return (
    <section className="panel replay-panel">
      <h2>Replay Session</h2>
      {statusQuery.isLoading ? <p>Loading replay status...</p> : null}
      {statusQuery.error ? <p className="error">Failed to load replay session.</p> : null}
      {status ? (
        <div className="meta-block">
          <p>
            Session: <code>{status.replay_session_id}</code>
          </p>
          <p>Status: {status.status}</p>
          <p>Reason codes: {status.reason_codes.join(", ") || "none"}</p>
          {status.failure_reason_code ? <p>Failure reason: {status.failure_reason_code}</p> : null}
          {status.derived_run_id ? (
            <p>
              Derived run: <Link to={`/runs/${status.derived_run_id}`}>{status.derived_run_id}</Link>
            </p>
          ) : null}
        </div>
      ) : null}
      <Link to="/">Back to runs</Link>
    </section>
  );
}
