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
    "Check whether the Verifiko application can reach its analysis API.",
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
        eyebrow="Connection"
        title="API connection status"
        description="A simple check to confirm that Verifiko can reach its analysis service."
      />

      <Card
        eyebrow="Health check"
        title="API status"
        description="Check whether the analysis service is reachable."
        action={
          <Button onClick={() => void runHealthCheck()} variant="secondary">
            Refresh
          </Button>
        }
      >
        <Input
          hint="Configured for this application."
          label="Service URL"
          readOnly
          value={getApiBaseUrl()}
        />

        {healthState.status === "loading" || healthState.status === "idle" ? (
          <p className="api-health__message">Checking service connection…</p>
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
