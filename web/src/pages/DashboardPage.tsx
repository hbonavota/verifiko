import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AnalyzeUrlForm } from "../components/analysis/AnalyzeUrlForm";
import { ScoreRing } from "../components/analysis/ScoreRing";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { StatPill } from "../components/ui/StatPill";
import { useAuth } from "../lib/auth";
import { createVerification, listMyVerifications } from "../lib/api";
import { formatRiskLevel, formatVerdict } from "../lib/formatVerdict";
import { useI18n } from "../lib/i18n";
import {
  copyVerificationLink,
  copyVerificationSummary,
  shareVerification,
} from "../lib/verificationActions";
import { adaptApiVerification } from "../lib/verificationAdapter";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import { toneForRiskLevel } from "../lib/risk";
import type { RiskLevel, VerificationSummary } from "../types/verification";

function toneForCount(riskLevel: RiskLevel) {
  return toneForRiskLevel(riskLevel);
}

function firstName(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }

  return trimmed.split(/\s+/)[0] ?? trimmed;
}

function formatRelativeTimestamp(value: string, locale: string, language: "en" | "es"): string {
  const timestamp = new Date(value).getTime();
  const diffSeconds = Math.round((timestamp - Date.now()) / 1000);
  const absSeconds = Math.abs(diffSeconds);
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });

  if (absSeconds < 60) {
    return language === "es" ? "hace un momento" : "just now";
  }
  if (absSeconds < 3600) {
    return formatter.format(Math.round(diffSeconds / 60), "minute");
  }
  if (absSeconds < 86400) {
    return formatter.format(Math.round(diffSeconds / 3600), "hour");
  }
  return formatter.format(Math.round(diffSeconds / 86400), "day");
}

export function DashboardPage() {
  const { copy, language, locale } = useI18n();
  const { authReady, currentUser, refreshQuotaStatus } = useAuth();
  const [verifications, setVerifications] = useState<VerificationSummary[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [copiedVerificationId, setCopiedVerificationId] = useState<string | null>(null);
  const [rerunningVerificationId, setRerunningVerificationId] = useState<string | null>(null);
  const [workspaceMessage, setWorkspaceMessage] = useState<string | null>(null);

  useDocumentMeta(
    copy.dashboard.metaTitle,
    copy.dashboard.metaDescription,
  );

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

  const activeVerification = verifications[0] ?? null;
  const showOwnedLoading = authReady && !!currentUser && isHistoryLoading;
  const workspaceOwner = currentUser ? firstName(currentUser.display_name || currentUser.email) : null;
  const latestSavedAt = activeVerification
    ? new Date(activeVerification.createdAt).toLocaleString(locale, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : copy.dashboard.noSavedYetShort;

  useEffect(() => {
    if (!copiedVerificationId) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setCopiedVerificationId(null);
    }, 1800);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [copiedVerificationId]);

  const activeReasons =
    activeVerification && activeVerification.signals.length > 0
      ? activeVerification.signals.slice(0, 3).map((signal) => signal.reason)
      : [copy.dashboard.noRecentAnalysis];

  async function handleCopyLink(verificationId: string) {
    const didCopy = await copyVerificationLink(verificationId);

    if (!didCopy) {
      setWorkspaceMessage(copy.dashboard.copyLinkUnavailable);
      return;
    }

    setCopiedVerificationId(verificationId);
    setWorkspaceMessage(null);
  }

  async function handleRerunVerification(verification: VerificationSummary) {
    setRerunningVerificationId(verification.id);
    setWorkspaceMessage(null);

    try {
      const payload = await createVerification({ url: verification.normalizedInput });
      const nextVerification = adaptApiVerification(payload, language);
      setVerifications((current) => [
        nextVerification,
        ...current.filter((item) => item.id !== nextVerification.id),
      ]);
      void refreshQuotaStatus();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : copy.dashboard.rerunFailed;
      setWorkspaceMessage(message);
    } finally {
      setRerunningVerificationId(null);
    }
  }

  async function handleShareVerification(verificationId: string) {
    const verification = verifications.find((item) => item.id === verificationId);
    if (!verification) {
      return;
    }

    const result = await shareVerification(verification, {
      language,
      locale,
      labels: {
        title: copy.detail.title,
        target: copy.common.target,
        risk: copy.common.risk,
        trustScore: copy.common.trustScore,
        verdict: copy.common.verdict,
        executedAt: copy.detail.executedAt,
        summary: copy.common.summary,
        signals: copy.detail.signalsRetained,
        link: copy.common.link,
      },
    });

    if (result === "copied") {
      setWorkspaceMessage(copy.dashboard.shareFallbackCopied);
      return;
    }

    if (result === "unavailable") {
      setWorkspaceMessage(copy.dashboard.copyLinkUnavailable);
      return;
    }

    if (result === "shared") {
      setWorkspaceMessage(null);
    }
  }

  async function handleExportSummary(verification: VerificationSummary) {
    const didCopy = await copyVerificationSummary(verification, {
      language,
      locale,
      labels: {
        title: copy.detail.title,
        target: copy.common.target,
        risk: copy.common.risk,
        trustScore: copy.common.trustScore,
        verdict: copy.common.verdict,
        executedAt: copy.detail.executedAt,
        summary: copy.common.summary,
        signals: copy.detail.signalsRetained,
        link: copy.common.link,
      },
    });

    setWorkspaceMessage(
      didCopy ? copy.dashboard.exportTextCopied : copy.dashboard.copyLinkUnavailable,
    );
  }

  return (
    <PageShell>
      <SectionTitle
        eyebrow={copy.dashboard.eyebrow}
        title={copy.dashboard.title}
        description={copy.dashboard.description}
      />

      {currentUser ? (
        <section className="dashboard-workspace-banner" aria-label={copy.dashboard.workspaceEyebrow}>
          <div className="dashboard-workspace-banner__copy">
            <p className="dashboard-workspace-banner__eyebrow">{copy.dashboard.workspaceEyebrow}</p>
            <p className="dashboard-workspace-banner__owner">{workspaceOwner}</p>
            <p className="dashboard-workspace-banner__description">{copy.dashboard.workspaceDescription}</p>
          </div>

          <div className="dashboard-workspace-banner__stats">
            <StatPill
              label={copy.dashboard.savedVerifications}
              value={String(verifications.length)}
              tone="primary"
            />
            <StatPill
              label={copy.dashboard.latestVerdictLabel}
              value={
                activeVerification
                  ? formatRiskLevel(activeVerification.riskLevel, language)
                  : copy.dashboard.empty
              }
              tone={activeVerification ? toneForRiskLevel(activeVerification.riskLevel) : "neutral"}
            />
            <StatPill
              label={copy.dashboard.lastSavedLabel}
              value={latestSavedAt}
              tone="neutral"
            />
          </div>
        </section>
      ) : null}

      <Card
        eyebrow={copy.dashboard.newVerification}
        title={copy.dashboard.verifyAnotherLink}
        description={undefined}
        tone="success"
        id="verifications"
        className="dashboard-intake-card"
      >
        <AnalyzeUrlForm
          buttonLabel={copy.analyzeForm.buttonLabel}
          className="dashboard-intake"
          hint={copy.analyzeForm.hint}
          inputClassName="dashboard-intake__input-control"
          inputLabel={copy.dashboard.link}
          placeholder={copy.analyzeForm.placeholder}
        />
      </Card>

      <Card
        eyebrow={copy.dashboard.latestResult}
        title={
          activeVerification
            ? copy.common.trustScore
            : currentUser
              ? copy.dashboard.emptySignedInTitle
              : copy.dashboard.noAnalysesYet
        }
        description={undefined}
        tone="warning"
        className="dashboard-assessment-card"
      >
        {showOwnedLoading ? (
          <div className="dashboard-card-stack">
            <div className="dashboard-card-headline">
              <div>
                <p className="metric-card__label">{copy.dashboard.latestResult}</p>
                <p className="dashboard-card__target">{copy.dashboard.loadingHistoryTitle}</p>
              </div>
              <Badge label={copy.common.loadingResult.toUpperCase()} tone="primary" />
            </div>
            <p className="metric-card__detail">{copy.dashboard.loadingHistoryCopy}</p>
          </div>
        ) : activeVerification ? (
          <div className="dashboard-card-stack">
            <div className="dashboard-assessment-card__hero">
              <ScoreRing
                label={copy.common.trustScore}
                riskLevel={activeVerification.riskLevel}
                score={activeVerification.score}
                size="hero"
              />
              <div className="dashboard-assessment-card__summary">
                <p className="dashboard-card__subject" title={activeVerification.subject}>
                  {activeVerification.subject}
                </p>
                <div className="dashboard-card__status-row">
                  <Badge
                    label={formatRiskLevel(activeVerification.riskLevel, language)}
                    tone={toneForRiskLevel(activeVerification.riskLevel)}
                  />
                </div>
                <p className="metric-card__label">{copy.dashboard.verdict}</p>
                <p
                  className="dashboard-card__verdict"
                  title={`${copy.common.verificationResult}: ${formatVerdict(activeVerification.verdict, language)}`}
                >
                  {formatVerdict(activeVerification.verdict, language)}
                </p>
                <p className="dashboard-card__posture">{activeVerification.executiveSummary.posture}</p>
                <div className="dashboard-assessment-card__actions">
                  <Button to={`/verifications/${activeVerification.id}`} variant="primary">
                    {copy.common.viewResult}
                  </Button>
                </div>
              </div>
            </div>

            <div className="dashboard-card-headline dashboard-card-headline--muted">
              <div className="dashboard-card-pills">
                <StatPill label={copy.dashboard.signalsCount} value={String(activeVerification.signals.length)} tone="warning" />
                <StatPill label={copy.dashboard.openQuestions} value={String(activeVerification.inconclusive.length)} tone="danger" />
              </div>
            </div>
          </div>
        ) : currentUser ? (
          <div className="dashboard-card-stack">
            <div className="dashboard-card-headline">
              <div>
                <p className="metric-card__label">{copy.dashboard.latestResult}</p>
                <p className="dashboard-card__target">{copy.dashboard.emptySignedInTitle}</p>
              </div>
              <Badge label={copy.common.ready.toUpperCase()} tone="primary" />
            </div>
            <p className="metric-card__detail">{copy.dashboard.emptySignedInCopy}</p>
            <div className="dashboard-assessment-card__actions">
              <Button to="/#analyze-url" variant="primary">
                {copy.dashboard.emptySignedInAction}
              </Button>
            </div>
          </div>
        ) : (
          <div className="dashboard-card-stack">
            <div className="dashboard-card-headline">
              <div>
                <p className="metric-card__label">{copy.dashboard.status}</p>
                <p className="dashboard-card__target">{copy.dashboard.readyForFirstVerification}</p>
              </div>
              <Badge label={copy.dashboard.empty.toUpperCase()} tone="neutral" />
            </div>
          </div>
        )}
      </Card>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <Card
            eyebrow={copy.dashboard.signalBreakdown}
            title={activeVerification ? copy.dashboard.signalsInThisResult : copy.dashboard.signalsUnavailable}
            description={undefined}
            id="signals"
          >
            {activeVerification ? (
              <div className="signal-table-wrap">
                <div className="signal-table">
                  <div className="signal-table__header">
                    <span>{copy.dashboard.signalName}</span>
                    <span>{copy.dashboard.category}</span>
                    <span>{copy.dashboard.severity}</span>
                    <span>{copy.dashboard.confidence}</span>
                    <span>{copy.dashboard.scoreContribution}</span>
                    <span>{copy.dashboard.status}</span>
                  </div>
                  {activeVerification.signals.map((signal) => (
                    <article key={signal.id} className="signal-table__row">
                      <div className="signal-table__identity">
                        <p className="signal-table__name">{signal.title}</p>
                        <p className="signal-table__subcopy">{signal.description}</p>
                      </div>
                      <span className="signal-table__value" data-label={copy.dashboard.category}>
                        {signal.category}
                      </span>
                      <div className="signal-table__cell" data-label={copy.dashboard.severity}>
                        <Badge
                          label={formatRiskLevel(signal.severity, language)}
                          tone={toneForRiskLevel(signal.severity)}
                        />
                      </div>
                      <span className="signal-table__value" data-label={copy.dashboard.confidence}>
                        {signal.confidence}%
                      </span>
                      <span className="signal-table__value" data-label={copy.dashboard.scoreContribution}>
                        -{signal.scoreContribution}
                      </span>
                      <div className="signal-table__cell" data-label={copy.dashboard.status}>
                        <Badge label={signal.status} tone={toneForRiskLevel(signal.severity)} />
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <p className="metric-card__detail">{copy.dashboard.noResultAvailableYet}</p>
            )}
          </Card>

          <section className="dashboard-inspection-grid">
            <Card
              eyebrow={copy.dashboard.whyFlagged}
              title={copy.dashboard.mostInfluentialSignals}
              description={undefined}
            >
              <div className="support-list">
                {activeReasons.map((reason, index) => (
                  <article key={reason} className="support-list__item support-list__item--plain">
                    <div>
                      <p className="support-list__title">{`${copy.dashboard.materialFactor} ${index + 1}`}</p>
                      <p className="support-list__description">{reason}</p>
                    </div>
                  </article>
                ))}
              </div>
            </Card>

            <Card
              eyebrow={copy.dashboard.evidenceSnapshot}
              title={copy.dashboard.evidenceSnapshotTitle}
              description={undefined}
            >
              {activeVerification ? (
                <div className="evidence-grid">
                  <div className="evidence-block">
                    <p className="evidence-block__label">{copy.dashboard.observed}</p>
                    <ul className="evidence-block__list">
                      {activeVerification.evidenceSummary.observed.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="evidence-block">
                    <p className="evidence-block__label">{copy.dashboard.sources}</p>
                    <ul className="evidence-block__list">
                      {activeVerification.evidenceSummary.sources.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="evidence-block">
                    <p className="evidence-block__label">{copy.dashboard.unresolved}</p>
                    <ul className="evidence-block__list">
                      {activeVerification.evidenceSummary.unresolved.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <p className="metric-card__detail">{copy.dashboard.evidenceAppearsLater}</p>
              )}
            </Card>
          </section>

          <Card
            eyebrow={copy.dashboard.decisionTrace}
            title={copy.dashboard.scoreGenerationSequence}
            description={undefined}
            id="cases"
          >
            {activeVerification ? (
              <div className="decision-trace">
                {activeVerification.decisionTrace.map((step) => (
                  <article key={step.id} className="decision-trace__item">
                    <div className="decision-trace__marker" />
                    <div className="decision-trace__content">
                      <p className="decision-trace__label">{step.label}</p>
                      <p className="decision-trace__detail">{step.detail}</p>
                      <p className="decision-trace__outcome">{step.outcome}</p>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="metric-card__detail">{copy.dashboard.decisionTraceAppearsLater}</p>
            )}
          </Card>

          <Card
            eyebrow={copy.dashboard.caseRecommendation}
            title={copy.dashboard.suggestedNextAction}
            description={undefined}
            tone="warning"
          >
            {activeVerification ? (
              <div className="recommendation-panel">
                <p className="recommendation-panel__headline">{activeVerification.recommendation.title}</p>
                <p className="recommendation-panel__copy">{activeVerification.recommendation.detail}</p>
              </div>
            ) : (
              <p className="metric-card__detail">{copy.dashboard.recommendationAppearsLater}</p>
            )}
          </Card>
        </div>

        <aside className="dashboard-rail">
          <Card
            eyebrow={currentUser ? copy.dashboard.privateLibraryEyebrow : copy.dashboard.recentAnalyses}
            title={currentUser ? copy.dashboard.privateLibraryTitle : copy.dashboard.latestResults}
            description={currentUser ? copy.dashboard.privateLibraryDescription : undefined}
            action={
              currentUser && verifications.length > 0 ? (
                <Badge
                  label={`${verifications.length} ${copy.dashboard.savedResultsLabel}`}
                  tone="primary"
                />
              ) : undefined
            }
            className="dashboard-rail-card"
          >
            {showOwnedLoading ? (
              <div className="dashboard-history-skeleton" aria-hidden="true">
                {Array.from({ length: 3 }).map((_, index) => (
                  <div key={`history-skeleton-${index}`} className="dashboard-history-skeleton__item">
                    <span className="dashboard-history-skeleton__line dashboard-history-skeleton__line--eyebrow" />
                    <span className="dashboard-history-skeleton__line dashboard-history-skeleton__line--title" />
                    <span className="dashboard-history-skeleton__line" />
                    <span className="dashboard-history-skeleton__line dashboard-history-skeleton__line--short" />
                  </div>
                ))}
              </div>
            ) : verifications.length > 0 ? (
              <div className="activity-feed">
                {verifications.slice(0, 5).map((verification, index) => (
                  <article
                    key={verification.id}
                    className={`activity-feed__item activity-feed__item--saved${index === 0 ? " activity-feed__item--latest" : ""}`}
                  >
                    <p className="activity-feed__eyebrow">
                      {index === 0 ? copy.dashboard.latestSavedTag : copy.dashboard.savedResultTag}
                    </p>
                    <div className="activity-feed__row">
                      <Link
                        className="activity-feed__title-link"
                        title={verification.subject}
                        to={`/verifications/${verification.id}`}
                      >
                        <p className="activity-feed__title" title={verification.subject}>{verification.subject}</p>
                      </Link>
                      <div className="activity-feed__status">
                        <Badge
                          label={formatRiskLevel(verification.riskLevel, language)}
                          tone={toneForCount(verification.riskLevel)}
                        />
                        <p className="activity-feed__verdict">
                          {formatVerdict(verification.verdict, language)}
                        </p>
                      </div>
                    </div>
                    <div className="activity-feed__meta">
                      <p
                        className="activity-feed__timestamp"
                        title={new Date(verification.createdAt).toLocaleString(locale)}
                      >
                        {formatRelativeTimestamp(verification.createdAt, locale, language)}
                      </p>
                      <p className="activity-feed__meta-copy">
                        {copy.dashboard.signalsCaptured.replace(
                          "{count}",
                          String(verification.signals.length),
                        )}
                      </p>
                    </div>
                    <p className="activity-feed__detail">{verification.summary}</p>
                    <div className="activity-feed__footer">
                      <div className="activity-feed__actions">
                        <Button to={`/verifications/${verification.id}`} variant="secondary">
                          {copy.dashboard.openAction}
                        </Button>
                        <Button
                          onClick={() => void handleCopyLink(verification.id)}
                          variant="ghost"
                        >
                          {copiedVerificationId === verification.id
                            ? copy.dashboard.copiedAction
                            : copy.dashboard.copyLinkAction}
                        </Button>
                        <Button
                          onClick={() => void handleExportSummary(verification)}
                          variant="ghost"
                        >
                          {copy.dashboard.exportTextAction}
                        </Button>
                        <Button
                          disabled={rerunningVerificationId === verification.id}
                          onClick={() => void handleRerunVerification(verification)}
                          variant="ghost"
                        >
                          {rerunningVerificationId === verification.id
                            ? copy.dashboard.rerunningAction
                            : copy.dashboard.rerunAction}
                        </Button>
                        <Button
                          onClick={() => void handleShareVerification(verification.id)}
                          variant="ghost"
                        >
                          {copy.dashboard.shareAction}
                        </Button>
                      </div>
                    </div>
                  </article>
                ))}
                {workspaceMessage ? (
                  <p className="dashboard-workspace-message" role="status">
                    {workspaceMessage}
                  </p>
                ) : null}
              </div>
            ) : currentUser ? (
              <div className="dashboard-history-empty">
                <p className="recommendation-panel__headline">{copy.dashboard.noVerificationsYetTitle}</p>
                <p className="notes-panel__text">{copy.dashboard.noVerificationsYetCopy}</p>
                <div className="dashboard-action-stack">
                  <Button href="#verifications" variant="primary">
                    {copy.dashboard.emptySignedInAction}
                  </Button>
                </div>
              </div>
            ) : (
              <p className="metric-card__detail">{copy.common.noResultsYet}</p>
            )}
          </Card>

          <Card
            eyebrow={copy.dashboard.suggestedNextStep}
            title={copy.dashboard.whatToDoNext}
            description={undefined}
            tone="warning"
            className="dashboard-rail-card"
          >
            {activeVerification ? (
              <div className="notes-panel">
                <p className="recommendation-panel__headline">{activeVerification.recommendation.title}</p>
                <p className="notes-panel__text">{activeVerification.recommendation.detail}</p>
                <div className="dashboard-action-stack">
                  <Button to={`/verifications/${activeVerification.id}`} variant="primary">
                    {copy.dashboard.openSavedResult}
                  </Button>
                  <Button href="#verifications" variant="secondary">
                    {copy.dashboard.verifyAnotherLink}
                  </Button>
                </div>
                <p className="notes-panel__meta">{activeVerification.executiveSummary.operationalImpact}</p>
              </div>
            ) : currentUser ? (
              <div className="notes-panel">
                <p className="recommendation-panel__headline">{copy.dashboard.emptySignedInTitle}</p>
                <p className="notes-panel__text">{copy.dashboard.emptySignedInCopy}</p>
                <div className="dashboard-action-stack">
                  <Button href="#verifications" variant="primary">
                    {copy.dashboard.emptySignedInAction}
                  </Button>
                </div>
              </div>
            ) : (
              <p className="metric-card__detail">{copy.dashboard.nextStepAppearsLater}</p>
            )}
          </Card>
        </aside>
      </section>
    </PageShell>
  );
}
