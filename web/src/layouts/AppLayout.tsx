import { CookieBanner } from "../components/ui/CookieBanner";
import { Outlet } from "react-router-dom";

import { ContentShell } from "./ContentShell";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-layout__main">
        <Topbar />
        <ContentShell>
          <Outlet />
        </ContentShell>
        <CookieBanner />
      </div>
    </div>
  );
}
