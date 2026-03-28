import { GoogleSignInButton } from "../components/auth/GoogleSignInButton";
import { Button } from "../components/ui/Button";
import { useAuth } from "../lib/auth";
import { LanguageSwitcher } from "../components/ui/LanguageSwitcher";
import { useI18n } from "../lib/i18n";

export function Topbar() {
  const { copy } = useI18n();
  const { currentUser, logout } = useAuth();

  return (
    <header className="topbar">
      <div>
        <p className="topbar__eyebrow">{copy.topbar.eyebrow}</p>
        <p className="topbar__title">{copy.topbar.title}</p>
      </div>
      <div className="topbar__actions">
        {currentUser ? (
          <div className="topbar-account">
            <div className="topbar-account__copy">
              <p className="topbar-account__label">{copy.topbar.account}</p>
              <p className="topbar-account__value">{currentUser.email}</p>
            </div>
            <Button onClick={logout} variant="secondary">
              {copy.topbar.signOut}
            </Button>
          </div>
        ) : (
          <GoogleSignInButton className="topbar-auth" />
        )}
        <LanguageSwitcher className="topbar__language" />
      </div>
    </header>
  );
}
