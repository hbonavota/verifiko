import { useEffect } from "react";

import { useI18n } from "./i18n";

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

    document.title = `${title} | Verifiko`;
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
