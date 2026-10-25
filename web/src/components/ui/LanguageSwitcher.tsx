import { useI18n, type Language } from "../../lib/i18n";

interface LanguageSwitcherProps {
  className?: string;
}

const LANGUAGES: Language[] = ["en", "es"];

export function LanguageSwitcher({ className }: LanguageSwitcherProps) {
  const { copy, language, setLanguage } = useI18n();
  const classes = className ? `language-switcher ${className}` : "language-switcher";

  return (
    <div aria-label={copy.languageSwitcher.label} className={classes} role="group">
      {LANGUAGES.map((option) => (
        <button
          key={option}
          aria-label={
            option === "en" ? copy.languageSwitcher.english : copy.languageSwitcher.spanish
          }
          className={
            option === language
              ? "language-switcher__button language-switcher__button--active"
              : "language-switcher__button"
          }
          onClick={() => setLanguage(option)}
          type="button"
        >
          {option.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
