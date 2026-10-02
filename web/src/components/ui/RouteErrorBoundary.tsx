import { Component, type ReactNode } from "react";

import { useI18n } from "../../lib/i18n";
import { Button } from "./Button";

interface RouteErrorBoundaryProps {
  children: ReactNode;
}

interface RouteErrorBoundaryState {
  hasError: boolean;
}

// A render error in a routed page would otherwise leave the user on a blank
// screen. The most common cause is a stale lazy chunk after a new deploy (the
// hashed file 404s); `lazyWithReload` auto-reloads once, and this boundary is the
// safety net for when that reload didn't resolve it or any other render error is
// thrown. It shows a recovery screen with a full-reload action (which fetches the
// fresh index.html and chunks) instead of nothing.
export class RouteErrorBoundary extends Component<
  RouteErrorBoundaryProps,
  RouteErrorBoundaryState
> {
  state: RouteErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): RouteErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown): void {
    console.error("[RouteErrorBoundary] Unhandled render error:", error);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return <RouteErrorFallback />;
    }
    return this.props.children;
  }
}

function RouteErrorFallback() {
  const { copy } = useI18n();
  return (
    <div className="route-error" role="alert">
      <div className="route-error__panel">
        <p className="route-error__title">{copy.errorBoundary.title}</p>
        <p className="route-error__description">{copy.errorBoundary.description}</p>
        <div className="route-error__actions">
          <Button variant="primary" onClick={() => window.location.reload()}>
            {copy.errorBoundary.reload}
          </Button>
          <Button variant="secondary" href="/app">
            {copy.errorBoundary.home}
          </Button>
        </div>
      </div>
    </div>
  );
}
