import { lazy, Suspense, type ComponentType } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AnalyticsPageTracker } from "./components/analytics/AnalyticsPageTracker";
import { RouteErrorBoundary } from "./components/ui/RouteErrorBoundary";
import { AppLayout } from "./layouts/AppLayout";
import { LandingPage } from "./pages/LandingPage";

// After a new deploy, an old tab holds an index.html that points at chunk
// hashes that no longer exist, so a lazy import 404s and React renders a blank
// screen. Recover by reloading the page once (guarded so we never loop).
function lazyWithReload<T extends ComponentType<unknown>>(
  factory: () => Promise<{ default: T }>,
) {
  return lazy(() =>
    factory()
      .then((mod) => {
        window.sessionStorage.removeItem("verifiko:chunk-reload");
        return mod;
      })
      .catch((error) => {
        if (!window.sessionStorage.getItem("verifiko:chunk-reload")) {
          window.sessionStorage.setItem("verifiko:chunk-reload", "1");
          window.location.reload();
          return new Promise<{ default: T }>(() => {});
        }
        throw error;
      }),
  );
}

// The landing is the entry point and stays eager; the rest of the app is
// code-split so a first visit to "/" never downloads the whole workspace.
const HomePage = lazyWithReload(() =>
  import("./pages/HomePage").then((m) => ({ default: m.HomePage })),
);
const DashboardPage = lazyWithReload(() =>
  import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const VerificationDetailPage = lazyWithReload(() =>
  import("./pages/VerificationDetailPage").then((m) => ({ default: m.VerificationDetailPage })),
);
const ApiHealthPage = lazyWithReload(() =>
  import("./pages/ApiHealthPage").then((m) => ({ default: m.ApiHealthPage })),
);
const ContactPage = lazyWithReload(() =>
  import("./pages/ContactPage").then((m) => ({ default: m.ContactPage })),
);
const PrivacyPage = lazyWithReload(() =>
  import("./pages/PrivacyPage").then((m) => ({ default: m.PrivacyPage })),
);
const TermsPage = lazyWithReload(() =>
  import("./pages/TermsPage").then((m) => ({ default: m.TermsPage })),
);
const MagicLinkPage = lazyWithReload(() =>
  import("./pages/MagicLinkPage").then((m) => ({ default: m.MagicLinkPage })),
);
const NotFoundPage = lazyWithReload(() =>
  import("./pages/NotFoundPage").then((m) => ({ default: m.NotFoundPage })),
);

export default function App() {
  return (
    <BrowserRouter>
      <AnalyticsPageTracker />
      <RouteErrorBoundary>
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
      </RouteErrorBoundary>
    </BrowserRouter>
  );
}
