import { useMemo, useState } from "react";
import { useFeed } from "../FeedContext";
import FeedRow from "../components/FeedRow";
import AlertDetailPanel from "../components/AlertDetailPanel";

export default function LiveFeed() {
  const { items, isPolling, setIsPolling, intervalSeconds, setIntervalSeconds, connectionError, queueExhausted } = useFeed();
  const [selected, setSelected] = useState(null);

  const falsePositiveReview = useMemo(
    () => items.filter((i) => i.kind === "alert" && i.reasoning_status === "complete" && i.agent_verdict === "false_positive"),
    [items]
  );

  return (
    <div className="p-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Live Feed</h1>
          <p className="text-sm text-text-secondary mt-1">
            Simulated traffic classified live by the RF model. Flagged traffic escalates to the LLM agent.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs text-text-secondary font-mono flex items-center gap-2">
            interval
            <select
              value={intervalSeconds}
              onChange={(e) => setIntervalSeconds(Number(e.target.value))}
              className="bg-panel-raised border border-hairline rounded px-2 py-1 text-text-primary font-mono text-xs"
            >
              {[2, 3, 4, 5, 8, 10].map((s) => (
                <option key={s} value={s}>
                  {s}s
                </option>
              ))}
            </select>
          </label>

          <button
            onClick={() => setIsPolling((p) => !p)}
            className={`px-3 py-1.5 rounded border text-xs font-mono transition-colors ${
              isPolling
                ? "border-signal-truepositive/40 text-signal-truepositive hover:bg-signal-truepositive/10"
                : "border-signal-benign/40 text-signal-benign hover:bg-signal-benign/10"
            }`}
          >
            {isPolling ? "pause feed" : "resume feed"}
          </button>
        </div>
      </div>

      {connectionError && (
        <div className="mb-4 px-4 py-3 rounded border border-signal-truepositive/40 bg-signal-truepositive/10 text-sm text-signal-truepositive">
          Can't reach the backend ({connectionError}). Confirm Flask is running on the expected port.
        </div>
      )}

      {queueExhausted && !connectionError && (
        <div className="mb-4 px-4 py-3 rounded border border-signal-neutral/40 bg-signal-neutral/10 text-sm text-text-secondary">
          Traffic queue exhausted — re-run the training script to generate a fresh live_traffic_sample.csv, or restart the backend.
        </div>
      )}

      <div className="rounded border border-hairline bg-panel overflow-hidden mb-10">
        <div className="flex items-center gap-4 px-4 py-2 border-b border-hairline text-[11px] uppercase tracking-wider text-text-secondary">
          <span className="w-36">timestamp</span>
          <span className="w-32">source ip</span>
          <span className="w-16">port</span>
          <span className="w-14">proto</span>
          <span className="w-32">label</span>
          <span className="w-16">conf.</span>
          <span className="ml-auto">status</span>
        </div>
        <div className="max-h-[520px] overflow-y-auto">
          {items.length === 0 ? (
            <div className="px-4 py-10 text-center text-sm text-text-secondary">
              Waiting for the first classified row...
            </div>
          ) : (
            items.map((item) => <FeedRow key={item.key} item={item} onSelect={setSelected} />)
          )}
        </div>
      </div>

      <div>
        <h2 className="text-sm uppercase tracking-wider text-text-secondary mb-3">
          Review queue — AI-reasoned false positives ({falsePositiveReview.length})
        </h2>
        <div className="rounded border border-hairline bg-panel overflow-hidden">
          {falsePositiveReview.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-text-secondary">No false positives resolved yet.</div>
          ) : (
            falsePositiveReview.map((item) => (
              <div
                key={`review-${item.key}`}
                onClick={() => setSelected(item)}
                className="flex items-center gap-4 px-4 py-2.5 border-b border-hairline last:border-b-0 cursor-pointer hover:bg-panel-raised"
              >
                <span className="font-mono text-xs text-text-secondary w-36 shrink-0">{item.timestamp}</span>
                <span className="font-mono text-sm w-32 shrink-0">{item.src_ip}</span>
                <span className="font-mono text-sm w-32 shrink-0 truncate">{item.label}</span>
                <span className="text-sm text-text-secondary truncate">{item.agent_reasoning}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <AlertDetailPanel item={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
