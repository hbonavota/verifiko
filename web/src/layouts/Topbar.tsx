import { useLocation } from "react-router-dom";

import { EmailAuthModal } from "../components/auth/EmailAuthModal";
import { GoogleSignInButton } from "../components/auth/GoogleSignInButton";
import { Button } from "../components/ui/Button";
import { UpgradeModal } from "../components/ui/UpgradeModal";
import { useAuth } from "../lib/auth";
import { readStoredAuthSession } from "../lib/authSessionStorage";
import { trackAuthEntryClicked, trackUpgradeIntentClicked } from "../lib/analytics";
import { LanguageSwitcher } from "../components/ui/LanguageSwitcher";
import { useI18n } from "../lib/i18n";
import { useState } from "react";
import { useUpgradeIntent } from "../lib/upgradeIntentStorage";

export function Topbar() {
  const { copy, language } = useI18n();
  const { authReady, currentUser, logout, quotaReady, quotaStatus } = useAuth();
  const location = useLocation();
  const [isUpgradeModalOpen, setIsUpgradeModalOpen] = useState(false);
  const [isEmailAuthModalOpen, setIsEmailAuthModalOpen] = useState(false);
  const { hasSubmittedUpgradeIntent } = useUpgradeIntent();
  const displayName = currentUser?.display_name?.trim() || currentUser?.email || "";
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((segment) => segment.charAt(0).toUpperCase())
    .join("");
  const quotaSummary = quotaReady && quotaStatus ? buildQuotaSummary(copy, quotaStatus) : null;
  const analyticsPlan = currentUser?.plan ?? quotaStatus?.plan ?? "ANONYMOUS";
  const isAuthenticated = Boolean(currentUser);
  // While a saved session is being validated, show an account-sized placeholder
  // instead of the sign-in actions so the swap to the account block does not
  // push the page down. Anonymous visitors (no saved session) are unaffected.
  const pendingSessionPlan = !authReady && !currentUser ? readPendingSessionPlan() : null;

  return (
    <>
      <header className="topbar">
        <div>
          <p className="topbar__eyebrow">{copy.topbar.eyebrow}</p>
          <p className="topbar__title">{copy.topbar.title}</p>
        </div>
        <div
          className={
            currentUser || pendingSessionPlan
              ? "topbar__actions topbar__actions--account"
              : "topbar__actions"
          }
        >
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
                <p className="topbar-account__eyebrow">{copy.topbar.account}</p>
                <p className="topbar-account__label">{copy.topbar.accountHistoryEnabled}</p>
                <p className="topbar-account__value">{displayName}</p>
                <p className="topbar-account__meta">{currentUser.email}</p>
                {quotaSummary ? (
                  <>
                    <p className="topbar-account__quota">{quotaSummary.title}</p>
                    <p className="topbar-account__quota-note">{quotaSummary.detail}</p>
                  </>
                ) : (
                  // Keep the quota lines' space so the block does not grow when the
                  // quota arrives; if it never does, keep the space but show nothing.
                  <QuotaLinePlaceholders variant={quotaReady ? "reserved" : "skeleton"} />
                )}
              </div>
              <div className="topbar-account__actions">
                <Button to="/dashboard" variant="ghost">
                  {copy.topbar.reviewHistory}
                </Button>
                {currentUser.plan === "FREE" ? (
                  <Button
                    className={hasSubmittedUpgradeIntent ? "topbar-account__upgrade-button" : undefined}
                    onClick={() => {
                      trackUpgradeIntentClicked({
                        sourcePath: location.pathname,
                        language,
                        isAuthenticated,
                        plan: analyticsPlan,
                        source: "topbar",
                      });
                      setIsUpgradeModalOpen(true);
                    }}
                    variant={hasSubmittedUpgradeIntent ? "secondary" : "primary"}
                  >
                    {hasSubmittedUpgradeIntent
                      ? copy.topbar.upgradeInterestSaved
                      : copy.topbar.upgradeToPro}
                  </Button>
                ) : null}
                <Button onClick={logout} variant="secondary">
                  {copy.topbar.signOut}
                </Button>
              </div>
            </div>
          ) : pendingSessionPlan ? (
            <PendingAccountPlaceholder plan={pendingSessionPlan} />
          ) : (
            <div className="topbar-auth">
              <div className="topbar-auth__access-actions">
                <GoogleSignInButton
                  onInteraction={() => {
                    trackAuthEntryClicked({
                      sourcePath: location.pathname,
                      language,
                      isAuthenticated,
                      plan: analyticsPlan,
                      entryPoint: "topbar_google_sign_in",
                    });
                  }}
                />
                <Button
                  className="topbar-auth__email-button"
                  variant="secondary"
                  onClick={() => {
                    trackAuthEntryClicked({
                      sourcePath: location.pathname,
                      language,
                      isAuthenticated,
                      plan: analyticsPlan,
                      entryPoint: "topbar_email",
                    });
                    setIsEmailAuthModalOpen(true);
                  }}
                >
                  {copy.topbar.signInWithEmail}
                </Button>
              </div>
              <p className="topbar-auth__cta">{copy.topbar.signInToUnlockMore}</p>
            </div>
          )}
          <LanguageSwitcher className="topbar__language" />
        </div>
      </header>
      <UpgradeModal
        open={isUpgradeModalOpen}
        onClose={() => setIsUpgradeModalOpen(false)}
        source="topbar"
      />
      <EmailAuthModal
        open={isEmailAuthModalOpen}
        onClose={() => setIsEmailAuthModalOpen(false)}
      />
    </>
  );
}

const NBSP = "\u00a0";

function QuotaLinePlaceholders({ variant }: { variant: "skeleton" | "reserved" }) {
  const modifier = `topbar-account__quota--${variant}`;
  return (
    <>
      <p aria-hidden="true" className={`topbar-account__quota ${modifier}`}>
        {NBSP}
      </p>
      <p aria-hidden="true" className={`topbar-account__quota-note ${modifier}`}>
        {NBSP}
      </p>
    </>
  );
}

// Mirrors the account block's structure and line classes so it has the same size.
function PendingAccountPlaceholder({ plan }: { plan: string }) {
  const actionCount = plan === "FREE" ? 3 : 2;
  return (
    <div aria-hidden="true" className="topbar-account topbar-account--pending">
      <div className="topbar-account__avatar topbar-account__avatar--skeleton" />
      <div className="topbar-account__copy">
        <p className="topbar-account__eyebrow topbar-skeleton">{NBSP}</p>
        <p className="topbar-account__label topbar-skeleton">{NBSP}</p>
        <p className="topbar-account__value topbar-skeleton">{NBSP}</p>
        <p className="topbar-account__meta topbar-skeleton">{NBSP}</p>
        <QuotaLinePlaceholders variant="skeleton" />
      </div>
      <div className="topbar-account__actions">
        {/* Same elements as the real actions (a link, then <button>s): native
            buttons do not inherit the font size, so the element type matters. */}
        <span className="button topbar-account__button-skeleton">{NBSP}</span>
        {Array.from({ length: actionCount - 1 }, (_, index) => (
          <button
            className="button topbar-account__button-skeleton"
            disabled
            key={index}
            tabIndex={-1}
            type="button"
          >
            {NBSP}
          </button>
        ))}
      </div>
    </div>
  );
}

function readPendingSessionPlan(): string | null {
  try {
    const session = readStoredAuthSession();
    return session ? session.user?.plan ?? "FREE" : null;
  } catch {
    return null;
  }
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
