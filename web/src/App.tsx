import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AnalyticsPageTracker } from "./components/analytics/AnalyticsPageTracker";
import { AppLayout } from "./layouts/AppLayout";
import { ApiHealthPage } from "./pages/ApiHealthPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { VerificationDetailPage } from "./pages/VerificationDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <AnalyticsPageTracker />
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/verifications/:id" element={<VerificationDetailPage />} />
          <Route path="/api-health" element={<ApiHealthPage />} />
          <Route path="/home" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
