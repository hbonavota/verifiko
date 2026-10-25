interface SectionTitleProps {
  eyebrow: string;
  title: string;
  description: string;
  align?: "start" | "center";
}

export function SectionTitle({ eyebrow, title, description, align = "start" }: SectionTitleProps) {
  return (
    <div className={`section-title section-title--${align}`}>
      <p className="section-title__eyebrow">{eyebrow}</p>
      <h1 className="section-title__heading">{title}</h1>
      <p className="section-title__description">{description}</p>
    </div>
  );
}
