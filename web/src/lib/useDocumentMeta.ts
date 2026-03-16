import { useEffect } from "react";

const DEFAULT_DESCRIPTION =
  "Verifiko is an explainable verification workspace for evidence-driven risk assessment.";

export function useDocumentMeta(title: string, description = DEFAULT_DESCRIPTION) {
  useEffect(() => {
    const previousTitle = document.title;
    const descriptionTag = document.querySelector('meta[name="description"]');
    const previousDescription = descriptionTag?.getAttribute("content");

    document.title = `${title} | Verifiko`;

    if (descriptionTag) {
      descriptionTag.setAttribute("content", description);
    }

    return () => {
      document.title = previousTitle;

      if (descriptionTag && previousDescription) {
        descriptionTag.setAttribute("content", previousDescription);
      }
    };
  }, [description, title]);
}
