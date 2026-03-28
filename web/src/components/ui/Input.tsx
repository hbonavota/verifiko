import type { InputHTMLAttributes, ReactNode } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  action?: ReactNode;
}

export function Input({ action, hint, id, label, ...props }: InputProps) {
  const resolvedId = id ?? `input-${label.toLowerCase().replace(/\s+/g, "-")}`;
  const inputClassName = props.className ? `field__input ${props.className}` : "field__input";

  return (
    <label className="field" htmlFor={resolvedId}>
      <span className="field__label">{label}</span>
      <span className={action ? "field__control field__control--has-action" : "field__control"}>
        <input {...props} className={inputClassName} id={resolvedId} />
        {action ? <span className="field__action">{action}</span> : null}
      </span>
      {hint ? <span className="field__hint">{hint}</span> : null}
    </label>
  );
}
