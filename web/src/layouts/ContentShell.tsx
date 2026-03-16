import type { PropsWithChildren } from "react";

export function ContentShell({ children }: PropsWithChildren) {
  return <main className="content-shell">{children}</main>;
}
