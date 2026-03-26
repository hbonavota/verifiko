import { useEffect, useRef, useState } from "react";

import { AnalyzeUrlForm } from "../components/analysis/AnalyzeUrlForm";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { listVerifications } from "../lib/api";
import { formatVerdict } from "../lib/formatVerdict";
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
    "Verify Link",
    "Verify a link and review the latest result in Verifiko.",
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
            eyebrow="Verifiko"
            title="Verify links before you trust them."
            description="Get a clear security verdict."
          />

          <Card className="analysis-hero__panel" tone="success">
            <p className="hero-panel__eyebrow">Start verification</p>

            <AnalyzeUrlForm
              buttonLabel="Verify this link"
              buttonClassName="analysis-form__button analysis-form__button--hero"
              className="analysis-form--hero"
              hint="Paste a link to verify its safety."
              inputClassName="analysis-form__input-control"
              onStateChange={setAnalysisState}
            />
          </Card>
        </div>

        <div ref={resultCardRef}>
          <Card
            eyebrow={isLoadingAnalysis ? "Verifying" : latestVerification ? "Latest result" : "Result"}
            title={
              isLoadingAnalysis
                ? "Verification in progress"
                : latestVerification
                  ? "Verification result"
                  : "Ready to verify"
            }
            description={undefined}
            tone={isLoadingAnalysis ? "success" : latestVerification ? cardToneForRiskLevel(latestVerification.riskLevel) : "default"}
            className="analysis-hero__result"
          >
            {isLoadingAnalysis ? (
              <div className="analysis-result-card__hero">
                <ScoreRing label="Verifying" size="hero" state="loading" valueLabel="..." />
                <div className="analysis-result-card__summary-block">
                  <p className="analysis-result-card__headline">Verifying target</p>
                  <p className="analysis-result-card__copy">Collecting signals.</p>
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
                </div>

                <div className="analysis-result-card__hero">
                  <ScoreRing
                    label="Trust score"
                    riskLevel={latestVerification.riskLevel}
                    score={latestVerification.score}
                    size="hero"
                  />

                  <div className="analysis-result-card__summary-block">
                    <p className="analysis-result-card__subject" title={latestVerification.subject}>
                      {latestVerification.subject}
                    </p>
                    <p className="preview-card__label">Result</p>
                    <p
                      className="analysis-result-card__headline"
                      title={`Verification result: ${formatVerdict(latestVerification.verdict)}`}
                    >
                      {formatVerdict(latestVerification.verdict)}
                    </p>
                    <p className="analysis-result-card__copy">{latestVerification.executiveSummary.posture}</p>
                    <div className="analysis-result-card__actions">
                      <Button to={`/verifications/${latestVerification.id}`} variant="primary">
                        View result
                      </Button>
                      <Button to="/dashboard" variant="secondary">
                        Review signals
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="analysis-result-card__signals">
                  <p className="preview-card__label">Signals</p>
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
                  <p className="analysis-result-card__headline">No result yet</p>
                  <p className="analysis-result-card__copy">
                    Enter a link to check if it&apos;s safe or potentially malicious.
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>
      </section>
    </PageShell>
  );
}
