import type { ButtonHTMLAttributes, PropsWithChildren, ReactNode } from "react";
import { Link } from "react-router-dom";

type ButtonVariant = "primary" | "secondary" | "ghost";

interface SharedButtonProps extends PropsWithChildren {
  variant?: ButtonVariant;
  className?: string;
  leadingIcon?: ReactNode;
  title?: string;
}

interface ButtonAsButtonProps extends SharedButtonProps {
  to?: undefined;
  href?: undefined;
  type?: ButtonHTMLAttributes<HTMLButtonElement>["type"];
  onClick?: ButtonHTMLAttributes<HTMLButtonElement>["onClick"];
  disabled?: ButtonHTMLAttributes<HTMLButtonElement>["disabled"];
}

interface ButtonAsLinkProps extends SharedButtonProps {
  to: string;
  href?: undefined;
}

interface ButtonAsAnchorProps extends SharedButtonProps {
  href: string;
  to?: undefined;
}

type ButtonProps = ButtonAsButtonProps | ButtonAsLinkProps | ButtonAsAnchorProps;

function classNames(variant: ButtonVariant, className?: string): string {
  const baseClassName = `button button--${variant}`;
  return className ? `${baseClassName} ${className}` : baseClassName;
}

function ButtonContent({ leadingIcon, children }: SharedButtonProps) {
  return (
    <>
      {leadingIcon ? <span className="button__icon">{leadingIcon}</span> : null}
      <span>{children}</span>
    </>
  );
}

export function Button(props: ButtonProps) {
  const variant = props.variant ?? "primary";
  const buttonClassName = classNames(variant, props.className);

  if ("to" in props && props.to) {
    return (
      <Link className={buttonClassName} title={props.title} to={props.to}>
        <ButtonContent leadingIcon={props.leadingIcon}>{props.children}</ButtonContent>
      </Link>
    );
  }

  if ("href" in props && props.href) {
    return (
      <a className={buttonClassName} href={props.href} title={props.title}>
        <ButtonContent leadingIcon={props.leadingIcon}>{props.children}</ButtonContent>
      </a>
    );
  }

  const buttonProps = props as ButtonAsButtonProps;

  return (
    <button
      className={buttonClassName}
      disabled={buttonProps.disabled}
      onClick={buttonProps.onClick}
      title={buttonProps.title}
      type={buttonProps.type ?? "button"}
    >
      <ButtonContent leadingIcon={buttonProps.leadingIcon}>{buttonProps.children}</ButtonContent>
    </button>
  );
}
