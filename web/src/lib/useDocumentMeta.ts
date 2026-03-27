import { useEffect } from "react";

import { useI18n } from "./i18n";

export function useDocumentMeta(title: string, description?: string) {
  const { copy } = useI18n();
  const resolvedDescription = description ?? copy.document.defaultDescription;

  useEffect(() => {
    const previousTitle = document.title;
    const descriptionTag = document.querySelector('meta[name="description"]');
    const previousDescription = descriptionTag?.getAttribute("content");

    document.title = `${title} | Verifiko`;

    if (descriptionTag) {
      descriptionTag.setAttribute("content", resolvedDescription);
    }

    return () => {
      document.title = previousTitle;

      if (descriptionTag && previousDescription) {
        descriptionTag.setAttribute("content", previousDescription);
      }
    };
  }, [resolvedDescription, title]);
}
