import { Card } from "../components/ui/Card";
import { SectionTitle } from "../components/ui/SectionTitle";
import { useI18n } from "../lib/i18n";
import { VERIFIKO_CONTACT_EMAIL, VERIFIKO_CONTACT_MAILTO } from "../lib/site";
import { useDocumentMeta } from "../lib/useDocumentMeta";
import { PageShell } from "../layouts/PageShell";

export function PrivacyPage() {
  const { copy } = useI18n();

  useDocumentMeta(
    copy.privacyPage.metaTitle,
    copy.privacyPage.metaDescription,
  );

  return (
    <PageShell>
      <SectionTitle
        eyebrow={copy.privacyPage.eyebrow}
        title={copy.privacyPage.title}
        description={copy.privacyPage.description}
      />

      <div className="public-page__stack">
        <Card className="public-page__card" title={copy.privacyPage.overviewTitle}>
          <div className="public-page__prose">
            {copy.privacyPage.overviewCopy.map((paragraph) => (
              <p key={paragraph} className="public-page__copy">
                {paragraph}
              </p>
            ))}
          </div>
        </Card>

        <Card className="public-page__card" title={copy.privacyPage.accountTitle}>
          <ul className="public-page__list">
            {copy.privacyPage.accountItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>

        <Card className="public-page__card" title={copy.privacyPage.verificationTitle}>
          <ul className="public-page__list">
            {copy.privacyPage.verificationItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>

        <Card className="public-page__card" title={copy.privacyPage.cookiesTitle}>
          <ul className="public-page__list">
            {copy.privacyPage.cookiesItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>

        <Card className="public-page__card" title={copy.privacyPage.contactTitle}>
          <div className="public-page__prose">
            <p className="public-page__copy">
              {copy.privacyPage.contactCopy.replace("{email}", VERIFIKO_CONTACT_EMAIL)}
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
