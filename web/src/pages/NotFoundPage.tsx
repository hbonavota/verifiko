import { Button } from "../components/ui/Button";
import { SectionTitle } from "../components/ui/SectionTitle";
import { useI18n } from "../lib/i18n";
import { useDocumentMeta, useNoIndex } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";

export function NotFoundPage() {
  const { copy } = useI18n();

  useDocumentMeta(copy.notFound.metaTitle, copy.notFound.metaDescription);
  useNoIndex();

  return (
    <PageShell>
      <SectionTitle
        eyebrow={copy.notFound.eyebrow}
        title={copy.notFound.title}
        description={copy.notFound.description}
      />
      <Button to="/" variant="secondary">
        {copy.notFound.returnHome}
      </Button>
    </PageShell>
  );
}
