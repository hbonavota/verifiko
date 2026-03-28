import { GoogleSignInButton } from "../components/auth/GoogleSignInButton";
import { Button } from "../components/ui/Button";
import { useAuth } from "../lib/auth";
import { LanguageSwitcher } from "../components/ui/LanguageSwitcher";
import { useI18n } from "../lib/i18n";

export function Topbar() {
  const { copy } = useI18n();
  const { currentUser, logout } = useAuth();
  const displayName = currentUser?.display_name?.trim() || currentUser?.email || "";
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((segment) => segment.charAt(0).toUpperCase())
    .join("");

  return (
    <header className="topbar">
      <div>
        <p className="topbar__eyebrow">{copy.topbar.eyebrow}</p>
        <p className="topbar__title">{copy.topbar.title}</p>
      </div>
      <div className="topbar__actions">
        {currentUser ? (
          <div className="topbar-account">
            <div className="topbar-account__avatar" aria-hidden="true">
              {currentUser.avatar_url ? (
                <img
                  alt=""
                  className="topbar-account__avatar-image"
                  referrerPolicy="no-referrer"
                  src={currentUser.avatar_url}
                />
              ) : (
                <span>{initials || "V"}</span>
              )}
            </div>
            <div className="topbar-account__copy">
              <p className="topbar-account__label">{copy.topbar.accountHistoryEnabled}</p>
              <p className="topbar-account__value">{displayName}</p>
              <p className="topbar-account__meta">{currentUser.email}</p>
            </div>
            <div className="topbar-account__actions">
              <Button to="/dashboard" variant="ghost">
                {copy.topbar.reviewHistory}
              </Button>
              <Button onClick={logout} variant="secondary">
                {copy.topbar.signOut}
              </Button>
            </div>
          </div>
        ) : (
          <GoogleSignInButton className="topbar-auth" />
        )}
        <LanguageSwitcher className="topbar__language" />
      </div>
    </header>
  );
}
