import { Link, NavLink, useLocation } from "react-router-dom";

import brandMark from "../assets/verifiko-mark.svg";
import { LanguageSwitcher } from "../components/ui/LanguageSwitcher";
import { primaryNavigation } from "../data/navigation";
import { useI18n } from "../lib/i18n";

export function Sidebar() {
  const location = useLocation();
  const { copy } = useI18n();

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
      <div className="sidebar__header">
        <Link className="brand-lockup" to="/">
          <img alt="" className="brand-lockup__mark" height="52" src={brandMark} width="52" />
          <div>
            <span className="brand-lockup__name">Verifiko</span>
          </div>
        </Link>

        <LanguageSwitcher className="sidebar__language" />
      </div>

      <nav aria-label={copy.navigation.primaryLabel} className="sidebar-nav">
        {primaryNavigation.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            className={isActiveItem(item.href) ? "sidebar-nav__link sidebar-nav__link--active" : "sidebar-nav__link"}
          >
            {copy.navigation[item.labelKey]}
          </NavLink>
        ))}
        <button
          className="sidebar-nav__button sidebar-nav__button--mobile-only"
          data-future-auth-trigger="login"
          type="button"
        >
          {copy.navigation.login}
        </button>
      </nav>
    </aside>
  );
}
