import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function Input({ hint, id, label, ...props }: InputProps) {
  const resolvedId = id ?? `input-${label.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <label className="field" htmlFor={resolvedId}>
      <span className="field__label">{label}</span>
      <input className="field__input" id={resolvedId} {...props} />
      {hint ? <span className="field__hint">{hint}</span> : null}
    </label>
  );
}
