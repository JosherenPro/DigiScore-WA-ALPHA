/** Indicateur de chargement unique pour tout le produit — remplace les
 * "Chargement…" en texte brut dispersés dans chaque page. */
export default function Spinner({ label = "Chargement…" }: { label?: string }) {
  return (
    <div className="loading" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      {label}
    </div>
  );
}
