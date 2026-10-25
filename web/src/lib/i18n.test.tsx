import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { I18nProvider, getStoredLanguage, useI18n, type Language } from "./i18n";

const STORAGE_KEY = "verifiko-language";

function renderI18n({ deferStoredLanguage = false } = {}) {
  const languages: Language[] = [];
  const view = renderHook(
    () => {
      const value = useI18n();
      languages.push(value.language);
      return value;
    },
    {
      wrapper: ({ children }: { children: ReactNode }) => (
        <I18nProvider deferStoredLanguage={deferStoredLanguage}>{children}</I18nProvider>
      ),
    },
  );
  return { ...view, languages };
}

// Every leaf path of a nested copy object, e.g. "notFound.returnHome".
function keyPaths(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return [prefix];
  }
  return Object.entries(value).flatMap(([key, child]) =>
    keyPaths(child, prefix ? `${prefix}.${key}` : key),
  );
}

afterEach(() => {
  window.localStorage.clear();
  document.documentElement.lang = "";
});

describe("getStoredLanguage", () => {
  it("returns the stored language and falls back to English for missing or unknown values", () => {
    expect(getStoredLanguage()).toBe("en");

    window.localStorage.setItem(STORAGE_KEY, "es");
    expect(getStoredLanguage()).toBe("es");

    window.localStorage.setItem(STORAGE_KEY, "fr");
    expect(getStoredLanguage()).toBe("en");
  });
});

describe("I18nProvider", () => {
  it("switches copy and locale, and persists the choice to storage and <html lang>", () => {
    const { result } = renderI18n();
    expect(result.current.copy.notFound.returnHome).toBe("Return to home");

    act(() => {
      result.current.setLanguage("es");
    });

    expect(result.current.copy.notFound.returnHome).toBe("Volver al inicio");
    expect(result.current.locale).toBe("es-ES");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("es");
    expect(document.documentElement.lang).toBe("es");
  });

  it("with deferStoredLanguage, renders English first and applies the stored language after", () => {
    window.localStorage.setItem(STORAGE_KEY, "es");

    const { result, languages } = renderI18n({ deferStoredLanguage: true });

    expect(languages[0]).toBe("en");
    expect(result.current.language).toBe("es");
    // The English placeholder never overwrote the saved choice.
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("es");
  });

  it("has the same copy keys in English and Spanish", () => {
    const { result } = renderI18n();
    const englishKeys = keyPaths(result.current.copy);

    act(() => {
      result.current.setLanguage("es");
    });

    expect(keyPaths(result.current.copy)).toEqual(englishKeys);
  });
});
