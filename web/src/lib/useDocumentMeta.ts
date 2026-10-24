import { useEffect } from "react";

import { useI18n } from "./i18n";

// Unknown routes are served by the SPA rewrite with a 200 (soft 404). Pages that
// render a "not found" state call this so crawlers do not index those URLs.
export function useNoIndex() {
  useEffect(() => {
    const robotsTag = document.createElement("meta");
    robotsTag.name = "robots";
    robotsTag.content = "noindex";
    document.head.appendChild(robotsTag);

    return () => {
      robotsTag.remove();
    };
  }, []);
}

export function useDocumentMeta(title: string, description?: string) {
  const { copy, language } = useI18n();
  const resolvedDescription = description ?? copy.document.defaultDescription;

  useEffect(() => {
    const previousTitle = document.title;
    const previousLang = document.documentElement.lang;
    const descriptionTag = document.querySelector('meta[name="description"]');
    const previousDescription = descriptionTag?.getAttribute("content");
    const canonicalTag = document.querySelector('link[rel="canonical"]');
    const previousCanonical = canonicalTag?.getAttribute("href");
    const canonicalHref = `${window.location.origin}${window.location.pathname}`;

    // Titles that already carry the brand (e.g. the landing's, which mirrors the
    // static <title> in index.html) are used as-is instead of getting a suffix.
    document.title = title.includes("Verifiko") ? title : `${title} | Verifiko`;
    document.documentElement.lang = language;

    if (descriptionTag) {
      descriptionTag.setAttribute("content", resolvedDescription);
    }

    if (canonicalTag) {
      canonicalTag.setAttribute("href", canonicalHref);
    } else {
      const newCanonicalTag = document.createElement("link");
      newCanonicalTag.rel = "canonical";
      newCanonicalTag.href = canonicalHref;
      document.head.appendChild(newCanonicalTag);
    }

    return () => {
      document.title = previousTitle;
      document.documentElement.lang = previousLang;

      if (descriptionTag && previousDescription) {
        descriptionTag.setAttribute("content", previousDescription);
      }

      const currentCanonicalTag = document.querySelector('link[rel="canonical"]');
      if (!currentCanonicalTag) {
        return;
      }

      if (previousCanonical) {
        currentCanonicalTag.setAttribute("href", previousCanonical);
      } else {
        currentCanonicalTag.remove();
      }
    };
  }, [language, resolvedDescription, title]);
}
