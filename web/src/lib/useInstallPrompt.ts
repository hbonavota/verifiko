import { useCallback, useEffect, useRef, useState } from "react";

// Chromium's install event (not in the DOM typings).
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

export type InstallMode = "hidden" | "native" | "ios";

function isStandalone(): boolean {
  const iosStandalone = (navigator as Navigator & { standalone?: boolean }).standalone === true;
  return iosStandalone || window.matchMedia?.("(display-mode: standalone)").matches === true;
}

function isIos(): boolean {
  const ua = navigator.userAgent;
  // iPadOS reports itself as a Mac; touch support tells them apart.
  return /iphone|ipad|ipod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

/**
 * Whether (and how) the app can be installed from this browser.
 *
 * Always "hidden" on the first render, on the server and the client alike, so the
 * prerendered landing hydrates without a mismatch; the real mode is decided in an
 * effect. "native" needs the PWA service worker (VITE_PWA_ENABLED): without it the
 * browser never fires beforeinstallprompt and the button simply stays hidden.
 */
export function useInstallPrompt(): { mode: InstallMode; promptInstall: () => Promise<void> } {
  const [mode, setMode] = useState<InstallMode>("hidden");
  const deferredPromptRef = useRef<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    if (isStandalone()) {
      return;
    }
    if (isIos()) {
      setMode("ios");
      return;
    }

    function handleBeforeInstallPrompt(event: Event) {
      event.preventDefault();
      deferredPromptRef.current = event as BeforeInstallPromptEvent;
      setMode("native");
    }

    function handleAppInstalled() {
      deferredPromptRef.current = null;
      setMode("hidden");
    }

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleAppInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, []);

  const promptInstall = useCallback(async () => {
    const deferredPrompt = deferredPromptRef.current;
    if (!deferredPrompt) {
      return;
    }
    // The event can be used only once.
    deferredPromptRef.current = null;
    setMode("hidden");
    await deferredPrompt.prompt();
    await deferredPrompt.userChoice;
  }, []);

  return { mode, promptInstall };
}
