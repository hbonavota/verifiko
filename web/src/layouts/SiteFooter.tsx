import { Link } from "react-router-dom";

import { useI18n } from "../lib/i18n";

interface SiteFooterProps {
  onOpenCookiePreferences?: () => void;
}

export function SiteFooter({ onOpenCookiePreferences }: SiteFooterProps) {
  const { copy } = useI18n();
  const year = new Date().getFullYear();

  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <button className="site-footer__button" onClick={onOpenCookiePreferences} type="button">
          {copy.footer.cookiePreferences}
        </button>
        <nav aria-label={copy.footer.legalLabel} className="site-footer__nav">
          <Link className="site-footer__link" to="/privacy">
            {copy.footer.privacyPolicy}
          </Link>
          <Link className="site-footer__link" to="/terms">
            {copy.footer.termsOfService}
          </Link>
          <Link className="site-footer__link" to="/contact">
            {copy.footer.contact}
          </Link>
        </nav>
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
        </p>
      </div>
    </footer>
  );
}
