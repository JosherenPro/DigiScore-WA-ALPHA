import { Link } from "react-router-dom";

/** Identité d'un membre dans les listes de portefeuille.
 *
 * Ces écrans n'affichaient que `VOL-0002912` : un code de génération, que
 * personne ne reconnaît et qu'on ne peut pas prononcer au téléphone. Le nom
 * passe devant, le code reste dessous — c'est lui qui sert à rechercher et à
 * rapprocher avec le SIG, il ne doit pas disparaître pour autant.
 */
export default function MembreLabel({
  nom,
  code,
  membreId,
  suffixe,
}: {
  nom?: string | null;
  code?: string | null;
  membreId?: number | null;
  suffixe?: string;
}) {
  // Sans nom (donnée ancienne, membre supprimé), le code reprend la vedette
  // plutôt que d'afficher une ligne vide.
  const principal = (nom || "").trim() || code || "Membre inconnu";
  const secondaire = (nom || "").trim() ? code : null;

  const titre = membreId ? (
    <Link to={`/membres/${membreId}`}>
      <strong>{principal}</strong>
    </Link>
  ) : (
    <strong>{principal}</strong>
  );

  return (
    <span className="membre-label">
      {titre}
      {(secondaire || suffixe) && (
        <span className="muted membre-label-code">
          {[secondaire, suffixe].filter(Boolean).join(" · ")}
        </span>
      )}
    </span>
  );
}
