import { useEffect, useState } from "react";

import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { SectionTitle } from "../components/ui/SectionTitle";
import { fetchApiHealth, getApiBaseUrl } from "../lib/api";
import { useI18n } from "../lib/i18n";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";
import type { HealthCheckResult } from "../types/verification";

type HealthState =
  | { status: "idle" | "loading" }
  | { status: "ready"; payload: HealthCheckResult }
  | { status: "error"; message: string };

export function ApiHealthPage() {
  const { copy, language, locale } = useI18n();
  const [healthState, setHealthState] = useState<HealthState>({ status: "idle" });

  useDocumentMeta(
    copy.health.metaTitle,
    copy.health.metaDescription,
  );

  async function runHealthCheck() {
    setHealthState({ status: "loading" });

    try {
      const payload = await fetchApiHealth(language);
      setHealthState({ status: "ready", payload });
    } catch (error) {
      const message = error instanceof Error ? error.message : copy.health.statusCheckFailed;
      setHealthState({ status: "error", message });
    }
  }

  useEffect(() => {
    void runHealthCheck();
  }, [language]);

  return (
    <PageShell>
      <SectionTitle
        eyebrow={copy.health.eyebrow}
        title={copy.health.title}
        description={copy.health.description}
      />

      <Card
        eyebrow={copy.health.serviceCheck}
        title={copy.health.verificationService}
        description={copy.health.verificationServiceDescription}
        action={
          <Button onClick={() => void runHealthCheck()} variant="secondary">
            {copy.common.refresh}
          </Button>
        }
      >
        <Input
          hint={copy.health.configuredServiceEndpoint}
          label={copy.common.serviceEndpoint}
          readOnly
          value={getApiBaseUrl(language)}
        />

        {healthState.status === "loading" || healthState.status === "idle" ? (
          <p className="api-health__message">{copy.health.checking}</p>
        ) : null}

        {healthState.status === "ready" ? (
          <div className="api-health__result">
            <Badge label={healthState.payload.status.toUpperCase()} tone="success" />
            <p className="api-health__message">{healthState.payload.detail}</p>
            <p className="api-health__timestamp">
              {copy.common.lastChecked} {new Date(healthState.payload.checkedAt).toLocaleString(locale)}
            </p>
          </div>
        ) : null}

        {healthState.status === "error" ? (
          <div className="api-health__result">
            <Badge label={copy.health.error.toUpperCase()} tone="danger" />
            <p className="api-health__message">{healthState.message}</p>
          </div>
        ) : null}
      </Card>
    </PageShell>
  );
}
