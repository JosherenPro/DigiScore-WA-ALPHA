import { useState, type ReactNode } from "react";

/** Bloc de contenu repliable.
 *
 * Les fiches empilaient une dizaine de sections dépliées : la fiche membre
 * faisait plusieurs écrans de haut avant d'arriver à l'information cherchée.
 * Le principe retenu : ce qui sert à décider reste ouvert, ce qui sert à
 * vérifier se replie — mais son titre et son compteur restent lisibles, pour
 * qu'on sache qu'il y a quelque chose dedans sans avoir à ouvrir.
 */
export default function Section({
  titre,
  compteur,
  resume,
  defaultOpen = false,
  action,
  children,
}: {
  titre: string;
  compteur?: number;
  resume?: ReactNode;
  defaultOpen?: boolean;
  action?: ReactNode;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const vide = compteur === 0;

  return (
    <section className={`block sec${open ? " open" : ""}${vide ? " vide" : ""}`}>
      <button
        type="button"
        className="sec-head"
        aria-expanded={open}
        disabled={vide}
        onClick={() => !vide && setOpen((v) => !v)}
      >
        <span className="sec-titre">
          {titre}
          {compteur != null && <span className="sec-compteur">{compteur}</span>}
        </span>
        {resume && <span className="sec-resume muted">{resume}</span>}
        <span className="sec-chevron" aria-hidden="true">
          {vide ? (
            <span className="muted sec-vide-label">vide</span>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m6 9 6 6 6-6" />
            </svg>
          )}
        </span>
      </button>
      {open && !vide && (
        <div className="sec-body">
          {children}
          {action && <div className="actions">{action}</div>}
        </div>
      )}
    </section>
  );
}
