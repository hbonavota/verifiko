import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { createVerification } from "../../lib/api";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";

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
  buttonLabel = "Analyze",
  buttonClassName,
  className,
  errorClassName,
  hint = "URL or hostname.",
  inputClassName,
  inputLabel = "URL",
  onStateChange,
  placeholder = "https://example.com/login",
  submittingLabel = "Scanning...",
}: AnalyzeUrlFormProps) {
  const navigate = useNavigate();
  const [analysisTarget, setAnalysisTarget] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedTarget = analysisTarget.trim();
    if (!trimmedTarget) {
      setSubmitError("Enter a URL to analyze.");
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
      setSubmitError(error instanceof Error ? error.message : "Verification request failed.");
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
          autoComplete="off"
          className={inputClassName}
          hint={hint}
          inputMode="url"
          label={inputLabel}
          placeholder={placeholder}
          value={analysisTarget}
          onChange={(event) => setAnalysisTarget(event.target.value)}
        />
        <Button className={resolvedButtonClassName} disabled={isSubmitting} type="submit" variant="primary">
          {isSubmitting ? submittingLabel : buttonLabel}
        </Button>
      </form>
      {submitError ? <p className={messageClassName}>{submitError}</p> : null}
    </div>
  );
}
