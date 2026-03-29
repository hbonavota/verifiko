import { useEffect, useRef, useState } from "react";

import { AnalyzeUrlForm } from "../components/analysis/AnalyzeUrlForm";
import { EmailAuthModal } from "../components/auth/EmailAuthModal";
import { GoogleSignInButton } from "../components/auth/GoogleSignInButton";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { useAuth } from "../lib/auth";
import { listMyVerifications } from "../lib/api";
import { formatRiskLevel, formatVerdict } from "../lib/formatVerdict";
import { useI18n } from "../lib/i18n";
import { adaptApiVerification } from "../lib/verificationAdapter";
import { toneForRiskLevel } from "../lib/risk";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import type { VerificationSummary } from "../types/verification";

function cardToneForRiskLevel(riskLevel: VerificationSummary["riskLevel"]) {
  const tone = toneForRiskLevel(riskLevel);
  return tone === "warning" || tone === "danger" || tone === "success" ? tone : "default";
}

export function HomePage() {
  const { copy, language } = useI18n();
  const { authReady, currentUser } = useAuth();

  useDocumentMeta(
    copy.home.metaTitle,
    copy.home.metaDescription,
  );

  const [verifications, setVerifications] = useState<VerificationSummary[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [analysisState, setAnalysisState] = useState<"idle" | "submitting" | "error">("idle");
  const [isEmailAuthModalOpen, setIsEmailAuthModalOpen] = useState(false);
  const [emailAuthMode, setEmailAuthMode] = useState<"login" | "register">("login");
  const resultCardRef = useRef<HTMLDivElement | null>(null);

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
  const isLoadingAnalysis = analysisState === "submitting";
  const isLoadingOwnedResult = !isLoadingAnalysis && authReady && !!currentUser && isHistoryLoading;
  const isSupportingResultCard = !isLoadingAnalysis && !isLoadingOwnedResult && !latestVerification;
  const resultCardClassName = [
    "analysis-hero__result",
    latestVerification || isLoadingAnalysis || isLoadingOwnedResult ? "analysis-hero__result--live" : "",
    isSupportingResultCard ? "analysis-hero__result--supporting" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <PageShell>
      <>
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
              onStateChange={setAnalysisState}
              showProPanel={false}
            />

            {!currentUser ? (
              <div className="analysis-hero__auth-strip">
                <div className="analysis-hero__auth-copy">
                  <p className="analysis-hero__auth-title">{copy.home.authPromptTitle}</p>
                  <p className="analysis-hero__auth-description">{copy.home.authPromptCopy}</p>
                </div>
                <div className="analysis-hero__auth-actions">
                  <GoogleSignInButton className="analysis-hero__auth-google" />
                  <Button
                    onClick={() => {
                      setEmailAuthMode("login");
                      setIsEmailAuthModalOpen(true);
                    }}
                    variant="secondary"
                  >
                    {copy.topbar.signInWithEmail}
                  </Button>
                  <Button
                    onClick={() => {
                      setEmailAuthMode("register");
                      setIsEmailAuthModalOpen(true);
                    }}
                    variant="ghost"
                  >
                    {copy.topbar.createAccount}
                  </Button>
                </div>
              </div>
            ) : null}
          </Card>
        </div>

        <div ref={resultCardRef}>
          <Card
            eyebrow={isLoadingAnalysis ? copy.home.verifying : latestVerification ? copy.home.latestResult : copy.home.result}
            title={
              isLoadingAnalysis
                ? copy.home.verificationInProgress
                : latestVerification
                  ? copy.home.verificationResult
                  : copy.home.readyToVerify
            }
            description={undefined}
            tone={isLoadingAnalysis ? "success" : latestVerification ? cardToneForRiskLevel(latestVerification.riskLevel) : "default"}
            className={resultCardClassName}
          >
            {isLoadingAnalysis ? (
              <div className="analysis-result-card__hero">
                <ScoreRing label={copy.home.verifying} size="hero" state="loading" valueLabel="..." />
                <div className="analysis-result-card__summary-block">
                  <p className="analysis-result-card__headline">{copy.home.verifyingTarget}</p>
                  <p className="analysis-result-card__copy">{copy.home.collectingSignals}</p>
                  <div className="analysis-result-card__loading-stack" aria-hidden="true">
                    <span className="analysis-result-card__loading-line analysis-result-card__loading-line--strong" />
                    <span className="analysis-result-card__loading-line" />
                    <span className="analysis-result-card__loading-line analysis-result-card__loading-line--short" />
                  </div>
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
                    label={formatRiskLevel(latestVerification.riskLevel, language)}
                    tone={toneForRiskLevel(latestVerification.riskLevel)}
                  />
                </div>

                <div className="analysis-result-card__hero">
                  <ScoreRing
                    label={copy.common.trustScore}
                    riskLevel={latestVerification.riskLevel}
                    score={latestVerification.score}
                    size="hero"
                  />

                  <div className="analysis-result-card__summary-block">
                    <p className="analysis-result-card__subject" title={latestVerification.subject}>
                      {latestVerification.subject}
                    </p>
                    <p className="preview-card__label">{copy.common.result}</p>
                    <p
                      className="analysis-result-card__headline"
                      title={`${copy.common.verificationResult}: ${formatVerdict(latestVerification.verdict, language)}`}
                    >
                      {formatVerdict(latestVerification.verdict, language)}
                    </p>
                    <p className="analysis-result-card__copy">{latestVerification.executiveSummary.posture}</p>
                    <div className="analysis-result-card__actions">
                      <Button to={`/verifications/${latestVerification.id}`} variant="primary">
                        {copy.common.viewResult}
                      </Button>
                      <Button to="/dashboard" variant="secondary">
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
                      <p className="preview-signal-list__detail">{signal.reason}</p>
                    </article>
                  ))}
                </div>
              </>
            ) : currentUser ? (
              <div className="analysis-result-card__hero analysis-result-card__hero--empty">
                <ScoreRing label={copy.common.ready} state="idle" valueLabel="--" />
                <div className="analysis-result-card__summary-block">
                  <p className="analysis-result-card__headline">{copy.home.signedInReadyTitle}</p>
                  <p className="analysis-result-card__copy">{copy.home.signedInReadyCopy}</p>
                  <div className="analysis-result-card__actions">
                    <Button href="#analyze-url" variant="secondary">
                      {copy.common.verifyAnotherLink}
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="analysis-result-card__hero analysis-result-card__hero--empty">
                <ScoreRing label={copy.common.ready} state="idle" valueLabel="--" />
                <div className="analysis-result-card__summary-block">
                  <p className="analysis-result-card__headline">{copy.home.noResultYet}</p>
                  <p className="analysis-result-card__copy">{copy.home.emptyCopy}</p>
                </div>
              </div>
            )}
          </Card>
        </div>
      </section>
      <EmailAuthModal
        initialMode={emailAuthMode}
        open={isEmailAuthModalOpen}
        onClose={() => setIsEmailAuthModalOpen(false)}
      />
      </>
    </PageShell>
  );
}
