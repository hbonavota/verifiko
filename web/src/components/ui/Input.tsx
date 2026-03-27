import type { InputHTMLAttributes, ReactNode } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  action?: ReactNode;
}

export function Input({ action, hint, id, label, ...props }: InputProps) {
  const resolvedId = id ?? `input-${label.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <label className="field" htmlFor={resolvedId}>
      <span className="field__label">{label}</span>
      <span className={action ? "field__control field__control--has-action" : "field__control"}>
        <input className="field__input" id={resolvedId} {...props} />
        {action ? <span className="field__action">{action}</span> : null}
      </span>
      {hint ? <span className="field__hint">{hint}</span> : null}
    </label>
  );
}
