import { useEffect, useState } from "react";

import { CookieBanner } from "../components/ui/CookieBanner";
import { Outlet } from "react-router-dom";

import { useAuth } from "../lib/auth";
import { ContentShell } from "./ContentShell";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppLayout() {
  const [cookieBannerReopenKey, setCookieBannerReopenKey] = useState(0);
  const { authReady, currentUser, refreshQuotaStatus } = useAuth();

  // Quota is fetched here (inside the app shell) rather than globally, so the
  // marketing landing at "/" never makes an API call on first paint.
  useEffect(() => {
    if (authReady) {
      void refreshQuotaStatus();
    }
  }, [authReady, currentUser?.id, refreshQuotaStatus]);

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-layout__main">
        <Topbar />
        <ContentShell
          onOpenCookiePreferences={() => setCookieBannerReopenKey((current) => current + 1)}
        >
          <Outlet />
        </ContentShell>
        <CookieBanner reopenKey={cookieBannerReopenKey} />
      </div>
    </div>
  );
}
