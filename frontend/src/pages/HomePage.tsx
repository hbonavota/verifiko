import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import { SectionTitle } from "../components/ui/SectionTitle";

const credibilityPillars = [
  {
    title: "Explainable",
    description:
      "Risk output is decomposed into individual signals, category penalties, and a readable summary.",
  },
  {
    title: "Operational",
    description:
      "The interface is framed for review work, escalation decisions, and evidence handoff, not vanity metrics.",
  },
  {
    title: "Composable",
    description:
      "Backend capabilities are exposed as clear services and routes that can be surfaced in focused product flows.",
  },
  {
    title: "Pragmatic",
    description:
      "Verifiko favors traceable signals, calm UX, and explicit tradeoffs over speculative automation language.",
  },
];

const credibilityChips = [
  "FastAPI",
  "PostgreSQL-ready",
  "Hexagonal architecture",
  "Explainable signals",
] as const;

const scoreBreakdown = [
  { label: "Domain structure", value: 21, tone: "danger" },
  { label: "Content behavior", value: 18, tone: "warning" },
  { label: "Navigation behavior", value: 11, tone: "neutral" },
] as const;

const previewSignals = [
  {
    title: "Brand impersonation",
    detail: "Visual identity and login framing align too closely with the legitimate destination.",
    tone: "danger" as const,
  },
  {
    title: "Credential lure language",
    detail: "Action prompts are optimized for rapid credential submission rather than navigation clarity.",
    tone: "warning" as const,
  },
  {
    title: "Redirect mismatch",
    detail: "Observed path behavior introduces a destination shift before the form experience resolves.",
    tone: "neutral" as const,
  },
] as const;

const verificationSteps = [
  {
    title: "Normalize the target",
    description:
      "Inputs are normalized into a consistent verification object so downstream analysis uses a stable representation.",
  },
  {
    title: "Collect signals",
    description:
      "Signals describe concrete observations such as structure anomalies, content cues, redirects, and reputation context.",
  },
  {
    title: "Score with traceability",
    description:
      "Category penalties and compound rules shape the score while preserving a readable explanation of why it moved.",
  },
] as const;

const explainabilityPoints = [
  {
    title: "Review confidence depends on traceable reasoning",
    description:
      "Analysts need to understand which signals drove a score and which ones are still inconclusive before taking action.",
  },
  {
    title: "Operational teams need defensible outputs",
    description:
      "A verification result should support escalation, monitoring, or blocking decisions without turning into a black box.",
  },
] as const;

export function HomePage() {
  useDocumentMeta(
    "Overview",
    "Verifiko is an explainable verification workspace for suspicious digital content, focused on evidence traceability and operational clarity.",
  );

  return (
    <PageShell>
      <section className="landing-hero">
        <div className="landing-hero__content">
          <SectionTitle
            eyebrow="Signal-based verification backend"
            title="Explainable risk assessment for suspicious digital content"
            description="Verifiko is designed for verification workflows where analysts need more than a score. It emphasizes explainable signals, evidence traceability, and operational clarity so suspicious content can be reviewed with context instead of guesswork."
          />

          <div className="hero-panel">
            <div className="hero-panel__body">
              <p className="hero-panel__eyebrow">Product posture</p>
              <h2 className="hero-panel__title">
                Built for reviewability, scoring transparency, and evidence-first decision support.
              </h2>
              <p className="hero-panel__copy">
                The frontend frames the existing backend as a serious internal tool or early SaaS
                product surface, with enough structure to communicate how verification results can
                be interpreted, challenged, and acted on.
              </p>
            </div>
            <div className="hero-panel__actions">
              <Button to="/dashboard" variant="primary">
                Start analysis
              </Button>
              <Button to="/api-health" variant="secondary">
                View API health
              </Button>
            </div>
          </div>

          <div className="landing-chip-row" aria-label="Technology and credibility markers">
            {credibilityChips.map((chip) => (
              <Badge key={chip} label={chip} tone="primary" />
            ))}
          </div>
        </div>

        <Card
          eyebrow="Verification preview"
          title="Verification result preview"
          description="Representative example of how a single verification can be reviewed with score context, evidence, and reasoning."
          tone="warning"
        >
          <div className="preview-card__topline">
            <div>
              <p className="preview-card__label">Run ID</p>
              <p className="preview-card__run-id">vrf-2026-0315-018</p>
            </div>
            <Badge label="MEDIUM RISK" tone="warning" />
          </div>

          <div className="preview-card__score-block">
            <div>
              <p className="preview-card__label">Risk score</p>
              <p className="preview-card__score">58</p>
            </div>
            <p className="preview-card__summary">
              Signals indicate meaningful suspicious behavior, but the current evidence does not yet
              justify a terminal malicious disposition.
            </p>
          </div>

          <div className="breakdown-list">
            {scoreBreakdown.map((item) => (
              <div key={item.label} className="breakdown-list__row">
                <div className="breakdown-list__labels">
                  <span>{item.label}</span>
                  <span>{item.value}</span>
                </div>
                <div className="breakdown-list__track">
                  <div
                    className={`breakdown-list__fill breakdown-list__fill--${item.tone}`}
                    style={{ width: `${item.value * 3}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="preview-signal-list">
            {previewSignals.map((signal) => (
              <article key={signal.title} className="preview-signal-list__item">
                <div className="preview-signal-list__topline">
                  <p className="preview-signal-list__title">{signal.title}</p>
                  <Badge label="Observed" tone={signal.tone} />
                </div>
                <p className="preview-signal-list__detail">{signal.detail}</p>
              </article>
            ))}
          </div>

          <div className="preview-evidence">
            <p className="preview-card__label">Evidence summary</p>
            <p className="preview-evidence__text">
              Page styling, action language, and redirect behavior collectively suggest a suspicious
              credential collection flow. Additional infrastructure context would refine confidence.
            </p>
          </div>
        </Card>
      </section>

      <section className="card-grid card-grid--four">
        {credibilityPillars.map((item) => (
          <Card key={item.title} eyebrow="Credibility" title={item.title} description={item.description} />
        ))}
      </section>

      <section className="support-grid">
        <Card
          eyebrow="How verification works"
          title="A clear path from input to explainable result"
          description="The backend already carries the core verification and scoring logic. The frontend surface is meant to present that logic in a review-friendly form."
        >
          <div className="support-list">
            {verificationSteps.map((step, index) => (
              <article key={step.title} className="support-list__item">
                <div className="support-list__index">{index + 1}</div>
                <div>
                  <p className="support-list__title">{step.title}</p>
                  <p className="support-list__description">{step.description}</p>
                </div>
              </article>
            ))}
          </div>
        </Card>

        <Card
          eyebrow="Why explainability matters"
          title="Readable reasoning makes verification results usable"
          description="Verifiko treats explainability as an operational requirement rather than a decorative claim."
        >
          <div className="support-list">
            {explainabilityPoints.map((point) => (
              <article key={point.title} className="support-list__item support-list__item--plain">
                <div>
                  <p className="support-list__title">{point.title}</p>
                  <p className="support-list__description">{point.description}</p>
                </div>
              </article>
            ))}
          </div>
        </Card>
      </section>
    </PageShell>
  );
}
