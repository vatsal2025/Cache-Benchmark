import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./lib/store";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import OverviewPage from "./pages/OverviewPage";
import CaptchaLibraryPage from "./pages/CaptchaLibraryPage";
import CaptchaDetailPage from "./pages/CaptchaDetailPage";
import AttackBenchmarkPage from "./pages/AttackBenchmarkPage";
import ExperimentManagerPage from "./pages/ExperimentManagerPage";
import ExperimentDetailPage from "./pages/ExperimentDetailPage";
import BacktestMonitorPage from "./pages/BacktestMonitorPage";
import ReportsPage from "./pages/ReportsPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/overview" replace />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="captchas" element={<CaptchaLibraryPage />} />
          <Route path="captchas/:id" element={<CaptchaDetailPage />} />
          <Route path="captchas/:id/attacks" element={<AttackBenchmarkPage />} />
          <Route path="experiments" element={<ExperimentManagerPage />} />
          <Route path="experiments/:id" element={<ExperimentDetailPage />} />
          <Route path="backtests" element={<BacktestMonitorPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
