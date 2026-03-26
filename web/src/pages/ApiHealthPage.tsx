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
    "Status",
    "Confirm that Verifiko can reach its verification service.",
  );

  async function runHealthCheck() {
    setHealthState({ status: "loading" });

    try {
      const payload = await fetchApiHealth();
      setHealthState({ status: "ready", payload });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Status check failed.";
      setHealthState({ status: "error", message });
    }
  }

  useEffect(() => {
    void runHealthCheck();
  }, []);

  return (
    <PageShell>
      <SectionTitle
        eyebrow="Status"
        title="Service status"
        description="Confirm that Verifiko can reach its verification service."
      />

      <Card
        eyebrow="Service check"
        title="Verification service"
        description="Confirm that the verification service is reachable."
        action={
          <Button onClick={() => void runHealthCheck()} variant="secondary">
            Refresh
          </Button>
        }
      >
        <Input
          hint="Configured service endpoint."
          label="Service endpoint"
          readOnly
          value={getApiBaseUrl()}
        />

        {healthState.status === "loading" || healthState.status === "idle" ? (
          <p className="api-health__message">Checking service status…</p>
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
