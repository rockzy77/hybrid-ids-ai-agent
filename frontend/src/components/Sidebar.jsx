import { NavLink } from "react-router-dom";
import { useFeed } from "../FeedContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard" },
  { to: "/live-feed", label: "Live Feed" },
  { to: "/alerts", label: "Alerts" },
  { to: "/employees", label: "Employees" },
];

export default function Sidebar() {
  const { connectionError } = useFeed();

  return (
    <aside className="w-56 shrink-0 bg-panel border-r border-hairline flex flex-col h-screen sticky top-0">
      <div className="px-5 py-6 border-b border-hairline">
        <div className="font-mono text-sm tracking-widest text-text-primary">
          HYBRID<span className="text-signal-reasoning">·</span>IDS
        </div>
        <div className="text-[11px] text-text-secondary mt-1">SOC Console</div>
      </div>

      <nav className="flex-1 py-4">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `block px-5 py-2.5 text-sm border-l-2 transition-colors ${
                isActive
                  ? "border-signal-reasoning text-text-primary bg-panel-raised"
                  : "border-transparent text-text-secondary hover:text-text-primary hover:bg-panel-raised"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-hairline text-[11px] font-mono text-text-secondary">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              connectionError ? "bg-signal-truepositive" : "bg-signal-benign animate-pulse-dot"
            }`}
          />
          {connectionError ? "backend unreachable" : "backend connected"}
        </div>
      </div>
    </aside>
  );
}
