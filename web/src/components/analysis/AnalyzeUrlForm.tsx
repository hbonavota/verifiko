import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { createVerification } from "../../lib/api";
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
  buttonLabel = "Verify this link",
  buttonClassName,
  className,
  errorClassName,
  hint = "Paste a link to verify its safety.",
  inputClassName,
  inputLabel = "Link",
  onStateChange,
  placeholder = "Paste a link to verify its safety",
  submittingLabel = "Verifying...",
}: AnalyzeUrlFormProps) {
  const navigate = useNavigate();
  const [analysisTarget, setAnalysisTarget] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handlePaste() {
    if (!navigator.clipboard?.readText) {
      setSubmitError("Clipboard access is not available in this browser.");
      return;
    }

    try {
      const clipboardValue = (await navigator.clipboard.readText()).trim();
      if (!clipboardValue) {
        setSubmitError("Clipboard does not contain a link to verify.");
        return;
      }

      setAnalysisTarget(clipboardValue);
      setSubmitError(null);
      onStateChange?.("idle");
    } catch {
      setSubmitError("Clipboard access was blocked.");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedTarget = analysisTarget.trim();
    if (!trimmedTarget) {
      setSubmitError("Enter a URL to verify.");
      onStateChange?.("error");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    onStateChange?.("submitting");

    try {
      const verification = await createVerification({ url: trimmedTarget });
      navigate(`/verifications/${verification.id}`);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Verification failed.");
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
              aria-label="Paste a link from the clipboard"
              className="analysis-form__paste"
              disabled={isSubmitting}
              onClick={() => void handlePaste()}
              title="Paste a link from the clipboard"
              type="button"
            >
              <PasteIcon />
            </button>
          }
          autoComplete="off"
          className={inputClassName}
          hint={hint}
          inputMode="url"
          label={inputLabel}
          placeholder={placeholder}
          title="Analyze this link for potential security risks"
          value={analysisTarget}
          onChange={(event) => setAnalysisTarget(event.target.value)}
        />
        <Button
          className={resolvedButtonClassName}
          disabled={isSubmitting}
          title="Analyze this link for potential security risks"
          type="submit"
          variant="primary"
        >
          {isSubmitting ? submittingLabel : buttonLabel}
        </Button>
      </form>
      {submitError ? <p className={messageClassName}>{submitError}</p> : null}
    </div>
  );
}
