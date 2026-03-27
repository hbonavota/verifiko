import { LanguageSwitcher } from "../components/ui/LanguageSwitcher";
import { useI18n } from "../lib/i18n";

export function Topbar() {
  const { copy } = useI18n();

  return (
    <header className="topbar">
      <div>
        <p className="topbar__eyebrow">{copy.topbar.eyebrow}</p>
        <p className="topbar__title">{copy.topbar.title}</p>
      </div>
      <LanguageSwitcher className="topbar__language" />
    </header>
  );
}
