import type { PropsWithChildren } from "react";

import { SiteFooter } from "./SiteFooter";

export function ContentShell({ children }: PropsWithChildren) {
  return (
    <main className="content-shell">
      <div className="content-shell__body">{children}</div>
      <SiteFooter />
    </main>
  );
}
