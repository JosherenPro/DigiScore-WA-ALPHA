import { useEffect, useRef, useState } from "react";

/** Infobulle explicative, ouverte au survol/focus sur grand écran et au clic
 * partout — un agent sur téléphone n'a pas de survol. Le contenu reste dans le
 * DOM et relié par aria-describedby : un lecteur d'écran l'annonce sans avoir
 * à ouvrir quoi que ce soit. */
export default function InfoTip({
  label,
  titre,
  children,
}: {
  label: string;
  titre?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLSpanElement>(null);
  const id = useRef(`tip-${Math.random().toString(36).slice(2, 9)}`).current;

  // Clic en dehors / Échap : sinon sur mobile l'infobulle reste collée à
  // l'écran et masque la barre qu'elle explique.
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <span className={`infotip${open ? " open" : ""}`} ref={wrap}>
      <button
        type="button"
        className="infotip-btn"
        aria-label={`Comment est calculé : ${label}`}
        aria-expanded={open}
        aria-describedby={id}
        onClick={() => setOpen((v) => !v)}
      >
        ?
      </button>
      <span className="infotip-bubble" id={id} role="tooltip">
        {titre && <strong className="infotip-titre">{titre}</strong>}
        {children}
      </span>
    </span>
  );
}
