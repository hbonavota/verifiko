import type { PropsWithChildren } from "react";

export function PageShell({ children }: PropsWithChildren) {
  return <div className="page-shell">{children}</div>;
}
