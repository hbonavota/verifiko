import { GoogleSignInButton } from "../components/auth/GoogleSignInButton";
import { Button } from "../components/ui/Button";
import { UpgradeModal } from "../components/ui/UpgradeModal";
import { useAuth } from "../lib/auth";
import { LanguageSwitcher } from "../components/ui/LanguageSwitcher";
import { useI18n } from "../lib/i18n";
import { useState } from "react";

export function Topbar() {
  const { copy } = useI18n();
  const { currentUser, logout, quotaReady, quotaStatus } = useAuth();
  const [isUpgradeModalOpen, setIsUpgradeModalOpen] = useState(false);
  const displayName = currentUser?.display_name?.trim() || currentUser?.email || "";
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((segment) => segment.charAt(0).toUpperCase())
    .join("");
  const quotaSummary = quotaReady && quotaStatus ? buildQuotaSummary(copy, quotaStatus) : null;

  return (
    <>
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
                {quotaSummary ? (
                  <>
                    <p className="topbar-account__quota">{quotaSummary.title}</p>
                    <p className="topbar-account__quota-note">{quotaSummary.detail}</p>
                  </>
                ) : null}
              </div>
              <div className="topbar-account__actions">
                <Button to="/dashboard" variant="ghost">
                  {copy.topbar.reviewHistory}
                </Button>
                {currentUser.plan === "FREE" ? (
                  <Button
                    onClick={() => {
                      console.log("upgrade_clicked");
                      setIsUpgradeModalOpen(true);
                    }}
                    variant="primary"
                  >
                    {copy.topbar.upgradeToPro}
                  </Button>
                ) : null}
                <Button onClick={logout} variant="secondary">
                  {copy.topbar.signOut}
                </Button>
              </div>
            </div>
          ) : (
            <div className="topbar-auth">
              <p className="topbar-auth__cta">{copy.topbar.signInToUnlockMore}</p>
              <GoogleSignInButton />
              {quotaSummary ? (
                <div className="topbar-auth__quota">
                  <p className="topbar-auth__quota-title">{quotaSummary.title}</p>
                  <p className="topbar-auth__quota-copy">{quotaSummary.detail}</p>
                </div>
              ) : null}
            </div>
          )}
          <LanguageSwitcher className="topbar__language" />
        </div>
      </header>
      <UpgradeModal open={isUpgradeModalOpen} onClose={() => setIsUpgradeModalOpen(false)} />
    </>
  );
}

function buildQuotaSummary(
  copy: ReturnType<typeof useI18n>["copy"],
  quotaStatus: NonNullable<ReturnType<typeof useAuth>["quotaStatus"]>,
): { title: string; detail: string } {
  if (quotaStatus.plan === "ANONYMOUS") {
    if (quotaStatus.blocked) {
      return {
        title: copy.topbar.quota.anonymousBlockedTitle,
        detail: copy.topbar.quota.anonymousBlockedDetail,
      };
    }

    return {
      title: copy.topbar.quota.anonymousTitle
        .replace("{remaining}", String(quotaStatus.remaining_today))
        .replace("{dailyLimit}", String(quotaStatus.daily_limit)),
      detail: copy.topbar.quota.anonymousDetail,
    };
  }

  if (quotaStatus.plan === "PRO") {
    if (quotaStatus.blocked) {
      return {
        title: copy.topbar.quota.proBlockedTitle,
        detail: copy.topbar.quota.resetDetail,
      };
    }

    return {
      title: copy.topbar.quota.proTitle
        .replace("{remaining}", String(quotaStatus.remaining_today))
        .replace("{dailyLimit}", String(quotaStatus.daily_limit)),
      detail: copy.topbar.quota.proDetail,
    };
  }

  if (quotaStatus.blocked) {
    return {
      title: copy.topbar.quota.freeBlockedTitle,
      detail: copy.topbar.quota.freeBlockedDetail,
    };
  }

  return {
    title: copy.topbar.quota.freeTitle
      .replace("{remaining}", String(quotaStatus.remaining_today))
      .replace("{dailyLimit}", String(quotaStatus.daily_limit)),
    detail: copy.topbar.quota.freeDetail,
  };
}
