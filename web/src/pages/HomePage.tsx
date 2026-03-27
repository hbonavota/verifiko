import { useEffect, useRef, useState } from "react";

import { AnalyzeUrlForm } from "../components/analysis/AnalyzeUrlForm";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { listVerifications } from "../lib/api";
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

  useDocumentMeta(
    copy.home.metaTitle,
    copy.home.metaDescription,
  );

  const [verifications, setVerifications] = useState<VerificationSummary[]>([]);
  const [analysisState, setAnalysisState] = useState<"idle" | "submitting" | "error">("idle");
  const resultCardRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadVerifications() {
      try {
        const payload = await listVerifications();
        if (!isMounted) {
          return;
        }

        setVerifications(payload.map((verification) => adaptApiVerification(verification, language)));
      } catch {
        if (!isMounted) {
          return;
        }

        setVerifications([]);
      }
    }

    void loadVerifications();

    return () => {
      isMounted = false;
    };
  }, [language]);

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
              hint={copy.analyzeForm.hint}
              inputClassName="analysis-form__input-control"
              onStateChange={setAnalysisState}
            />
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
            className="analysis-hero__result"
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
                        <Badge label={signal.severity} tone={toneForRiskLevel(signal.severity)} />
                      </div>
                      <p className="preview-signal-list__detail">{signal.reason}</p>
                    </article>
                  ))}
                </div>
              </>
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
        </div>
      </section>
    </PageShell>
  );
}
