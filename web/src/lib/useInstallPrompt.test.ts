import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useInstallPrompt, type InstallMode } from "./useInstallPrompt";

const IPHONE_UA =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";

// jsdom has no matchMedia; the hook treats a missing one as "not standalone".
function mockDisplayModeStandalone(matches: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: vi.fn((query: string) => ({
      matches: matches && query === "(display-mode: standalone)",
      media: query,
    })),
  });
}

function installPromptEvent() {
  return Object.assign(new Event("beforeinstallprompt", { cancelable: true }), {
    prompt: vi.fn().mockResolvedValue(undefined),
    userChoice: Promise.resolve({ outcome: "accepted", platform: "web" }),
  });
}

// Records the mode of every render, so the pre-effect first render is observable.
function renderInstallPrompt() {
  const modes: InstallMode[] = [];
  const view = renderHook(() => {
    const result = useInstallPrompt();
    modes.push(result.mode);
    return result;
  });
  return { ...view, modes };
}

afterEach(() => {
  vi.restoreAllMocks();
  Reflect.deleteProperty(window, "matchMedia");
  Reflect.deleteProperty(navigator, "standalone");
});

describe("useInstallPrompt", () => {
  it("renders 'hidden' first, even on iOS, so the prerendered landing hydrates cleanly", () => {
    vi.spyOn(navigator, "userAgent", "get").mockReturnValue(IPHONE_UA);

    const { result, modes } = renderInstallPrompt();

    expect(modes[0]).toBe("hidden");
    expect(result.current.mode).toBe("ios");
  });

  it("stays 'hidden' when already installed (display-mode: standalone)", () => {
    mockDisplayModeStandalone(true);
    const { result } = renderInstallPrompt();

    act(() => {
      window.dispatchEvent(installPromptEvent());
    });

    expect(result.current.mode).toBe("hidden");
  });

  it("stays 'hidden' when launched from the iOS home screen (navigator.standalone)", () => {
    vi.spyOn(navigator, "userAgent", "get").mockReturnValue(IPHONE_UA);
    Object.defineProperty(navigator, "standalone", { configurable: true, value: true });

    const { result } = renderInstallPrompt();

    expect(result.current.mode).toBe("hidden");
  });

  it("switches to 'native' on beforeinstallprompt and back to 'hidden' on appinstalled", () => {
    const { result } = renderInstallPrompt();
    expect(result.current.mode).toBe("hidden");

    const event = installPromptEvent();
    act(() => {
      window.dispatchEvent(event);
    });
    expect(result.current.mode).toBe("native");
    // The browser's own mini-infobar is suppressed in favour of our button.
    expect(event.defaultPrevented).toBe(true);

    act(() => {
      window.dispatchEvent(new Event("appinstalled"));
    });
    expect(result.current.mode).toBe("hidden");
  });

  it("promptInstall shows the deferred prompt once and hides the button", async () => {
    const { result } = renderInstallPrompt();
    const event = installPromptEvent();
    act(() => {
      window.dispatchEvent(event);
    });

    await act(() => result.current.promptInstall());
    await act(() => result.current.promptInstall());

    expect(event.prompt).toHaveBeenCalledTimes(1);
    expect(result.current.mode).toBe("hidden");
  });
});
