import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AnalyticsPageTracker } from "./components/analytics/AnalyticsPageTracker";
import { AppLayout } from "./layouts/AppLayout";
import { ApiHealthPage } from "./pages/ApiHealthPage";
import { ContactPage } from "./pages/ContactPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HomePage } from "./pages/HomePage";
import { LandingPage } from "./pages/LandingPage";
import { MagicLinkPage } from "./pages/MagicLinkPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { TermsPage } from "./pages/TermsPage";
import { VerificationDetailPage } from "./pages/VerificationDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <AnalyticsPageTracker />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route element={<AppLayout />}>
          <Route path="/app" element={<HomePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/verifications/:id" element={<VerificationDetailPage />} />
          <Route path="/api-health" element={<ApiHealthPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/contact" element={<ContactPage />} />
          <Route path="/auth/magic" element={<MagicLinkPage />} />
          <Route path="/home" element={<Navigate to="/app" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
