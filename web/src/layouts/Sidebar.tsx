import { useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import brandMark from "../assets/verifiko-mark.svg";
import { EmailAuthModal } from "../components/auth/EmailAuthModal";
import { Button } from "../components/ui/Button";
import { LanguageSwitcher } from "../components/ui/LanguageSwitcher";
import { primaryNavigation } from "../data/navigation";
import { trackAuthEntryClicked } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { readPendingSessionPlan } from "../lib/authSessionStorage";
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
  const { authReady, currentUser, logout, quotaStatus } = useAuth();
  const [isEmailAuthModalOpen, setIsEmailAuthModalOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const analyticsPlan = currentUser?.plan ?? quotaStatus?.plan ?? "ANONYMOUS";
  const isAuthenticated = Boolean(currentUser);
  const displayName = currentUser ? displayNameForUser(currentUser) : "";
  const initials = currentUser ? initialsForUser(currentUser) : "";
  // While a saved session is being validated, reserve the session card's space so
  // it does not push the page down when it appears (the card shows on phones only).
  const hasPendingSession = !authReady && !currentUser && readPendingSessionPlan() !== null;

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
        <Link className="brand-lockup" to="/app">
          <img alt="" className="brand-lockup__mark" height="52" src={brandMark} width="52" />
          <div>
            <span className="brand-lockup__name">Verifiko</span>
          </div>
        </Link>

        <div className="sidebar__header-actions">
          <LanguageSwitcher className="sidebar__language" />
          <button
            type="button"
            className="sidebar__menu-toggle"
            aria-label={isMenuOpen ? copy.navigation.closeMenu : copy.navigation.openMenu}
            aria-expanded={isMenuOpen}
            aria-controls="primary-nav"
            onClick={() => setIsMenuOpen((open) => !open)}
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" aria-hidden="true">
              {isMenuOpen ? (
                <path
                  d="M6 6l12 12M18 6L6 18"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              ) : (
                <path
                  d="M4 7h16M4 12h16M4 17h16"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      <nav
        id="primary-nav"
        aria-label={copy.navigation.primaryLabel}
        className={isMenuOpen ? "sidebar-nav sidebar-nav--open" : "sidebar-nav"}
      >
        {primaryNavigation.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            onClick={() => setIsMenuOpen(false)}
            className={isActiveItem(item.href) ? "sidebar-nav__link sidebar-nav__link--active" : "sidebar-nav__link"}
          >
            {item.labelKey === "review"
              ? currentUser
                ? copy.navigation.history
                : copy.navigation.info
              : copy.navigation[item.labelKey]}
          </NavLink>
        ))}
        {!currentUser ? (
          <button
            className="sidebar-nav__button sidebar-nav__button--mobile-only"
            onClick={() => {
              setIsMenuOpen(false);
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
      ) : hasPendingSession ? (
        <PendingSessionCard
          historyLabel={copy.topbar.reviewHistory}
          signOutLabel={copy.topbar.signOut}
        />
      ) : null}
      <EmailAuthModal open={isEmailAuthModalOpen} onClose={() => setIsEmailAuthModalOpen(false)} />
    </aside>
  );
}

const NBSP = "\u00a0";

// Mirrors the session card's markup and classes so it has the same size. The pills
// carry the real (transparent) labels and the same element types as the real
// actions (a link, then a native <button>, which does not inherit the font size).
function PendingSessionCard({
  historyLabel,
  signOutLabel,
}: {
  historyLabel: string;
  signOutLabel: string;
}) {
  return (
    <section aria-hidden="true" className="sidebar-account sidebar-account--pending">
      <div className="sidebar-account__identity">
        <div className="sidebar-account__avatar sidebar-account__avatar--skeleton" />
        <div className="sidebar-account__copy">
          <p className="sidebar-account__eyebrow sidebar-skeleton">{NBSP}</p>
          <p className="sidebar-account__label sidebar-skeleton">{NBSP}</p>
          <p className="sidebar-account__value sidebar-skeleton">{NBSP}</p>
          <p className="sidebar-account__meta sidebar-skeleton">{NBSP}</p>
        </div>
      </div>
      <div className="sidebar-account__actions">
        <span className="button sidebar-account__history sidebar-account__button-skeleton">
          {historyLabel}
        </span>
        <button
          className="button sidebar-account__logout sidebar-account__button-skeleton"
          disabled
          tabIndex={-1}
          type="button"
        >
          {signOutLabel}
        </button>
      </div>
    </section>
  );
}
