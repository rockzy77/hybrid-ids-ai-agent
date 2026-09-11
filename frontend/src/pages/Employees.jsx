import { useEffect, useState } from "react";
import { api } from "../api";

export default function Employees() {
  const [employees, setEmployees] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getEmployees()
      .then(setEmployees)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Employees</h1>
        <p className="text-sm text-text-secondary mt-1">
          Organisational context the agent queries when triaging an alert.
        </p>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded border border-signal-truepositive/40 bg-signal-truepositive/10 text-sm text-signal-truepositive">
          Can't reach the backend ({error}).
        </div>
      )}

      <div className="rounded border border-hairline bg-panel overflow-hidden">
        <div className="grid grid-cols-[1fr_140px_180px_130px_110px_110px] gap-4 px-4 py-2 border-b border-hairline text-[11px] uppercase tracking-wider text-text-secondary">
          <span>name</span>
          <span>department</span>
          <span>role</span>
          <span>ip address</span>
          <span>hours</span>
          <span>clearance</span>
        </div>

        {employees.length === 0 && !error ? (
          <div className="px-4 py-10 text-center text-sm text-text-secondary">Loading...</div>
        ) : (
          employees.map((e) => (
            <div
              key={e.id}
              className="grid grid-cols-[1fr_140px_180px_130px_110px_110px] gap-4 px-4 py-2.5 border-b border-hairline last:border-b-0 text-sm hover:bg-panel-raised"
            >
              <span>{e.name}</span>
              <span className="text-text-secondary">{e.department}</span>
              <span className="text-text-secondary">{e.role}</span>
              <span className="font-mono text-xs">{e.ip_address}</span>
              <span className="font-mono text-xs text-text-secondary">
                {e.work_start}–{e.work_end}
              </span>
              <span className="font-mono text-xs uppercase text-text-secondary">{e.clearance_level}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
