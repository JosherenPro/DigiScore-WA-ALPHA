import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, money, type AmortOut, type MemoOut } from "../api/client";
import Spinner from "../components/Spinner";
import Alert from "../components/Alert";
import { useApi } from "../hooks/useApi";

const APERCU = 6;

function pct(taux: number): string {
  return `${(taux * 100).toFixed(2).replace(".", ",").replace(/,00$/, "")} %`;
}

function dateCourte(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString("fr-FR", { month: "short", year: "numeric" });
}

/** Échéancier du crédit.
 *
 * Le tableau n'affichait que la mensualité hors assurance : le membre repartait
 * avec un montant inférieur à ce qu'il doit réellement chaque mois. On montre
 * désormais d'abord ce qu'il paie (mensualité totale), et le détail ensuite.
 */
function Echeancier({ am }: { am: AmortOut }) {
  const [tout, setTout] = useState(false);
  const lignes = tout ? am.lignes : am.lignes.slice(0, APERCU);
  const longue = am.lignes.length > APERCU;

  return (
    <section className="block mt-md">
      <h2>Échéancier</h2>
      <p className="ledger-note">
        Capital {money(am.montant)} sur {am.duree_mois} mois · taux nominal {pct(am.taux_nominal)} ·
        assurance {pct(am.taux_assurance)} par an.
      </p>

      {/* Ce que le membre doit retenir, avant le tableau détaillé. */}
      <div className="amort-resume">
        <div className="amort-principal">
          <span className="muted">À payer chaque mois</span>
          <strong>{money(am.mensualite_totale)}</strong>
          <span className="muted">
            dont {money(am.assurance_mensuelle)} d’assurance
          </span>
        </div>
        <div className="stat-row">
          <div className="stat-tile">
            <span className="muted">Mensualité hors assurance</span>
            <strong>{money(am.mensualite_hors_assurance)}</strong>
          </div>
          <div className="stat-tile">
            <span className="muted">Coût total du crédit</span>
            <strong>{money(am.cout_total)}</strong>
          </div>
          <div className="stat-tile">
            <span className="muted">Total à rembourser</span>
            <strong>{money(am.total_a_rembourser)}</strong>
          </div>
        </div>
      </div>

      <div className="table-scroll mt-md">
        <table className="amort-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Échéance le</th>
              <th>À payer</th>
              <th>Capital</th>
              <th>Intérêt</th>
              <th>Assurance</th>
              <th>Restant dû</th>
            </tr>
          </thead>
          <tbody>
            {lignes.map((l, i) => (
              <tr key={Number(l.numero ?? i)}>
                <td>{String(l.numero ?? i + 1)}</td>
                <td>{dateCourte(l.due_on)}</td>
                <td>
                  <strong>{money(Number(l.echeance_totale ?? l.echeance ?? 0))}</strong>
                </td>
                <td>{money(Number(l.capital ?? 0))}</td>
                <td>{money(Number(l.interet ?? 0))}</td>
                <td>{money(Number(l.assurance ?? 0))}</td>
                <td>{money(Number(l.restant ?? 0))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {longue && (
        <button className="btn ghost sm mt-sm" type="button" onClick={() => setTout((v) => !v)}>
          {tout
            ? `Réduire — n’afficher que les ${APERCU} premières`
            : `Voir les ${am.lignes.length} échéances`}
        </button>
      )}
    </section>
  );
}

export default function Memo() {
  const { id } = useParams();
  const { data: m, error, loading } = useApi<MemoOut>(() => api.memo(Number(id)), [id]);
  const [am, setAm] = useState<AmortOut | null>(null);

  useEffect(() => {
    api.amortissement(Number(id)).then(setAm).catch(() => undefined);
  }, [id]);

  if (error) return <div className="page"><Alert kind="error">{error}</Alert></div>;
  if (loading || !m) return <div className="page"><Spinner /></div>;

  return (
    <div className="page memo">
      <h1>{m.titre}</h1>
      <p className="lede">
        {m.client} — {m.projet}
      </p>
      <section className="block">
        <div className="kv">
          <span>Montant demandé</span>
          <strong>{money(m.demande)}</strong>
          <span>Avis moteur</span>
          <span>{m.avis || "—"}</span>
          {m.analyse && (
            <>
              <span>CAF</span>
              <strong>{money(m.analyse.caf)}</strong>
              <span>RCSD</span>
              <strong>{m.analyse.rcsd.toFixed(2)}</strong>
              <span>EBE</span>
              <strong>{money(m.analyse.ebe)}</strong>
            </>
          )}
        </div>
      </section>

      {/* La mensualité réelle rapportée à la capacité de remboursement : c'est
          la vérification que le comité fait de tête, autant la poser. */}
      {am && m.analyse && m.analyse.caf > 0 && (
        <p className={`msg ${am.mensualite_totale > m.analyse.caf ? "ko" : "ok"} mt-md`}>
          Mensualité totale {money(am.mensualite_totale)} pour une CAF de {money(m.analyse.caf)}
          {am.mensualite_totale > m.analyse.caf
            ? " — la charge dépasse la capacité mensuelle dégagée."
            : ` — soit ${Math.round((am.mensualite_totale / m.analyse.caf) * 100)} % de la capacité mensuelle.`}
        </p>
      )}

      <section className="block mt-md">
        <h2>Rubriques comité</h2>
        {m.rubriques.map((r) => (
          <p key={r}>{r}</p>
        ))}
      </section>

      {am && <Echeancier am={am} />}

      <div className="actions">
        <Link className="btn ghost" to={`/demandes/${id}`}>
          Retour au résultat
        </Link>
        <button className="btn ghost no-print" type="button" onClick={() => window.print()}>
          Imprimer le mémo
        </button>
      </div>
    </div>
  );
}
