import StatusPill from "./StatusPill";

export default function AlertDetailPanel({ item, onClose }) {
  if (!item) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-full max-w-md h-full bg-panel border-l border-hairline p-6 overflow-y-auto animate-slide-in">
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="text-xs text-text-secondary font-mono mb-1">ALERT #{item.id}</div>
            <div className="text-lg font-semibold">{item.label}</div>
          </div>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary text-sm font-mono px-2 py-1 rounded hover:bg-panel-raised"
          >
            close
          </button>
        </div>

        <div className="mb-5">
          <StatusPill item={item} />
        </div>

        <dl className="space-y-3 text-sm mb-6">
          <Row label="Source IP" value={item.src_ip} mono />
          <Row label="Destination port" value={`:${item.dst_port}`} mono />
          <Row label="Protocol" value={item.protocol} mono />
          <Row label="Detected label" value={item.label} mono />
          <Row label="Confidence" value={`${(item.confidence * 100).toFixed(1)}%`} mono />
          <Row label="Timestamp" value={item.timestamp} mono />
        </dl>

        <div className="border-t border-hairline pt-5">
          <div className="text-xs uppercase tracking-wider text-text-secondary mb-2">Agent reasoning</div>
          {item.reasoning_status === "reasoning" ? (
            <div className="text-sm text-text-secondary font-mono flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-signal-reasoning animate-pulse-dot" />
              triaging against organisational context...
            </div>
          ) : (
            <p className="text-sm leading-relaxed text-text-primary whitespace-pre-wrap">
              {item.agent_reasoning || "No reasoning recorded."}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, mono }) {
  return (
    <div className="flex justify-between items-center">
      <dt className="text-text-secondary">{label}</dt>
      <dd className={mono ? "font-mono" : ""}>{value}</dd>
    </div>
  );
}
