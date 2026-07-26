import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import brandMark from "../assets/verifiko-mark.svg";
import { EmailAuthModal } from "../components/auth/EmailAuthModal";
import { GoogleSignInButton } from "../components/auth/GoogleSignInButton";
import { Button } from "../components/ui/Button";
import { LanguageSwitcher } from "../components/ui/LanguageSwitcher";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import { useDocumentMeta } from "../lib/useDocumentMeta";

export function LandingPage() {
  const { copy } = useI18n();
  const { authReady, currentUser } = useAuth();
  const navigate = useNavigate();
  const [isEmailAuthModalOpen, setIsEmailAuthModalOpen] = useState(false);

  useDocumentMeta(copy.home.metaTitle, copy.home.metaDescription);

  // Signed-in visitors don't need the marketing page — take them to the app.
  useEffect(() => {
    if (authReady && currentUser) {
      navigate("/app", { replace: true });
    }
  }, [authReady, currentUser, navigate]);

  return (
    <div className="landing">
      <header className="landing__topbar">
        <Link className="brand-lockup" to="/">
          <img alt="" className="brand-lockup__mark" height="44" src={brandMark} width="44" />
          <span className="brand-lockup__name">Verifiko</span>
        </Link>
        <div className="landing__topbar-actions">
          <LanguageSwitcher />
          <GoogleSignInButton onSuccess={() => navigate("/app")} />
          <Button
            className="landing__email-cta"
            variant="secondary"
            onClick={() => setIsEmailAuthModalOpen(true)}
          >
            {copy.landing.emailCta}
          </Button>
        </div>
      </header>

      <main className="landing__main">
        <section className="landing__hero">
          <p className="landing__eyebrow">{copy.landing.eyebrow}</p>
          <h1 className="landing__title">{copy.landing.title}</h1>
          <p className="landing__lead">{copy.landing.lead}</p>
          <div className="landing__cta">
            <Button to="/app" variant="primary" className="landing__start">
              {copy.landing.start}
            </Button>
            <p className="landing__cta-note">{copy.landing.ctaNote}</p>
          </div>
        </section>

        <section className="landing__steps" aria-label={copy.dashboard.howItWorks.title}>
          {copy.dashboard.howItWorks.steps.map((step, index) => (
            <article key={step.title} className="how-it-works__step">
              <span className="how-it-works__step-num" aria-hidden="true">
                {index + 1}
              </span>
              <div>
                <p className="how-it-works__step-title">{step.title}</p>
                <p className="how-it-works__step-copy">{step.copy}</p>
              </div>
            </article>
          ))}
        </section>
      </main>

      <EmailAuthModal
        open={isEmailAuthModalOpen}
        onClose={() => setIsEmailAuthModalOpen(false)}
      />
    </div>
  );
}
