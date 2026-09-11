import { HashRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import { FeedProvider } from "./FeedContext";
import Dashboard from "./pages/Dashboard";
import LiveFeed from "./pages/LiveFeed";
import AlertsTable from "./pages/AlertsTable";
import Employees from "./pages/Employees";

export default function App() {
  return (
    <FeedProvider>
      <HashRouter>
        <div className="flex min-h-screen bg-void">
          <Sidebar />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/live-feed" element={<LiveFeed />} />
              <Route path="/alerts" element={<AlertsTable />} />
              <Route path="/employees" element={<Employees />} />
            </Routes>
          </main>
        </div>
      </HashRouter>
    </FeedProvider>
  );
}
