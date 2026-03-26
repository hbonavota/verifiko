import { NavLink, useLocation } from "react-router-dom";

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
          <h1 className="brand-lockup__name">Verifiko</h1>
        </div>
      </div>

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
    </aside>
  );
}
