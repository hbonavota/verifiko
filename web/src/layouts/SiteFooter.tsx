import { useI18n } from "../lib/i18n";

interface SiteFooterProps {
  onOpenCookiePreferences?: () => void;
}

export function SiteFooter({ onOpenCookiePreferences }: SiteFooterProps) {
  const { copy } = useI18n();
  const year = new Date().getFullYear();

  return (
    <footer className="site-footer">
      <p className="site-footer__text">
        <span className="site-footer__year">&copy; {year} Verifiko</span>
        <span className="site-footer__separator" aria-hidden="true">
          ·
        </span>
        <span>{copy.footer.developedBy} </span>
        <a
          className="site-footer__link"
          href="https://orbytia.es/"
          rel="noreferrer"
          target="_blank"
        >
          Orbytia
        </a>
        <span className="site-footer__separator" aria-hidden="true">
          ·
        </span>
        <button className="site-footer__button" onClick={onOpenCookiePreferences} type="button">
          {copy.footer.cookiePreferences}
        </button>
      </p>
    </footer>
  );
}
