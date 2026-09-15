import { Link } from "react-router-dom";
import { getUser, homeFor } from "../auth";
import Section from "../components/Section";

/** Politique d'utilisation — le volet réglementaire, longtemps absent du
 * produit. Chaque engagement listé ici correspond à un mécanisme réellement
 * implémenté (table, contrôle d'accès, endpoint) : rien n'est promis que le
 * système ne tienne. Les points non traités sont dits comme tels plutôt
 * qu'enjolivés — une conformité affichée à tort est un risque, pas une
 * fonctionnalité. */
export default function Politique() {
  const user = getUser();

  return (
    <div className="page politique">
      <h1>Politique d’utilisation</h1>
      <p className="lede">
        DigiScore-WA est un copilote d’éligibilité au crédit destiné aux COOPEC et IMF de l’UMOA.
        Cette page décrit ce que le système fait des données, qui peut les voir, et comment chaque
        décision reste vérifiable.
      </p>

      <Section titre="1. Principe fondateur — la décision reste humaine" defaultOpen>
        <p>
          Le moteur de score produit une <strong>recommandation</strong>, jamais une décision. Aucun crédit
          n’est accordé, conditionné ou refusé sans l’avis signé d’un Directeur (Chef d’Agence) ou du comité de crédit.
          Lorsque l’avis humain s’écarte de la recommandation, <strong>le motif est obligatoire</strong> : le
          registre refuse la décision sans justification écrite.
        </p>
        <p className="muted">
          Les éclairages d’apprentissage automatique (scorecard ML, détection d’anomalies, early warning)
          sont explicitement marqués « consultatif » dans l’interface et n’entrent jamais dans le calcul de
          la décision, qui reste produit par le moteur de règles.
        </p>
      </Section>

      <Section titre="2. Protection des données">
        <ul className="pol-list">
          <li>
            <strong>Minimisation.</strong> Seules les données nécessaires à l’instruction du crédit sont
            collectées : identité du membre, compte et mouvements de la COOPEC, données économiques de
            l’activité, pièces justificatives, garanties et cautions.
          </li>
          <li>
            <strong>Pas de données de mobile money.</strong> Les relevés Flooz / T-Money ne sont pas
            collectés. Les comptes détenus dans d’autres institutions ne sont visibles que sous forme de
            <strong> numéro masqué</strong>, et n’affectent jamais le solde local.
          </li>
          <li>
            <strong>Consentement pour la centrale des risques.</strong> L’interrogation du BIC est
            subordonnée à un consentement écrit du membre, conservé avec sa date de signature et le scan du
            document. Sans consentement signé, pas d’interrogation.
          </li>
          <li>
            <strong>Pièces justificatives.</strong> Les photos de pièces sont servies derrière
            authentification : aucune image n’est accessible par une URL publique.
          </li>
        </ul>
      </Section>

      <Section titre="3. Confidentialité et habilitations">
        <p>
          L’accès est cloisonné par rôle, contrôlé côté serveur à chaque appel — jamais seulement en
          masquant un bouton dans l’interface :
        </p>
        <ul className="pol-list">
          <li>
            <strong>Agent de crédit</strong> — crée et instruit les dossiers, consulte les fiches membres,
            consigne le suivi terrain.
          </li>
          <li>
            <strong>Directeur (Chef d’Agence)</strong> — valide, renvoie, escalade ou refuse les dossiers soumis, dans
            la limite de sa délégation. Au-delà, le dossier part automatiquement au comité.
          </li>
          <li>
            <strong>Comité de crédit (CIC)</strong> — seul habilité à signer au niveau comité. La file CIC
            est fermée aux autres rôles.
          </li>
        </ul>
        <p className="muted">
          Les sessions sont portées par un jeton à durée limitée, conservé pour la seule durée de l’onglet
          ouvert. Aucune signature n’est possible sans session authentifiée.
        </p>
      </Section>

      <Section titre="4. Auditabilité">
        <p className="pol-engagement">
          DigiScore-WA conserve toutes les décisions, les justifications du score et l’historique des
          modifications afin de répondre aux exigences d’audit et de conformité.
        </p>
        <p>Concrètement, pour chaque dossier sont conservés :</p>
        <ul className="pol-list">
          <li>
            <strong>La piste d’audit</strong> — qui, quoi, quand : chaque étape (création, collecte, pièce
            jointe, analyse, soumission, décision) est journalisée avec son auteur et son horodatage,
            consultable depuis l’écran du dossier.
          </li>
          <li>
            <strong>Les décisions</strong> — niveau, avis, auteur, date, motif, et un indicateur d’écart à
            la recommandation.
          </li>
          <li>
            <strong>L’historique des scores</strong> — chaque nouvelle analyse archive la précédente avec le
            détail des 6 critères, les knock-outs, l’explication et la <strong>version du moteur</strong>
            utilisée. Un score passé reste donc rejouable et opposable.
          </li>
          <li>
            <strong>Le barème est public dans l’outil</strong> — le détail de chacun des 6 critères est
            consultable directement sur l’écran de résultat, sans avoir à ouvrir le code.
          </li>
        </ul>
      </Section>

      <Section titre="5. Conformité BCEAO">
        <p>
          Le produit est conçu pour s’inscrire dans les exigences prudentielles applicables aux SFD de
          l’UMOA, en particulier sur les points suivants :
        </p>
        <ul className="pol-list">
          <li>
            <strong>Traçabilité des engagements</strong> — toute décision de crédit est nominative, motivée
            et horodatée.
          </li>
          <li>
            <strong>Séparation des fonctions</strong> — celui qui instruit n’est pas celui qui décide, et
            au-delà de la délégation du Directeur (Chef d’Agence) la décision remonte au comité.
          </li>
          <li>
            <strong>Suivi du portefeuille</strong> — PAR 1 / 30 / 90, balance âgée et niveaux de
            recouvrement sont calculés à partir des encours réels, pas saisis à la main.
          </li>
          <li>
            <strong>Consultation de la centrale des risques</strong> — encadrée par le consentement écrit du
            membre, avec conservation du justificatif.
          </li>
        </ul>
        <p className="pol-reserve">
          <strong>Réserve importante.</strong> Ces mécanismes outillent la conformité, ils ne la
          prononcent pas. La validation réglementaire d’un déploiement — homologation, déclaration des
          traitements, durées de conservation, convention avec la centrale des risques — relève du
          responsable conformité de l’institution, et doit précéder toute mise en production.
        </p>
      </Section>

      <Section titre="6. Limites assumées">
        <ul className="pol-list">
          <li>
            Le score s’appuie sur les données déclarées et vérifiées par l’agent. Une collecte de mauvaise
            qualité produit un score de mauvaise qualité — le système signale les dossiers à historique
            léger (<em>thin-file</em>) plutôt que de faire comme s’il savait.
          </li>
          <li>
            Les modèles d’apprentissage sont entraînés sur des données de démonstration. Leur usage en
            production suppose un réentraînement sur les données de l’institution et un suivi de dérive.
          </li>
          <li>
            Le mode dégradé (connexion faible) conserve l’accès à l’interface, mais aucune décision n’est
            signée hors ligne.
          </li>
        </ul>
      </Section>

      <div className="actions">
        <Link className="btn ghost" to={user ? homeFor(user.role) : "/"}>
          {user ? "Retour à mon espace" : "Retour à la connexion"}
        </Link>
      </div>
    </div>
  );
}
