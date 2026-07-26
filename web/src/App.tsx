import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AnalyticsPageTracker } from "./components/analytics/AnalyticsPageTracker";
import { AppLayout } from "./layouts/AppLayout";
import { LandingPage } from "./pages/LandingPage";

// The landing is the entry point and stays eager; the rest of the app is
// code-split so a first visit to "/" never downloads the whole workspace.
const HomePage = lazy(() => import("./pages/HomePage").then((m) => ({ default: m.HomePage })));
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const VerificationDetailPage = lazy(() =>
  import("./pages/VerificationDetailPage").then((m) => ({ default: m.VerificationDetailPage })),
);
const ApiHealthPage = lazy(() =>
  import("./pages/ApiHealthPage").then((m) => ({ default: m.ApiHealthPage })),
);
const ContactPage = lazy(() =>
  import("./pages/ContactPage").then((m) => ({ default: m.ContactPage })),
);
const PrivacyPage = lazy(() =>
  import("./pages/PrivacyPage").then((m) => ({ default: m.PrivacyPage })),
);
const TermsPage = lazy(() => import("./pages/TermsPage").then((m) => ({ default: m.TermsPage })));
const MagicLinkPage = lazy(() =>
  import("./pages/MagicLinkPage").then((m) => ({ default: m.MagicLinkPage })),
);
const NotFoundPage = lazy(() =>
  import("./pages/NotFoundPage").then((m) => ({ default: m.NotFoundPage })),
);

export default function App() {
  return (
    <BrowserRouter>
      <AnalyticsPageTracker />
      <Suspense fallback={null}>
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
      </Suspense>
    </BrowserRouter>
  );
}
