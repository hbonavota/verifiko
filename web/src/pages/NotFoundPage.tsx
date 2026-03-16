import { Button } from "../components/ui/Button";
import { SectionTitle } from "../components/ui/SectionTitle";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";

export function NotFoundPage() {
  useDocumentMeta(
    "Not Found",
    "The requested Verifiko route could not be found in the current demo workspace.",
  );

  return (
    <PageShell>
      <SectionTitle
        eyebrow="Route Not Found"
        title="The requested route is not available."
        description="Return to the product overview or continue into the verification workspace from the dashboard."
      />
      <Button to="/" variant="secondary">
        Return to home
      </Button>
    </PageShell>
  );
}
