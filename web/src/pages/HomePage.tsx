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
import type { RiskLevel, VerificationSummary } from "../types/verification";

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
  const resultCardRef = useRef<HTMLDivElement | null>(null);
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

  useEffect(() => {
    if (analysisState !== "submitting") {
      return;
    }

    if (!window.matchMedia("(max-width: 720px)").matches) {
      return;
    }

    const frameId = window.requestAnimationFrame(() => {
      resultCardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, [analysisState]);

  const latestVerification = verifications[0] ?? null;
  const latestSignals = latestVerification?.signals.slice(0, 2) ?? [];
  const latestRiskAssessment = latestVerification?.riskAssessment;
  const isLoadingAnalysis = analysisState === "submitting";
  const isLoadingOwnedResult = !isLoadingAnalysis && authReady && !!currentUser && isHistoryLoading;
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

  return (
    <PageShell>
      <section className="analysis-hero">
        <div className="analysis-hero__content" id="analyze-url">
          <SectionTitle
            eyebrow={copy.home.eyebrow}
            title={copy.home.title}
            description={copy.home.description}
          />

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
              showQuotaIndicator={false}
              showProPanel={false}
            />
          </Card>
        </div>

        <div ref={resultCardRef} className="analysis-hero__result-shell">
          <Card
            eyebrow={
              isLoadingAnalysis
                ? deepAnalysisActive
                  ? copy.home.deepVerifying
                  : copy.home.verifying
                : latestVerification
                  ? copy.home.latestResult
                  : copy.home.result
            }
            title={
              isLoadingAnalysis
                ? deepAnalysisActive
                  ? copy.home.deepInProgress
                  : copy.home.verificationInProgress
                : latestVerification
                  ? copy.home.verificationResult
                  : copy.home.readyToVerify
            }
            description={undefined}
            tone={
              isLoadingAnalysis
                ? "success"
                : latestVerification
                  ? cardToneForRiskLevel(latestRiskAssessment.riskLevel)
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
                    {deepAnalysisActive ? copy.home.deepVerifyingTarget : copy.home.verifyingTarget}
                  </p>
                  <p className="analysis-result-card__copy">
                    {deepAnalysisActive ? copy.home.deepCollectingSignals : copy.home.collectingSignals}
                  </p>
                  <VerificationProgress deep={deepAnalysisActive} />
                </div>
              </div>
            ) : isLoadingOwnedResult ? (
              <div className="analysis-result-card__hero analysis-result-card__hero--empty">
                <ScoreRing label={copy.common.loadingResult} size="hero" state="loading" valueLabel="..." />
                <div className="analysis-result-card__summary-block">
                  <p className="analysis-result-card__headline">{copy.home.latestResult}</p>
                  <p className="analysis-result-card__copy">{copy.home.loadingOwnedResult}</p>
                </div>
              </div>
            ) : latestVerification ? (
              <>
                <div className="analysis-result-card__topline">
                  <Badge
                    label={formatRiskLevel(latestRiskAssessment.riskLevel, language)}
                    tone={toneForRiskLevel(latestRiskAssessment.riskLevel)}
                  />
                </div>

                <div className="analysis-result-card__hero">
                  <ScoreRing
                    label={copy.common.trustScore}
                    riskLevel={latestRiskAssessment.riskLevel}
                    score={latestRiskAssessment.score}
                    size="hero"
                  />

                  <div className="analysis-result-card__summary-block">
                    <p
                      className="analysis-result-card__subject"
                      title={latestVerification.originalInput}
                    >
                      {latestVerification.originalInput}
                    </p>
                    <p className="preview-card__label">{copy.common.result}</p>
                    <p
                      className="analysis-result-card__headline"
                      title={`${copy.common.verificationResult}: ${formatVerdict(latestRiskAssessment.verdict, language)}`}
                    >
                      {formatVerdict(latestRiskAssessment.verdict, language)}
                    </p>
                    <p className="analysis-result-card__copy">
                      {resultNote({
                        score: latestRiskAssessment.score,
                        warnings: [
                          ...(latestRiskAssessment.analysisWarnings ?? []),
                          ...(latestRiskAssessment.explanation?.coverageWarnings ?? []),
                        ],
                        scoreGuide: copy.detail.scoreGuide,
                        coverageNote: copy.coverageNote,
                      })}
                    </p>
                    <div className="analysis-result-card__actions">
                      <Button
                        to={`/verifications/${latestVerification.id}`}
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
                      <Button
                        to="/dashboard"
                        variant="secondary"
                        onClick={() => {
                          trackResultActionClicked({
                            sourcePath: location.pathname,
                            language,
                            isAuthenticated,
                            plan: analyticsPlan,
                            action: "review_signals",
                            resultState: "latest_result",
                          });
                        }}
                      >
                        {copy.common.reviewSignals}
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="analysis-result-card__signals">
                  <p className="preview-card__label">{copy.common.signals}</p>
                  {latestSignals.map((signal) => (
                    <article key={signal.id} className="preview-signal-list__item">
                      <div className="preview-signal-list__topline">
                        <p className="preview-signal-list__title">{signal.title}</p>
                        <Badge
                          label={formatRiskLevel(signal.severity, language)}
                          tone={toneForRiskLevel(signal.severity)}
                        />
                      </div>
                      <p className="preview-signal-list__detail">{signal.description}</p>
                    </article>
                  ))}
                </div>
              </>
            ) : currentUser ? (
              <div className="analysis-result-card__hero analysis-result-card__hero--empty">
                <ScoreRing label={copy.common.ready} size="hero" state="idle" valueLabel="--" />
                <div className="analysis-result-card__summary-block">
                  <p className="analysis-result-card__headline">{copy.home.signedInReadyTitle}</p>
                  <p className="analysis-result-card__copy">{copy.home.signedInReadyCopy}</p>
                  <div className="analysis-result-card__actions">
                    <Button
                      href="#analyze-url"
                      variant="secondary"
                      onClick={() => {
                        trackResultActionClicked({
                          sourcePath: location.pathname,
                          language,
                          isAuthenticated,
                          plan: analyticsPlan,
                          action: "verify_another_link",
                          resultState: "signed_in_empty",
                        });
                      }}
                    >
                      {copy.common.verifyAnotherLink}
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="analysis-result-card__hero analysis-result-card__hero--empty">
                <ScoreRing label={copy.common.ready} size="hero" state="idle" valueLabel="--" />
                <div className="analysis-result-card__summary-block">
                  <p className="analysis-result-card__headline">{copy.home.noResultYet}</p>
                  <p className="analysis-result-card__copy">{copy.home.emptyCopy}</p>
                </div>
              </div>
            )}
          </Card>

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
        </div>
      </section>
    </PageShell>
  );
}
