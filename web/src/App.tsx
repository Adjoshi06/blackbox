import { Link, Route, Routes } from "react-router-dom";
import { ReplayPage } from "./pages/ReplayPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { RunListPage } from "./pages/RunListPage";

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Flight Recorder Cockpit</h1>
          <p>Trace timelines, fork runs, and inspect deterministic replay paths.</p>
        </div>
        <nav>
          <Link to="/">Runs</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<RunListPage />} />
          <Route path="/runs/:runId" element={<RunDetailPage />} />
          <Route path="/replays/:replayId" element={<ReplayPage />} />
        </Routes>
      </main>
    </div>
  );
}
