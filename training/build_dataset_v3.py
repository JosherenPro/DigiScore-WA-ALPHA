"""Dataset v3 depuis Postgres (point-in-time a applied_at, sans fuite).

Label defaut = 1 si impaye constate :
  outstanding_loan(status='impaye' AND days_late>=30) OU past_credit(status='impaye')
pour le membre. Sinon 0. Taux attendu ~4% sur 20k demandes (volume v2 synthetique :
a utiliser en shadow/demo, pas comme risque reel FUCEC).
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

QUERY = """
SELECT
  c.id AS application_id,
  m.id AS member_id,
  m.joined_on, m.status AS member_status,
  a.current_balance AS solde, a.opened_on, a.status AS account_status,
  c.requested_amount, c.term_months, c.purpose, c.product_id,
  p.max_amount AS plafond_produit, p.guarantor_threshold AS seuil_caution,
  p.is_exceptional AS exceptionnel, c.tax_status, c.esg_exclusion,
  c.has_external_credits, c.external_proofs_ok, c.applied_at,
  ie.revenue AS ca, ie.cogs AS cmv, ie.operating_costs,
  ie.financial_income, ie.personal_income, ie.family_cost,
  ie.existing_debt_service, ie.equity AS fonds_propres, ie.total_debt,
  ie.total_assets, ie.current_assets, ie.current_liabilities,
  ie.avg_inventory AS stock_moyen, ie.net_income AS resultat_net,
  ie.income_proof_level AS preuve_revenu, ie.expense_proof_level AS preuve_charge,
  COALESCE(act.is_seasonal, FALSE) AS saisonnier,
  COALESCE(mkt.single_outlet_dependency, FALSE) AS dependance,
  COALESCE(mkt.competitor_count, 0) AS concurrence,
  COALESCE((SELECT SUM((g.value_amount)::double precision) FROM application_guarantee g WHERE g.application_id=c.id),0) AS valeur_garanties,
  COALESCE((SELECT COUNT(*) FROM savings_snapshot s JOIN account a2 ON a2.id=s.account_id WHERE a2.member_id=m.id AND s.as_of <= c.applied_at::date),0) AS has_snap,
  COALESCE((SELECT s.avg_balance_3m FROM savings_snapshot s JOIN account a2 ON a2.id=s.account_id WHERE a2.member_id=m.id AND s.as_of <= c.applied_at::date ORDER BY s.as_of DESC LIMIT 1),0) AS epargne_3m,
  COALESCE((SELECT s.avg_balance_6m FROM savings_snapshot s JOIN account a2 ON a2.id=s.account_id WHERE a2.member_id=m.id AND s.as_of <= c.applied_at::date ORDER BY s.as_of DESC LIMIT 1),0) AS epargne_6m,
  COALESCE((SELECT COUNT(*) FROM account_movement mv JOIN account a2 ON a2.id=mv.account_id WHERE a2.member_id=m.id AND mv.moved_on BETWEEN (c.applied_at::date - INTERVAL '90 days')::date AND c.applied_at::date),0) AS nb_mvt_90j,
  COALESCE((SELECT COUNT(*) FROM past_credit pc WHERE pc.member_id=m.id AND pc.status='solde' AND COALESCE(pc.late_count,0)=0),0) AS nb_solde_ok,
  COALESCE((SELECT COUNT(*) FROM past_credit pc WHERE pc.member_id=m.id AND pc.status='solde'),0) AS nb_solde,
  COALESCE((SELECT COUNT(*) FROM past_credit pc WHERE pc.member_id=m.id AND pc.status='impaye'),0) AS nb_impaye,
  COALESCE((SELECT MAX(COALESCE(pc.max_days_late,0)) FROM past_credit pc WHERE pc.member_id=m.id),0) AS max_jours_past,
  COALESCE((SELECT MAX(o.days_late) FROM outstanding_loan o WHERE o.member_id=m.id),0) AS max_jours_out,
  COALESCE((SELECT COUNT(*) FROM incident i WHERE i.member_id=m.id AND i.severity='grave'),0) AS nb_grave,
  COALESCE((SELECT es.avg_balance_6m FROM external_account ea JOIN external_savings_snapshot es ON es.account_id=ea.id WHERE ea.member_id=m.id ORDER BY es.as_of DESC LIMIT 1),0) AS ext_epargne_6m,
  COALESCE((SELECT COUNT(*) FROM external_account_movement em JOIN external_account ea ON ea.id=em.account_id WHERE ea.member_id=m.id AND em.moved_on BETWEEN (c.applied_at::date - INTERVAL '90 days')::date AND c.applied_at::date),0) AS ext_mvt_90j,
  COALESCE((SELECT MAX(b.bic_incident_count) FROM bic_report b WHERE b.member_id=m.id),0) AS bic_incidents,
  COALESCE((SELECT (w.signal_revenue_erosion::int + w.signal_margin::int + w.signal_receivables::int + w.signal_payables::int + w.signal_net_worth::int) FROM wealth w WHERE w.application_id=c.id),0) AS signaux_pat,
  CASE WHEN EXISTS (SELECT 1 FROM outstanding_loan o WHERE o.member_id=m.id AND o.status='impaye' AND o.days_late>=30)
         OR EXISTS (SELECT 1 FROM past_credit pc WHERE pc.member_id=m.id AND pc.status='impaye')
       THEN 1 ELSE 0 END AS label_defaut,
  CASE WHEN EXISTS (SELECT 1 FROM outstanding_loan o WHERE o.member_id=m.id AND o.status='impaye' AND o.days_late>=30)
       THEN 1 ELSE 0 END AS label_par30_futur
FROM credit_application c
JOIN member m ON m.id=c.member_id
LEFT JOIN account a ON a.member_id=m.id
LEFT JOIN credit_product p ON p.id=c.product_id
LEFT JOIN income_expense ie ON ie.application_id=c.id
LEFT JOIN activity act ON act.application_id=c.id
LEFT JOIN market mkt ON mkt.application_id=c.id
ORDER BY c.id
"""


def dump(output: str | Path, dsn: str | None = None) -> dict:
    import psycopg

    dsn = dsn or os.getenv("DATABASE_URL", "postgresql://digiscore:digiscore@localhost:5432/digiscore")
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(dsn) as conn, conn.cursor() as cur, out.open("w", newline="", encoding="utf-8") as f:
        cur.execute(QUERY)
        cols = [d[0] for d in cur.description]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        n = 0
        npos = 0
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            # dates -> iso pour CSV
            for k in ("joined_on", "opened_on", "applied_at"):
                if d[k] is not None:
                    d[k] = str(d[k])
            n += 1
            npos += int(d["label_defaut"] or 0)
            w.writerow(d)
    return {"rows": n, "defaults": npos, "rate": round(npos / max(n, 1), 5)}
