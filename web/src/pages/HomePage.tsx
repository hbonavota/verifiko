import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { AnalyzeUrlForm } from "../components/analysis/AnalyzeUrlForm";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { VerificationProgress } from "../components/analysis/VerificationProgress";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { trackQuotaPromptShown, trackResultActionClicked } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { listMyVerifications } from "../lib/api";
import { formatRiskLevel, formatVerdict } from "../lib/formatVerdict";
import { useI18n } from "../lib/i18n";
import { resultNote } from "../lib/coverageNote";
import { adaptApiVerification } from "../lib/verificationAdapter";
import { toneForRiskLevel } from "../lib/risk";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import type { ApiVerification, RiskLevel, VerificationSummary } from "../types/verification";

function cardToneForRiskLevel(riskLevel: RiskLevel) {
  const tone = toneForRiskLevel(riskLevel);
  return tone === "warning" || tone === "danger" || tone === "success" ? tone : "default";
}

export function HomePage() {
  const { copy, language } = useI18n();
  const { authReady, currentUser, quotaReady, quotaStatus } = useAuth();
  const location = useLocation();

  useDocumentMeta(
    copy.home.metaTitle,
    copy.home.metaDescription,
  );

  const [verifications, setVerifications] = useState<VerificationSummary[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [analysisState, setAnalysisState] = useState<"idle" | "submitting" | "error">("idle");
  const [deepAnalysisActive, setDeepAnalysisActive] = useState(false);
  const [inlineResult, setInlineResult] = useState<VerificationSummary | null>(null);
  const hasTrackedAnonymousSupportRef = useRef(false);

  useEffect(() => {
    let isMounted = true;

    async function loadVerifications() {
      if (!authReady) {
        return;
      }
      if (!currentUser) {
        if (isMounted) {
          setVerifications([]);
          setIsHistoryLoading(false);
        }
        return;
      }

      try {
        if (isMounted) {
          setIsHistoryLoading(true);
        }
        const payload = await listMyVerifications();
        if (!isMounted) {
          return;
        }

        setVerifications(payload.map((verification) => adaptApiVerification(verification, language)));
      } catch {
        if (!isMounted) {
          return;
        }

        setVerifications([]);
      } finally {
        if (isMounted) {
          setIsHistoryLoading(false);
        }
      }
    }

    void loadVerifications();

    return () => {
      isMounted = false;
    };
  }, [authReady, currentUser, language]);

  const isLoadingAnalysis = analysisState === "submitting";
  const showAnonymousSupport = authReady && !currentUser;
  const analyticsPlan = currentUser?.plan ?? quotaStatus?.plan ?? "ANONYMOUS";
  const isAuthenticated = Boolean(currentUser);
  const hasAnonymousQuotaStatus = quotaReady && quotaStatus?.plan === "ANONYMOUS";
  const anonymousSupportTitle = hasAnonymousQuotaStatus
    ? quotaStatus.blocked
      ? copy.topbar.quota.anonymousBlockedTitle
      : copy.topbar.quota.anonymousTitle
          .replace("{remaining}", String(quotaStatus.remaining_today))
          .replace("{dailyLimit}", String(quotaStatus.daily_limit))
    : null;
  const anonymousSupportDescription =
    hasAnonymousQuotaStatus && quotaStatus.blocked
      ? copy.topbar.quota.anonymousBlockedDetail
      : copy.home.authPromptCopy;
  const anonymousSupportMeta =
    hasAnonymousQuotaStatus && quotaStatus.blocked ? copy.analyzeForm.quota.resetAtMidnight : null;

  useEffect(() => {
    if (showAnonymousSupport && !hasTrackedAnonymousSupportRef.current) {
      trackQuotaPromptShown({
        sourcePath: location.pathname,
        language,
        isAuthenticated,
        plan: analyticsPlan,
        promptType: "support_note_anonymous",
      });
      hasTrackedAnonymousSupportRef.current = true;
      return;
    }

    if (!showAnonymousSupport) {
      hasTrackedAnonymousSupportRef.current = false;
    }
  }, [analyticsPlan, isAuthenticated, language, location.pathname, showAnonymousSupport]);

  function handleVerified(verification: ApiVerification) {
    setInlineResult(adaptApiVerification(verification, language));
    setAnalysisState("idle");
  }

  function handleVerifyAnother() {
    setInlineResult(null);
  }

  // While a scan is running (or a fresh result is ready) the verify card morphs
  // in place: the form is swapped for the live spinner and then the result, so
  // the user watches it happen without navigating or scrolling to hunt for it.
  const showActivityPanel = isLoadingAnalysis || inlineResult !== null;

  return (
    <PageShell>
      <section
        className={`analysis-hero${showActivityPanel ? " analysis-hero--active" : ""}`}
      >
        <div className="analysis-hero__content" id="analyze-url">
          <SectionTitle
            eyebrow={copy.home.eyebrow}
            title={copy.home.title}
            description={copy.home.description}
          />

          {showActivityPanel ? (
            <div className="analysis-hero__result-shell">
              <Card
                eyebrow={
                  isLoadingAnalysis
                    ? deepAnalysisActive
                      ? copy.home.deepVerifying
                      : copy.home.verifying
                    : copy.home.latestResult
                }
                title={
                  isLoadingAnalysis
                    ? deepAnalysisActive
                      ? copy.home.deepInProgress
                      : copy.home.verificationInProgress
                    : copy.home.verificationResult
                }
                description={undefined}
                tone={
                  isLoadingAnalysis
                    ? "success"
                    : inlineResult
                      ? cardToneForRiskLevel(inlineResult.riskAssessment.riskLevel)
                      : "default"
                }
                className="analysis-hero__result"
              >
                {isLoadingAnalysis ? (
                  <div className="analysis-result-card__hero">
                    <ScoreRing
                      label={deepAnalysisActive ? copy.home.deepVerifying : copy.home.verifying}
                      size="hero"
                      state="loading"
                      valueLabel="…"
                    />
                    <div className="analysis-result-card__summary-block">
                      <p className="analysis-result-card__headline">
                        {deepAnalysisActive
                          ? copy.home.deepVerifyingTarget
                          : copy.home.verifyingTarget}
                      </p>
                      <p className="analysis-result-card__copy">
                        {deepAnalysisActive
                          ? copy.home.deepCollectingSignals
                          : copy.home.collectingSignals}
                      </p>
                      <VerificationProgress deep={deepAnalysisActive} />
                    </div>
                  </div>
                ) : inlineResult ? (
                  <>
                    <div className="analysis-result-card__topline">
                      <Badge
                        label={formatRiskLevel(inlineResult.riskAssessment.riskLevel, language)}
                        tone={toneForRiskLevel(inlineResult.riskAssessment.riskLevel)}
                      />
                    </div>

                    <div className="analysis-result-card__hero">
                      <ScoreRing
                        label={copy.common.trustScore}
                        riskLevel={inlineResult.riskAssessment.riskLevel}
                        score={inlineResult.riskAssessment.score}
                        size="hero"
                      />

                      <div className="analysis-result-card__summary-block">
                        <p
                          className="analysis-result-card__subject"
                          title={inlineResult.originalInput}
                        >
                          {inlineResult.originalInput}
                        </p>
                        <p className="preview-card__label">{copy.common.result}</p>
                        <p className="analysis-result-card__headline">
                          {formatVerdict(inlineResult.riskAssessment.verdict, language)}
                        </p>
                        <p className="analysis-result-card__copy">
                          {resultNote({
                            score: inlineResult.riskAssessment.score,
                            warnings: [
                              ...(inlineResult.riskAssessment.analysisWarnings ?? []),
                              ...(inlineResult.riskAssessment.explanation?.coverageWarnings ?? []),
                            ],
                            scoreGuide: copy.detail.scoreGuide,
                            coverageNote: copy.coverageNote,
                          })}
                        </p>
                        <div className="analysis-result-card__actions">
                          {isAuthenticated ? (
                            <Button
                              to={`/verifications/${inlineResult.id}`}
                              variant="primary"
                              onClick={() => {
                                trackResultActionClicked({
                                  sourcePath: location.pathname,
                                  language,
                                  isAuthenticated,
                                  plan: analyticsPlan,
                                  action: "view_result",
                                  resultState: "latest_result",
                                });
                              }}
                            >
                              {copy.common.viewResult}
                            </Button>
                          ) : null}
                          <Button
                            variant={isAuthenticated ? "secondary" : "primary"}
                            onClick={handleVerifyAnother}
                          >
                            {copy.common.verifyAnotherLink}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </>
                ) : null}
              </Card>
            </div>
          ) : (
            <Card className="analysis-hero__panel" tone="success">
              <p className="hero-panel__eyebrow">{copy.home.startVerification}</p>

              <AnalyzeUrlForm
                buttonLabel={copy.analyzeForm.buttonLabel}
                buttonClassName="analysis-form__button analysis-form__button--hero"
                className="analysis-form--hero"
                hint=""
                inputClassName="analysis-form__input-control"
                onStateChange={(state, meta) => {
                  setAnalysisState(state);
                  if (state === "submitting") {
                    setDeepAnalysisActive(Boolean(meta?.deep));
                  }
                }}
                onVerified={handleVerified}
                showQuotaIndicator={false}
                showProPanel={false}
              />
            </Card>
          )}
        </div>

        {showAnonymousSupport ? (
          <section aria-label={copy.home.authPromptTitle} className="analysis-flow-support">
            <div className="analysis-flow-support__copy">
              <p className="analysis-flow-support__eyebrow">{copy.home.authPromptTitle}</p>
              {anonymousSupportTitle ? (
                <p className="analysis-flow-support__title">{anonymousSupportTitle}</p>
              ) : null}
              {anonymousSupportDescription ? (
                <p className="analysis-flow-support__description">{anonymousSupportDescription}</p>
              ) : null}
              {anonymousSupportMeta ? (
                <p className="analysis-flow-support__meta">{anonymousSupportMeta}</p>
              ) : null}
            </div>
          </section>
        ) : null}
      </section>
    </PageShell>
  );
}
