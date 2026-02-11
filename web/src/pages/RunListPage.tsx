import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listRuns } from "../api";

export function RunListPage() {
  const [query, setQuery] = useState("");
  const runsQuery = useQuery({
    queryKey: ["runs"],
    queryFn: listRuns,
    refetchInterval: 5000,
  });

  const rows = useMemo(() => {
    const items = runsQuery.data?.items ?? [];
    const search = query.trim().toLowerCase();
    if (!search) {
      return items;
    }
    return items.filter(
      (item) => item.run_id.toLowerCase().includes(search) || item.trace_id.toLowerCase().includes(search),
    );
  }, [runsQuery.data, query]);

  return (
    <section className="panel run-list-panel">
      <div className="toolbar">
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search run_id or trace_id"
          aria-label="Search runs"
        />
      </div>

      {runsQuery.isLoading ? <p>Loading runs...</p> : null}
      {runsQuery.error ? <p className="error">Failed to load runs.</p> : null}

      <div className="run-table" role="list">
        {rows.map((run) => (
          <article key={run.run_id} className="run-row" role="listitem">
            <div>
              <h3>{run.app_id}</h3>
              <p>{run.environment}</p>
              <code>{run.run_id}</code>
            </div>
            <div>
              <span className={`badge badge-${run.status}`}>{run.status}</span>
              <p>{new Date(run.started_at_utc).toLocaleString()}</p>
            </div>
            <div className="actions">
              <Link to={`/runs/${run.run_id}`}>Open</Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
