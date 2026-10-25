import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { useI18n } from "../lib/i18n";
import { VERIFIKO_CONTACT_EMAIL, VERIFIKO_CONTACT_MAILTO } from "../lib/site";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";

export function ContactPage() {
  const { copy } = useI18n();

  useDocumentMeta(copy.contactPage.metaTitle, copy.contactPage.metaDescription);

  return (
    <PageShell>
      <SectionTitle
        eyebrow={copy.contactPage.eyebrow}
        title={copy.contactPage.title}
        description={copy.contactPage.description}
      />

      <div className="public-page__stack">
        <Card className="public-page__card" title={copy.contactPage.aboutTitle}>
          <div className="public-page__prose">
            {copy.contactPage.aboutCopy.map((paragraph) => (
              <p key={paragraph} className="public-page__copy">
                {paragraph}
              </p>
            ))}
          </div>
        </Card>

        <Card className="public-page__card" title={copy.contactPage.emailTitle}>
          <div className="public-page__prose">
            <p className="public-page__contact-label">{copy.contactPage.emailLabel}</p>
            <a className="public-page__link" href={VERIFIKO_CONTACT_MAILTO}>
              {VERIFIKO_CONTACT_EMAIL}
            </a>
            <p className="public-page__copy">{copy.contactPage.emailCopy}</p>
            <p className="public-page__meta">{copy.contactPage.developedBy}</p>
          </div>
        </Card>

        <Card className="public-page__card" title={copy.contactPage.topicsTitle}>
          <ul className="public-page__list">
            {copy.contactPage.topics.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>
      </div>
    </PageShell>
  );
}
