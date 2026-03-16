import { NavLink, useLocation } from "react-router-dom";

import { dashboardMetrics } from "../data/mockDashboard";
import brandMark from "../assets/verifiko-mark.svg";
import { primaryNavigation } from "../data/navigation";

export function Sidebar() {
  const location = useLocation();

  function isActiveItem(href: string): boolean {
    const currentPath = `${location.pathname}${location.hash}`;

    if (href.includes("#")) {
      return currentPath === href;
    }

    if (href === "/dashboard") {
      return location.pathname === "/dashboard" && location.hash.length === 0;
    }

    return location.pathname === href;
  }

  return (
    <aside className="sidebar">
      <div className="brand-lockup">
        <img alt="" className="brand-lockup__mark" height="52" src={brandMark} width="52" />
        <div>
          <p className="brand-lockup__kicker">Verification Workspace</p>
          <h1 className="brand-lockup__name">Verifiko</h1>
        </div>
      </div>

      <p className="sidebar__copy">
        Explainable risk scoring with evidence traceability and analyst-oriented review workflows.
      </p>

      <nav aria-label="Primary" className="sidebar-nav">
        {primaryNavigation.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            className={isActiveItem(item.href) ? "sidebar-nav__link sidebar-nav__link--active" : "sidebar-nav__link"}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-panel">
        <p className="sidebar-panel__label">Workspace context</p>
        <div className="sidebar-panel__stack">
          <p className="sidebar-panel__text">Environment: {dashboardMetrics.environmentLabel}</p>
          <p className="sidebar-panel__text">Mode: Demo data with investigation-style workflows</p>
          <p className="sidebar-panel__text">
            Last sync: {new Date(dashboardMetrics.lastVerificationAt).toLocaleString()}
          </p>
          <p className="sidebar-panel__text">Backend status: {dashboardMetrics.apiStatus}</p>
        </div>
      </div>
    </aside>
  );
}
