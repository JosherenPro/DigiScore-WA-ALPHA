import type { FormEvent } from "react";

/** Recherche contextuelle — un exemplaire par page, jamais un champ générique
 * dans la sidebar : chaque page filtre ses propres données (dossiers, visites,
 * échéances…), pas toujours "chercher un membre". */
export default function PageSearch({
  value,
  onChange,
  onSubmit,
  placeholder = "Rechercher…",
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
}) {
  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit?.();
  }

  return (
    <form className="page-search" role="search" onSubmit={submit}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <circle cx="11" cy="11" r="7" />
        <path d="m21 21-4.3-4.3" />
      </svg>
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder} />
      {value && (
        <button type="button" className="page-search-clear" aria-label="Effacer" onClick={() => { onChange(""); onSubmit?.(); }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      )}
    </form>
  );
}
