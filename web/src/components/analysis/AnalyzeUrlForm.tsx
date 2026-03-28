import { useEffect, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { GoogleSignInButton } from "../auth/GoogleSignInButton";
import { useAuth } from "../../lib/auth";
import type { ApiQuotaStatus } from "../../types/verification";
import { ApiRequestError, createVerification } from "../../lib/api";
import {
  categorizeAnalysisError,
  detectDegradedCoverage,
  trackAnalysisCompleted,
  trackAnalysisFailed,
  trackAnalysisStarted,
} from "../../lib/analytics";
import { adaptApiVerification } from "../../lib/verificationAdapter";
import { useI18n } from "../../lib/i18n";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";

function PasteIcon() {
  return (
    <svg
      aria-hidden="true"
      className="analysis-form__paste-icon"
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M7.5 4.16667H6.16667C5.24619 4.16667 4.5 4.91286 4.5 5.83333V14.1667C4.5 15.0871 5.24619 15.8333 6.16667 15.8333H12.8333C13.7538 15.8333 14.5 15.0871 14.5 14.1667V12.8333"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
      <path
        d="M8.83333 10.8333L14.9167 4.75M14.9167 4.75H10.5M14.9167 4.75V9.16667"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
    </svg>
  );
}

interface AnalyzeUrlFormProps {
  buttonLabel?: string;
  buttonClassName?: string;
  className?: string;
  errorClassName?: string;
  hint?: string;
  inputClassName?: string;
  inputLabel?: string;
  onStateChange?: (state: "idle" | "submitting" | "error") => void;
  placeholder?: string;
  submittingLabel?: string;
}

export function AnalyzeUrlForm({
  buttonLabel,
  buttonClassName,
  className,
  errorClassName,
  hint,
  inputClassName,
  inputLabel,
  onStateChange,
  placeholder,
  submittingLabel,
}: AnalyzeUrlFormProps) {
  const { copy, language } = useI18n();
  const { currentUser, quotaStatus, refreshQuotaStatus } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [analysisTarget, setAnalysisTarget] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [quotaExceededRetryAfter, setQuotaExceededRetryAfter] = useState<number | null>(null);
  const [quotaExceededPlan, setQuotaExceededPlan] = useState<ApiQuotaStatus["plan"] | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isQuotaRetrying, setIsQuotaRetrying] = useState(false);
  const [inputType, setInputType] = useState<"manual" | "paste">("manual");

  const resolvedButtonLabel = buttonLabel ?? copy.analyzeForm.buttonLabel;
  const resolvedHint = hint ?? copy.analyzeForm.hint;
  const resolvedInputLabel = inputLabel ?? copy.analyzeForm.inputLabel;
  const resolvedPlaceholder = placeholder ?? copy.analyzeForm.placeholder;
  const resolvedSubmittingLabel = submittingLabel ?? copy.analyzeForm.submittingLabel;

  useEffect(() => {
    if (currentUser && quotaExceededRetryAfter === null && !isQuotaRetrying) {
      setSubmitError(null);
      setQuotaExceededRetryAfter(null);
      setQuotaExceededPlan(null);
      onStateChange?.("idle");
    }
  }, [currentUser, isQuotaRetrying, onStateChange, quotaExceededRetryAfter]);

  async function handlePaste() {
    if (!navigator.clipboard?.readText) {
      setSubmitError(copy.analyzeForm.errors.clipboardUnavailable);
      setQuotaExceededRetryAfter(null);
      setQuotaExceededPlan(null);
      return;
    }

    try {
      const clipboardValue = (await navigator.clipboard.readText()).trim();
      if (!clipboardValue) {
        setSubmitError(copy.analyzeForm.errors.clipboardEmpty);
        setQuotaExceededRetryAfter(null);
        setQuotaExceededPlan(null);
        return;
      }

      setAnalysisTarget(clipboardValue);
      setInputType("paste");
      setSubmitError(null);
      setQuotaExceededRetryAfter(null);
      setQuotaExceededPlan(null);
      onStateChange?.("idle");
    } catch {
      setSubmitError(copy.analyzeForm.errors.clipboardBlocked);
      setQuotaExceededRetryAfter(null);
      setQuotaExceededPlan(null);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedTarget = analysisTarget.trim();
    if (!trimmedTarget) {
      setSubmitError(copy.analyzeForm.errors.enterUrl);
      setQuotaExceededRetryAfter(null);
      setQuotaExceededPlan(null);
      onStateChange?.("error");
      return;
    }

    await submitVerification(trimmedTarget, inputType);
  }

  async function submitVerification(
    target: string,
    submissionInputType: "manual" | "paste",
    options?: { preserveQuotaState?: boolean },
  ) {
    setIsSubmitting(true);
    if (!options?.preserveQuotaState) {
      setSubmitError(null);
      setQuotaExceededRetryAfter(null);
      setQuotaExceededPlan(null);
    }
    onStateChange?.("submitting");
    trackAnalysisStarted({
      sourcePage: location.pathname,
      language,
      inputType: submissionInputType,
      hasProtocol: /^https?:\/\//i.test(target),
    });

    try {
      const verification = await createVerification({ url: target });
      const adaptedVerification = adaptApiVerification(verification, language);

      if (verification.status === "COMPLETED" && verification.risk_assessment) {
        trackAnalysisCompleted({
          sourcePage: location.pathname,
          language,
          riskLevel: adaptedVerification.riskLevel,
          verdict: adaptedVerification.verdict,
          signalCount: verification.signals.length,
          warningCount: adaptedVerification.inconclusive.length,
          hasFetchDegradation: detectDegradedCoverage(verification),
        });
      } else if (verification.status === "FAILED") {
        trackAnalysisFailed({
          sourcePage: location.pathname,
          language,
          errorType: "analysis_failed",
        });
      }

      void refreshQuotaStatus();

      navigate(`/verifications/${verification.id}`, {
        state: {
          verification,
        },
      });
    } catch (error) {
      trackAnalysisFailed({
        sourcePage: location.pathname,
        language,
        errorType: categorizeAnalysisError(error),
      });
      if (error instanceof ApiRequestError && error.status === 429) {
        await refreshQuotaStatus();
        setSubmitError(error.message);
        setQuotaExceededRetryAfter(error.retryAfterSeconds);
        setQuotaExceededPlan(quotaStatus?.plan ?? (currentUser ? currentUser.plan : "ANONYMOUS"));
      } else {
        setSubmitError(
          error instanceof Error ? error.message : copy.analyzeForm.errors.verificationFailed,
        );
        setQuotaExceededRetryAfter(null);
        setQuotaExceededPlan(null);
      }
      onStateChange?.("error");
    } finally {
      setIsSubmitting(false);
      setIsQuotaRetrying(false);
    }
  }

  const formClassName = className ? `analysis-form ${className}` : "analysis-form";
  const messageClassName = errorClassName ?? "analysis-form__error";
  const resolvedButtonClassName = buttonClassName ?? "analysis-form__button";
  const quotaPlan = quotaStatus?.plan ?? quotaExceededPlan;
  const showQuotaPanel = submitError && quotaExceededRetryAfter !== null;
  const quotaResetCopy =
    quotaExceededRetryAfter && quotaExceededRetryAfter > 0
      ? copy.analyzeForm.quota.resetCountdown.replace(
          "{timeRemaining}",
          formatRetryAfter(quotaExceededRetryAfter, language),
        )
      : copy.analyzeForm.quota.resetAtMidnight;
  const quotaPanelCopy = resolveQuotaPanelCopy(copy, quotaPlan);
  const quotaIndicator = quotaStatus
    ? resolveQuotaIndicatorCopy(copy, quotaStatus, language)
    : null;

  return (
    <div className="analysis-form-shell">
      {quotaIndicator ? (
        <section className="analysis-form__quota-indicator" aria-live="polite">
          <div className="analysis-form__quota-indicator-copy">
            <p className="analysis-form__quota-indicator-title">{quotaIndicator.title}</p>
            <p className="analysis-form__quota-indicator-plan">{quotaIndicator.planLabel}</p>
            <p className="analysis-form__quota-indicator-meta">{quotaIndicator.resetCopy}</p>
          </div>
          {quotaIndicator.cta === "google" ? (
            <div className="analysis-form__quota-indicator-actions">
              <GoogleSignInButton className="analysis-form__quota-inline-signin" />
            </div>
          ) : quotaIndicator.ctaNote ? (
            <div className="analysis-form__quota-indicator-actions">
              <p className="analysis-form__quota-indicator-note">{quotaIndicator.ctaNote}</p>
            </div>
          ) : null}
        </section>
      ) : null}
      <form className={formClassName} onSubmit={(event) => void handleSubmit(event)}>
        <Input
          action={
            <button
              aria-label={copy.analyzeForm.pasteAriaLabel}
              className="analysis-form__paste"
              disabled={isSubmitting}
              onClick={() => void handlePaste()}
              title={copy.analyzeForm.pasteTitle}
              type="button"
            >
              <PasteIcon />
            </button>
          }
          autoComplete="off"
          className={inputClassName}
          hint={resolvedHint}
          inputMode="url"
          label={resolvedInputLabel}
          placeholder={resolvedPlaceholder}
          title={copy.analyzeForm.analyzeTitle}
          value={analysisTarget}
          onChange={(event) => {
            setAnalysisTarget(event.target.value);
            setInputType("manual");
          }}
        />
        <Button
          className={resolvedButtonClassName}
          disabled={isSubmitting}
          title={copy.analyzeForm.analyzeTitle}
          type="submit"
          variant="primary"
        >
          {isSubmitting ? resolvedSubmittingLabel : resolvedButtonLabel}
        </Button>
      </form>
      {showQuotaPanel ? (
        <section className="analysis-form__quota" aria-live="polite">
          <div className="analysis-form__quota-body">
            <p className="analysis-form__quota-eyebrow">{quotaPanelCopy.eyebrow}</p>
            <p className="analysis-form__quota-title">{quotaPanelCopy.title}</p>
            <p className="analysis-form__quota-copy">{quotaPanelCopy.description}</p>
            <p className="analysis-form__quota-meta">{quotaResetCopy}</p>
          </div>
          <div className="analysis-form__quota-actions">
            {quotaPlan === "ANONYMOUS" ? (
              <GoogleSignInButton
                className="analysis-form__quota-signin"
                variant="quota"
                busy={isQuotaRetrying}
                busyLabel={copy.analyzeForm.quota.retrying}
                onSuccess={async () => {
                  setIsQuotaRetrying(true);
                  await submitVerification(analysisTarget.trim(), inputType, {
                    preserveQuotaState: true,
                  });
                }}
              />
            ) : null}
            <p className="analysis-form__quota-note">
              {quotaPlan === "ANONYMOUS"
                ? isQuotaRetrying
                  ? copy.analyzeForm.quota.retrying
                  : copy.analyzeForm.quota.cta
                : quotaPanelCopy.note}
            </p>
          </div>
        </section>
      ) : submitError ? (
        <p className={messageClassName}>{submitError}</p>
      ) : null}
    </div>
  );
}

function resolveQuotaPanelCopy(
  copy: ReturnType<typeof useI18n>["copy"],
  quotaPlan: ApiQuotaStatus["plan"] | null,
) {
  if (quotaPlan === "FREE") {
    return {
      eyebrow: copy.analyzeForm.quota.freeEyebrow,
      title: copy.analyzeForm.quota.freeTitle,
      description: copy.analyzeForm.quota.freeDescription,
      note: copy.analyzeForm.quota.freeNote,
    };
  }

  if (quotaPlan === "PRO") {
    return {
      eyebrow: copy.analyzeForm.quota.proEyebrow,
      title: copy.analyzeForm.quota.proTitle,
      description: copy.analyzeForm.quota.proDescription,
      note: copy.analyzeForm.quota.proNote,
    };
  }

  return {
    eyebrow: copy.analyzeForm.quota.eyebrow,
    title: copy.analyzeForm.quota.title,
    description: copy.analyzeForm.quota.description,
    note: copy.analyzeForm.quota.cta,
  };
}

function resolveQuotaIndicatorCopy(
  copy: ReturnType<typeof useI18n>["copy"],
  quotaStatus: ApiQuotaStatus,
  language: "en" | "es",
) {
  const resetCopy = quotaStatus.blocked
    ? copy.analyzeForm.quotaIndicator.resetCountdown.replace(
        "{timeRemaining}",
        formatRetryAfter(quotaStatus.reset_in_seconds, language),
      )
    : copy.analyzeForm.quotaIndicator.resetAtMidnight;

  if (quotaStatus.plan === "ANONYMOUS") {
    return quotaStatus.blocked
      ? {
          title: copy.analyzeForm.quotaIndicator.anonymousBlockedTitle,
          planLabel: copy.analyzeForm.quotaIndicator.anonymousBlockedPlan,
          resetCopy,
          cta: "google" as const,
          ctaNote: null,
        }
      : {
          title: copy.analyzeForm.quotaIndicator.anonymousTitle.replace(
            "{remaining}",
            String(quotaStatus.remaining_today),
          ),
          planLabel: copy.analyzeForm.quotaIndicator.anonymousPlan,
          resetCopy,
          cta: null,
          ctaNote: copy.analyzeForm.quotaIndicator.anonymousNote,
        };
  }

  if (quotaStatus.plan === "PRO") {
    return quotaStatus.blocked
      ? {
          title: copy.analyzeForm.quotaIndicator.proBlockedTitle,
          planLabel: copy.analyzeForm.quotaIndicator.proPlan,
          resetCopy,
          cta: null,
          ctaNote: copy.analyzeForm.quotaIndicator.proBlockedNote,
        }
      : {
          title: copy.analyzeForm.quotaIndicator.proTitle.replace(
            "{remaining}",
            String(quotaStatus.remaining_today),
          ),
          planLabel: copy.analyzeForm.quotaIndicator.proPlan,
          resetCopy,
          cta: null,
          ctaNote: null,
        };
  }

  return quotaStatus.blocked
    ? {
        title: copy.analyzeForm.quotaIndicator.freeBlockedTitle,
        planLabel: copy.analyzeForm.quotaIndicator.freePlan,
        resetCopy,
        cta: null,
        ctaNote: copy.analyzeForm.quotaIndicator.freeBlockedNote,
      }
    : {
        title: copy.analyzeForm.quotaIndicator.freeTitle.replace(
          "{remaining}",
          String(quotaStatus.remaining_today),
        ),
        planLabel: copy.analyzeForm.quotaIndicator.freePlan,
        resetCopy,
        cta: null,
        ctaNote: null,
      };
}

function formatRetryAfter(seconds: number, language: "en" | "es"): string {
  if (seconds < 60) {
    return language === "es" ? "menos de 1 min" : "less than 1m";
  }

  const totalMinutes = Math.max(1, Math.ceil(seconds / 60));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (language === "es") {
    if (hours > 0 && minutes > 0) {
      return `${hours} h ${minutes} min`;
    }
    if (hours > 0) {
      return `${hours} h`;
    }
    return `${minutes} min`;
  }

  if (hours > 0 && minutes > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (hours > 0) {
    return `${hours}h`;
  }
  return `${minutes}m`;
}
