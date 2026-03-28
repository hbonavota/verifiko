import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { createVerification } from "../../lib/api";
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
  const location = useLocation();
  const navigate = useNavigate();
  const [analysisTarget, setAnalysisTarget] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [inputType, setInputType] = useState<"manual" | "paste">("manual");

  const resolvedButtonLabel = buttonLabel ?? copy.analyzeForm.buttonLabel;
  const resolvedHint = hint ?? copy.analyzeForm.hint;
  const resolvedInputLabel = inputLabel ?? copy.analyzeForm.inputLabel;
  const resolvedPlaceholder = placeholder ?? copy.analyzeForm.placeholder;
  const resolvedSubmittingLabel = submittingLabel ?? copy.analyzeForm.submittingLabel;

  async function handlePaste() {
    if (!navigator.clipboard?.readText) {
      setSubmitError(copy.analyzeForm.errors.clipboardUnavailable);
      return;
    }

    try {
      const clipboardValue = (await navigator.clipboard.readText()).trim();
      if (!clipboardValue) {
        setSubmitError(copy.analyzeForm.errors.clipboardEmpty);
        return;
      }

      setAnalysisTarget(clipboardValue);
      setInputType("paste");
      setSubmitError(null);
      onStateChange?.("idle");
    } catch {
      setSubmitError(copy.analyzeForm.errors.clipboardBlocked);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedTarget = analysisTarget.trim();
    if (!trimmedTarget) {
      setSubmitError(copy.analyzeForm.errors.enterUrl);
      onStateChange?.("error");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    onStateChange?.("submitting");
    trackAnalysisStarted({
      sourcePage: location.pathname,
      language,
      inputType,
      hasProtocol: /^https?:\/\//i.test(trimmedTarget),
    });

    try {
      const verification = await createVerification({ url: trimmedTarget });
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

      navigate(`/verifications/${verification.id}`);
    } catch (error) {
      trackAnalysisFailed({
        sourcePage: location.pathname,
        language,
        errorType: categorizeAnalysisError(error),
      });
      setSubmitError(error instanceof Error ? error.message : copy.analyzeForm.errors.verificationFailed);
      onStateChange?.("error");
    } finally {
      setIsSubmitting(false);
    }
  }

  const formClassName = className ? `analysis-form ${className}` : "analysis-form";
  const messageClassName = errorClassName ?? "analysis-form__error";
  const resolvedButtonClassName = buttonClassName ?? "analysis-form__button";

  return (
    <div className="analysis-form-shell">
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
      {submitError ? <p className={messageClassName}>{submitError}</p> : null}
    </div>
  );
}
