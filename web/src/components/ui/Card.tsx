import type { HTMLAttributes, PropsWithChildren, ReactNode } from "react";

interface CardProps extends PropsWithChildren, HTMLAttributes<HTMLElement> {
  eyebrow?: string;
  title?: string;
  description?: string;
  action?: ReactNode;
  tone?: "default" | "warning" | "danger" | "success";
}

export function Card({
  eyebrow,
  title,
  description,
  action,
  tone = "default",
  children,
  className,
  ...props
}: CardProps) {
  const cardClassName = className ? `card card--${tone} ${className}` : `card card--${tone}`;

  return (
    <section className={cardClassName} {...props}>
      {(eyebrow ?? title ?? description ?? action) && (
        <header className="card__header">
          <div>
            {eyebrow ? <p className="card__eyebrow">{eyebrow}</p> : null}
            {title ? <h3 className="card__title">{title}</h3> : null}
            {description ? <p className="card__description">{description}</p> : null}
          </div>
          {action ? <div className="card__action">{action}</div> : null}
        </header>
      )}
      {children}
    </section>
  );
}
