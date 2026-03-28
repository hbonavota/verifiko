import type { PropsWithChildren } from "react";

import { SiteFooter } from "./SiteFooter";

interface ContentShellProps extends PropsWithChildren {
  onOpenCookiePreferences?: () => void;
}

export function ContentShell({ children, onOpenCookiePreferences }: ContentShellProps) {
  return (
    <main className="content-shell">
      <div className="content-shell__body">{children}</div>
      <SiteFooter onOpenCookiePreferences={onOpenCookiePreferences} />
    </main>
  );
}
