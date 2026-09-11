import StatusPill from "./StatusPill";

function leftBarColor(item) {
  if (item.kind === "clean") return "bg-signal-benign";
  if (item.reasoning_status === "reasoning") return "bg-signal-reasoning";
  if (item.reasoning_status === "complete") {
    return item.agent_verdict === "true_positive" ? "bg-signal-truepositive" : "bg-signal-falsepositive";
  }
  return "bg-signal-neutral";
}

export default function FeedRow({ item, onSelect }) {
  const isReasoning = item.kind === "alert" && item.reasoning_status === "reasoning";
  const isFalsePositive = item.kind === "alert" && item.reasoning_status === "complete" && item.agent_verdict === "false_positive";
  const label = item.kind === "clean" ? item.predicted_label : item.label;
  const clickable = item.kind === "alert";

  return (
    <div
      onClick={() => clickable && onSelect(item)}
      className={`relative overflow-hidden flex items-center gap-4 px-4 py-2.5 border-b border-hairline animate-slide-in
        ${item.kind === "clean" ? "animate-fade-out opacity-70" : ""}
        ${isFalsePositive ? "bg-signal-falsepositive/10" : "bg-transparent"}
        ${clickable ? "cursor-pointer hover:bg-panel-raised" : ""}
      `}
    >
      <span className={`absolute left-0 top-0 bottom-0 w-1 ${leftBarColor(item)}`} />

      {isReasoning && (
        <span className="pointer-events-none absolute inset-0 overflow-hidden">
          <span className="absolute top-0 bottom-0 w-1/3 bg-gradient-to-r from-transparent via-signal-reasoning/15 to-transparent animate-scan" />
        </span>
      )}

      <span className="font-mono text-xs text-text-secondary w-36 shrink-0">{item.timestamp}</span>
      <span className="font-mono text-sm w-32 shrink-0">{item.src_ip}</span>
      <span className="font-mono text-xs text-text-secondary w-16 shrink-0">:{item.dst_port}</span>
      <span className="font-mono text-xs text-text-secondary w-14 shrink-0">{item.protocol}</span>
      <span className="font-mono text-sm w-32 shrink-0 truncate">{label}</span>
      <span className="font-mono text-xs text-text-secondary w-16 shrink-0">
        {(item.confidence * 100).toFixed(0)}%
      </span>
      <span className="ml-auto">
        <StatusPill item={item} />
      </span>
    </div>
  );
}
