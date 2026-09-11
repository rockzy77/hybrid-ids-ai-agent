import { useEffect, useState } from "react";
import { api } from "../api";
import StatusPill from "../components/StatusPill";
import AlertDetailPanel from "../components/AlertDetailPanel";

export default function AlertsTable() {
  const [alerts, setAlerts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all"); // all | true_positive | false_positive | reasoning

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await api.getAlerts();
        if (!cancelled) {
          setAlerts(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    };
    load();
    const timer = setInterval(load, 3000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const filtered = alerts.filter((a) => {
    if (filter === "all") return true;
    if (filter === "reasoning") return a.reasoning_status === "reasoning";
    return a.reasoning_status === "complete" && a.agent_verdict === filter;
  });

  return (
    <div className="p-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Alerts</h1>
          <p className="text-sm text-text-secondary mt-1">Every alert the RF model has flagged, newest first.</p>
        </div>

        <div className="flex gap-2">
          {[
            ["all", "All"],
            ["reasoning", "Reasoning"],
            ["true_positive", "Investigate"],
            ["false_positive", "False positive"],
          ].map(([value, label]) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`px-3 py-1.5 rounded border text-xs font-mono transition-colors ${
                filter === value
                  ? "border-signal-reasoning/50 text-signal-reasoning bg-signal-reasoning/10"
                  : "border-hairline text-text-secondary hover:text-text-primary"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded border border-signal-truepositive/40 bg-signal-truepositive/10 text-sm text-signal-truepositive">
          Can't reach the backend ({error}).
        </div>
      )}

      <div className="rounded border border-hairline bg-panel overflow-hidden">
        <div className="grid grid-cols-[140px_120px_110px_90px_130px_1fr_110px] gap-4 px-4 py-2 border-b border-hairline text-[11px] uppercase tracking-wider text-text-secondary">
          <span>timestamp</span>
          <span>src ip</span>
          <span>label</span>
          <span>conf.</span>
          <span>status</span>
          <span>reasoning</span>
          <span></span>
        </div>

        {filtered.length === 0 ? (
          <div className="px-4 py-10 text-center text-sm text-text-secondary">No alerts match this filter.</div>
        ) : (
          filtered.map((a) => {
            const isFalsePositive = a.reasoning_status === "complete" && a.agent_verdict === "false_positive";
            const isTruePositive = a.reasoning_status === "complete" && a.agent_verdict === "true_positive";
            return (
              <div
                key={a.id}
                onClick={() => setSelected(a)}
                className={`grid grid-cols-[140px_120px_110px_90px_130px_1fr_110px] gap-4 px-4 py-2.5 border-b border-hairline last:border-b-0 cursor-pointer hover:bg-panel-raised text-sm
                  ${isFalsePositive ? "bg-signal-falsepositive/10" : ""}
                  ${isTruePositive ? "bg-signal-truepositive/5" : ""}
                `}
              >
                <span className="font-mono text-xs text-text-secondary">{a.timestamp}</span>
                <span className="font-mono">{a.src_ip}</span>
                <span className="font-mono text-xs">{a.label}</span>
                <span className="font-mono text-xs text-text-secondary">{(a.confidence * 100).toFixed(0)}%</span>
                <span>
                  <StatusPill item={a} />
                </span>
                <span className="text-text-secondary truncate">{a.agent_reasoning || "—"}</span>
                <span className="text-text-secondary text-xs font-mono">view →</span>
              </div>
            );
          })
        )}
      </div>

      <AlertDetailPanel item={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
