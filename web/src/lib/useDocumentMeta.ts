import { useEffect } from "react";

const DEFAULT_DESCRIPTION =
  "Verifiko verifies links with clear risk scoring and evidence-led results.";

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
