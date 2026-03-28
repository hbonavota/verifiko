import { useState } from "react";

import { CookieBanner } from "../components/ui/CookieBanner";
import { Outlet } from "react-router-dom";

import { ContentShell } from "./ContentShell";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppLayout() {
  const [cookieBannerReopenKey, setCookieBannerReopenKey] = useState(0);

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-layout__main">
        <Topbar />
        <ContentShell onOpenCookiePreferences={() => setCookieBannerReopenKey((current) => current + 1)}>
          <Outlet />
        </ContentShell>
        <CookieBanner reopenKey={cookieBannerReopenKey} />
      </div>
    </div>
  );
}
