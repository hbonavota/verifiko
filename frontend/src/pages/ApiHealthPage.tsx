import { useEffect, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { SectionTitle } from "../components/ui/SectionTitle";
import { fetchApiHealth, getApiBaseUrl } from "../lib/api";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import type { HealthCheckResult } from "../types/verification";

type HealthState =
  | { status: "idle" | "loading" }
  | { status: "ready"; payload: HealthCheckResult }
  | { status: "error"; message: string };

export function ApiHealthPage() {
  const [healthState, setHealthState] = useState<HealthState>({ status: "idle" });

  useDocumentMeta(
    "API Health",
    "Backend connectivity check for the current Verifiko API surface, including live status and configured base URL.",
  );

  async function runHealthCheck() {
    setHealthState({ status: "loading" });

    try {
      const payload = await fetchApiHealth();
      setHealthState({ status: "ready", payload });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Health probe failed.";
      setHealthState({ status: "error", message });
    }
  }

  useEffect(() => {
    void runHealthCheck();
  }, []);

  return (
    <PageShell>
      <SectionTitle
        eyebrow="Backend Connectivity"
        title="Backend health and local integration status"
        description="Direct health probe for the current API surface, kept intentionally focused so connectivity can be validated without expanding frontend scope."
      />

      <Card
        eyebrow="Health check"
        title="API status"
        description="Direct probe of the backend health route to confirm local integration readiness."
        action={
          <Button onClick={() => void runHealthCheck()} variant="secondary">
            Refresh
          </Button>
        }
      >
        <Input
          hint="Configured from VITE_API_BASE_URL."
          label="Backend base URL"
          readOnly
          value={getApiBaseUrl()}
        />

        {healthState.status === "loading" || healthState.status === "idle" ? (
          <p className="api-health__message">Checking backend health endpoint…</p>
        ) : null}

        {healthState.status === "ready" ? (
          <div className="api-health__result">
            <Badge label={healthState.payload.status.toUpperCase()} tone="success" />
            <p className="api-health__message">{healthState.payload.detail}</p>
            <p className="api-health__timestamp">
              Last checked {new Date(healthState.payload.checkedAt).toLocaleString()}
            </p>
          </div>
        ) : null}

        {healthState.status === "error" ? (
          <div className="api-health__result">
            <Badge label="ERROR" tone="danger" />
            <p className="api-health__message">{healthState.message}</p>
          </div>
        ) : null}
      </Card>
    </PageShell>
  );
}
