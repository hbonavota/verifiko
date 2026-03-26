import { useEffect, useState } from "react";

import { AnalyzeUrlForm } from "../components/analysis/AnalyzeUrlForm";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { listVerifications } from "../lib/api";
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
  useDocumentMeta(
    "Analyze URL",
    "Analyze suspicious URLs with a focused verification flow and inspect the latest result in Verifiko.",
  );

  const [verifications, setVerifications] = useState<VerificationSummary[]>([]);
  const [analysisState, setAnalysisState] = useState<"idle" | "submitting" | "error">("idle");

  useEffect(() => {
    let isMounted = true;

    async function loadVerifications() {
      try {
        const payload = await listVerifications();
        if (!isMounted) {
          return;
        }

        setVerifications(payload.map(adaptApiVerification));
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
  }, []);

  const latestVerification = verifications[0] ?? null;
  const latestSignals = latestVerification?.signals.slice(0, 2) ?? [];
  const isLoadingAnalysis = analysisState === "submitting";

  return (
    <PageShell>
      <section className="analysis-hero">
        <div className="analysis-hero__content" id="analyze-url">
          <SectionTitle
            eyebrow="Verifiko"
            title="Paste a URL. Read the score."
            description="One clear action. One clear result."
          />

          <Card className="analysis-hero__panel" tone="success">
            <div className="analysis-hero__panel-copy">
              <p className="hero-panel__eyebrow">Analyze URL</p>
              <h2 className="hero-panel__title">Fast input. Immediate visual feedback.</h2>
              <p className="hero-panel__copy">Paste the target and let the result take over.</p>
            </div>

            <AnalyzeUrlForm
              buttonLabel="Analyze URL"
              buttonClassName="analysis-form__button analysis-form__button--hero"
              className="analysis-form--hero"
              hint="Suspicious URL or hostname."
              inputClassName="analysis-form__input-control"
              onStateChange={setAnalysisState}
            />
          </Card>
        </div>

        <Card
          eyebrow={isLoadingAnalysis ? "Analysis in progress" : "Result"}
          title={
            isLoadingAnalysis
              ? "Running analysis"
              : latestVerification
                ? latestVerification.subject
                : "Ready for the next URL"
          }
          description={
            isLoadingAnalysis
              ? "Collecting the signals behind the result."
              : latestVerification
              ? latestVerification.summary
              : "The main result appears here with the score, verdict, and strongest retained signals."
          }
          tone={isLoadingAnalysis ? "success" : latestVerification ? cardToneForRiskLevel(latestVerification.riskLevel) : "default"}
          className="analysis-hero__result"
        >
          {isLoadingAnalysis ? (
            <div className="analysis-result-card__hero">
              <ScoreRing label="Analyzing" size="hero" state="loading" valueLabel="..." />
              <div className="analysis-result-card__summary-block">
                <p className="analysis-result-card__headline">Running verification</p>
                <p className="analysis-result-card__copy">
                  Verifiko is preparing the score, verdict, and retained signals.
                </p>
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
                <Badge label={latestVerification.riskLevel} tone={toneForRiskLevel(latestVerification.riskLevel)} />
                <p className="analysis-result-card__run-id">{latestVerification.id}</p>
              </div>

              <div className="analysis-result-card__hero">
                <ScoreRing
                  label="Trust score"
                  riskLevel={latestVerification.riskLevel}
                  score={latestVerification.score}
                  size="hero"
                />

                <div className="analysis-result-card__summary-block">
                  <p className="preview-card__label">Current posture</p>
                  <p className="analysis-result-card__headline">{latestVerification.verdict}</p>
                  <p className="analysis-result-card__copy">{latestVerification.executiveSummary.posture}</p>
                  <div className="analysis-result-card__actions">
                    <Button to={`/verifications/${latestVerification.id}`} variant="primary">
                      Open result
                    </Button>
                    <Button to="/dashboard" variant="secondary">
                      Open review
                    </Button>
                  </div>
                </div>
              </div>

              <div className="analysis-result-card__signals">
                <p className="preview-card__label">Top signals</p>
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
              <ScoreRing label="Awaiting result" size="hero" state="idle" valueLabel="--" />
              <div className="analysis-result-card__summary-block">
                <p className="analysis-result-card__headline">No analysis yet</p>
                <p className="analysis-result-card__copy">
                  Paste a URL above and the score will appear here.
                </p>
              </div>
            </div>
          )}
        </Card>
      </section>
    </PageShell>
  );
}
