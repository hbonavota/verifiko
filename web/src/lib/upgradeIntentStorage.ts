import { useEffect, useState } from "react";

export type UpgradeIntentSource = "topbar" | "quota_indicator" | "quota_blocked" | "pro_panel";

interface StoredUpgradeIntent {
  source: UpgradeIntentSource;
  submittedAt: string;
}

const STORAGE_KEY = "verifiko-upgrade-intent-v1";
const STORAGE_EVENT = "verifiko-upgrade-intent-changed";

function isUpgradeIntentSource(value: unknown): value is UpgradeIntentSource {
  return (
    value === "topbar" ||
    value === "quota_indicator" ||
    value === "quota_blocked" ||
    value === "pro_panel"
  );
}

export function readStoredUpgradeIntent(): StoredUpgradeIntent | null {
  if (typeof window === "undefined") {
    return null;
  }

  const rawValue = window.localStorage.getItem(STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsedValue = JSON.parse(rawValue) as Partial<StoredUpgradeIntent>;
    if (
      !parsedValue ||
      !isUpgradeIntentSource(parsedValue.source) ||
      typeof parsedValue.submittedAt !== "string"
    ) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }

    return {
      source: parsedValue.source,
      submittedAt: parsedValue.submittedAt,
    };
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function persistUpgradeIntent(source: UpgradeIntentSource): StoredUpgradeIntent {
  const record = {
    source,
    submittedAt: new Date().toISOString(),
  } satisfies StoredUpgradeIntent;

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
  window.dispatchEvent(new Event(STORAGE_EVENT));

  return record;
}

export function useUpgradeIntent() {
  const [upgradeIntent, setUpgradeIntent] = useState<StoredUpgradeIntent | null>(() =>
    readStoredUpgradeIntent(),
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const syncFromStorage = () => {
      setUpgradeIntent(readStoredUpgradeIntent());
    };

    window.addEventListener(STORAGE_EVENT, syncFromStorage);
    window.addEventListener("storage", syncFromStorage);

    return () => {
      window.removeEventListener(STORAGE_EVENT, syncFromStorage);
      window.removeEventListener("storage", syncFromStorage);
    };
  }, []);

  return {
    upgradeIntent,
    hasSubmittedUpgradeIntent: upgradeIntent !== null,
    saveUpgradeIntent: persistUpgradeIntent,
  };
}
