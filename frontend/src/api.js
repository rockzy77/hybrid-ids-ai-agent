const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

async function request(path, options) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (res.status === 204) return null;
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request to ${path} failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  getAlerts: () => request("/api/alerts"),
  getNextTraffic: () => request("/api/traffic/next"),
  getEmployees: () => request("/api/employees"),
  getDashboardStats: () => request("/api/dashboard/stats"),
  analyseAlert: (alert) =>
    request("/api/alerts/analyse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(alert),
    }),
};
