import { useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import brandMark from "../assets/verifiko-mark.svg";
import { EmailAuthModal } from "../components/auth/EmailAuthModal";
import { Button } from "../components/ui/Button";
import { LanguageSwitcher } from "../components/ui/LanguageSwitcher";
import { primaryNavigation } from "../data/navigation";
import { trackAuthEntryClicked } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";

function displayNameForUser(user: NonNullable<ReturnType<typeof useAuth>["currentUser"]>): string {
  return user.display_name?.trim() || user.email;
}

function initialsForUser(user: NonNullable<ReturnType<typeof useAuth>["currentUser"]>): string {
  return displayNameForUser(user)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((segment) => segment.charAt(0).toUpperCase())
    .join("");
}

export function Sidebar() {
  const location = useLocation();
  const { copy, language } = useI18n();
  const { currentUser, logout, quotaStatus } = useAuth();
  const [isEmailAuthModalOpen, setIsEmailAuthModalOpen] = useState(false);
  const analyticsPlan = currentUser?.plan ?? quotaStatus?.plan ?? "ANONYMOUS";
  const isAuthenticated = Boolean(currentUser);
  const displayName = currentUser ? displayNameForUser(currentUser) : "";
  const initials = currentUser ? initialsForUser(currentUser) : "";

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
        {!currentUser ? (
          <button
            className="sidebar-nav__button sidebar-nav__button--mobile-only"
            onClick={() => {
              trackAuthEntryClicked({
                sourcePath: location.pathname,
                language,
                isAuthenticated,
                plan: analyticsPlan,
                entryPoint: "sidebar_login",
              });
              setIsEmailAuthModalOpen(true);
            }}
            type="button"
          >
            {copy.navigation.login}
          </button>
        ) : null}
      </nav>

      {currentUser ? (
        <section aria-label={copy.topbar.account} className="sidebar-account">
          <div className="sidebar-account__identity">
            <div className="sidebar-account__avatar" aria-hidden="true">
              {currentUser.avatar_url ? (
                <img
                  alt=""
                  className="sidebar-account__avatar-image"
                  referrerPolicy="no-referrer"
                  src={currentUser.avatar_url}
                />
              ) : (
                <span>{initials || "V"}</span>
              )}
            </div>
            <div className="sidebar-account__copy">
              <p className="sidebar-account__eyebrow">{copy.topbar.account}</p>
              <p className="sidebar-account__label">{copy.topbar.accountHistoryEnabled}</p>
              <p className="sidebar-account__value">{displayName}</p>
              <p className="sidebar-account__meta">{currentUser.email}</p>
            </div>
          </div>
          <div className="sidebar-account__actions">
            <Button className="sidebar-account__history" to="/dashboard" variant="ghost">
              {copy.topbar.reviewHistory}
            </Button>
            <Button className="sidebar-account__logout" onClick={logout} variant="secondary">
              {copy.topbar.signOut}
            </Button>
          </div>
        </section>
      ) : null}
      <EmailAuthModal open={isEmailAuthModalOpen} onClose={() => setIsEmailAuthModalOpen(false)} />
    </aside>
  );
}
