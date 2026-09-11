const STYLES = {
  reasoning: "text-signal-reasoning border-signal-reasoning/40 bg-signal-reasoning/10",
  complete_true_positive: "text-signal-truepositive border-signal-truepositive/40 bg-signal-truepositive/10",
  complete_false_positive: "text-signal-falsepositive border-signal-falsepositive/40 bg-signal-falsepositive/10",
  clean: "text-signal-benign border-signal-benign/40 bg-signal-benign/10",
  neutral: "text-signal-neutral border-signal-neutral/40 bg-signal-neutral/10",
};

export default function StatusPill({ item }) {
  if (item.kind === "clean") {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[11px] font-mono ${STYLES.clean}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-signal-benign" />
        clean
      </span>
    );
  }

  if (item.reasoning_status === "reasoning") {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[11px] font-mono ${STYLES.reasoning}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-signal-reasoning animate-pulse-dot" />
        reasoning
      </span>
    );
  }

  if (item.reasoning_status === "complete") {
    const isTruePositive = item.agent_verdict === "true_positive";
    const style = isTruePositive ? STYLES.complete_true_positive : STYLES.complete_false_positive;
    return (
      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[11px] font-mono ${style}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${isTruePositive ? "bg-signal-truepositive" : "bg-signal-falsepositive"}`} />
        {isTruePositive ? "investigate" : "false positive"}
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[11px] font-mono ${STYLES.neutral}`}>
      pending
    </span>
  );
}
