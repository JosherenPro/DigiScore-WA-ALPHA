import { useState, type ReactNode } from "react";

/** Conteneur dépliable pour tout bloc d'éclairage ML.
 *
 * Replié par défaut : le ML est consultatif, il ne doit pas occuper l'écran
 * avant la décision du moteur de règles ni pousser le contenu métier sous la
 * ligne de flottaison. L'étiquette « consultatif » et le titre restent visibles
 * même replié — on doit savoir ce qu'on ouvre, et que ça ne décide rien.
 */
export default function MlSection({
  titre,
  resume,
  badge,
  defaultOpen = false,
  className = "",
  children,
}: {
  titre: string;
  resume?: ReactNode;
  badge?: ReactNode;
  defaultOpen?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className={`block ml ml-collapsible${open ? " open" : ""} ${className}`.trim()}>
      <button
        type="button"
        className="ml-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="ml-toggle-main">
          <span className="ml-tag">
            <span className="ml-dot" aria-hidden="true" /> Éclairage ML — consultatif, jamais décisionnel
          </span>
          <span className="ml-toggle-titre">{titre}</span>
          {resume && <span className="ml-toggle-resume muted">{resume}</span>}
        </span>
        <span className="ml-toggle-right">
          {badge}
          <span className="ml-chevron" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </span>
        </span>
      </button>
      {open && <div className="ml-collapsible-body">{children}</div>}
    </section>
  );
}
