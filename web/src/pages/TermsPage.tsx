import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { useI18n } from "../lib/i18n";
import { VERIFIKO_CONTACT_EMAIL, VERIFIKO_CONTACT_MAILTO } from "../lib/site";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";

export function TermsPage() {
  const { copy } = useI18n();

  useDocumentMeta(
    copy.termsPage.metaTitle,
    copy.termsPage.metaDescription,
  );

  return (
    <PageShell>
      <SectionTitle
        eyebrow={copy.termsPage.eyebrow}
        title={copy.termsPage.title}
        description={copy.termsPage.description}
      />

      <div className="public-page__stack">
        <Card className="public-page__card" title={copy.termsPage.serviceTitle}>
          <ul className="public-page__list">
            {copy.termsPage.serviceItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>

        <Card className="public-page__card" title={copy.termsPage.judgmentTitle}>
          <ul className="public-page__list">
            {copy.termsPage.judgmentItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>

        <Card className="public-page__card" title={copy.termsPage.useTitle}>
          <ul className="public-page__list">
            {copy.termsPage.useItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>

        <Card className="public-page__card" title={copy.termsPage.availabilityTitle}>
          <ul className="public-page__list">
            {copy.termsPage.availabilityItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>

        <Card className="public-page__card" title={copy.termsPage.contactTitle}>
          <div className="public-page__prose">
            <p className="public-page__copy">
              {copy.termsPage.contactCopy.replace("{email}", VERIFIKO_CONTACT_EMAIL)}
            </p>
            <a className="public-page__link" href={VERIFIKO_CONTACT_MAILTO}>
              {VERIFIKO_CONTACT_EMAIL}
            </a>
          </div>
        </Card>
      </div>
    </PageShell>
  );
}
