import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { api } from "../api";

function StatCard({ label, value, accent }) {
  return (
    <div className="rounded border border-hairline bg-panel px-5 py-4">
      <div className="text-[11px] uppercase tracking-wider text-text-secondary mb-2">{label}</div>
      <div className={`text-2xl font-mono font-semibold ${accent || "text-text-primary"}`}>{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getDashboardStats();
        setStats(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      }
    };
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, []);

  if (error) {
    return (
      <div className="p-8">
        <div className="px-4 py-3 rounded border border-signal-truepositive/40 bg-signal-truepositive/10 text-sm text-signal-truepositive">
          Can't reach the backend ({error}).
        </div>
      </div>
    );
  }

  if (!stats) {
    return <div className="p-8 text-sm text-text-secondary">Loading...</div>;
  }

  const funnelData = [
    { stage: "Traffic processed", count: stats.total_traffic_processed, fill: "#64748B" },
    { stage: "Flagged as attack", count: stats.total_alerts, fill: "#38BDF8" },
    { stage: "Needs investigation", count: stats.true_positives, fill: "#F14668" },
  ];

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="text-sm text-text-secondary mt-1">Two-stage detection pipeline, end to end.</p>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Traffic processed" value={stats.total_traffic_processed} />
        <StatCard label="Alerts flagged" value={stats.total_alerts} accent="text-signal-reasoning" />
        <StatCard label="Requires investigation" value={stats.true_positives} accent="text-signal-truepositive" />
        <StatCard label="Resolved false positives" value={stats.false_positives} accent="text-signal-falsepositive" />
      </div>

      <div className="rounded border border-hairline bg-panel p-5 mb-8">
        <h2 className="text-sm uppercase tracking-wider text-text-secondary mb-4">Detection funnel</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={funnelData} layout="vertical" margin={{ left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#232D38" horizontal={false} />
            <XAxis type="number" stroke="#8A99A8" fontSize={12} />
            <YAxis type="category" dataKey="stage" stroke="#8A99A8" fontSize={12} width={140} />
            <Tooltip
              contentStyle={{ background: "#1A222B", border: "1px solid #232D38", borderRadius: 6 }}
              labelStyle={{ color: "#DCE4EC" }}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]}>
              {funnelData.map((entry, index) => (
                <Cell key={index} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded border border-hairline bg-panel px-5 py-4">
          <div className="text-[11px] uppercase tracking-wider text-text-secondary mb-2">
            RF model test-set FPR
          </div>
          <div className="text-2xl font-mono font-semibold text-text-primary">
            {stats.rf_test_fpr !== null ? `${(stats.rf_test_fpr * 100).toFixed(2)}%` : "—"}
          </div>
          <p className="text-xs text-text-secondary mt-2">
            Measured on held-out CICIDS2017 test data with real ground truth (see ml/metrics.json).
          </p>
        </div>
        <div className="rounded border border-hairline bg-panel px-5 py-4">
          <div className="text-[11px] uppercase tracking-wider text-text-secondary mb-2">
            Agent workload reduction
          </div>
          <div className="text-2xl font-mono font-semibold text-text-primary">
            {(stats.alert_reduction_rate * 100).toFixed(1)}%
          </div>
          <p className="text-xs text-text-secondary mt-2">
            Share of flagged alerts the agent resolved as false positive — a workload metric, not an
            independent accuracy measure (these live alerts have no separate ground truth).
          </p>
        </div>
      </div>
    </div>
  );
}
