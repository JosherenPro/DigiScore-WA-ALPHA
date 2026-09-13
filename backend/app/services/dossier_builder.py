from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import (
    Account,
    Activity,
    ApplicationGuarantee,
    ApplicationGuarantor,
    CreditApplication,
    CreditProduct,
    GuarantorReview,
    IncomeExpense,
    Incident,
    Member,
    MonthlyCashflow,
    PastCredit,
    SavingsSnapshot,
    Wealth,
)


def _num(v, default=0):
    return float(v) if v is not None else default


def _months_since(d) -> int:
    if not d:
        return 0
    today = date(2026, 9, 13)
    return max(0, (today.year - d.year) * 12 + today.month - d.month)


def build_dossier(db: Session, application_id: int) -> dict:
    """Assemble le contrat scoring (cles FR inchangees) depuis le schema EN."""
    app = db.get(CreditApplication, application_id)
    if not app:
        raise ValueError("demande introuvable")
    member = db.get(Member, app.member_id)
    account = db.scalars(select(Account).where(Account.member_id == member.id)).first()
    snap = None
    if account:
        snap = db.scalars(select(SavingsSnapshot).where(SavingsSnapshot.account_id == account.id)).first()
    credits = db.scalars(select(PastCredit).where(PastCredit.member_id == member.id)).all()
    incidents = db.scalars(select(Incident).where(Incident.member_id == member.id)).all()
    ie = db.scalars(select(IncomeExpense).where(IncomeExpense.application_id == app.id)).first()
    wealth = db.scalars(select(Wealth).where(Wealth.application_id == app.id)).first()
    cash = db.scalars(select(MonthlyCashflow).where(MonthlyCashflow.application_id == app.id)).all()
    act = db.scalars(select(Activity).where(Activity.application_id == app.id)).first()
    gars = db.scalars(select(ApplicationGuarantee).where(ApplicationGuarantee.application_id == app.id)).all()
    product = db.get(CreditProduct, app.product_id)
    links = db.scalars(
        select(ApplicationGuarantor).where(ApplicationGuarantor.application_id == app.id)
    ).all()
    nb_ok = 0
    for link in links:
        ev = db.scalars(
            select(GuarantorReview).where(GuarantorReview.application_guarantor_id == link.id)
        ).first()
        if ev and ev.eligible:
            nb_ok += 1

    return {
        "membre": {
            "id": member.id,
            "anciennete_mois": _months_since(member.joined_on),
            "statut": member.status,
        },
        "compte": {
            "solde": _num(account.current_balance) if account else 0,
            "date_ouverture_jours": _months_since(account.opened_on) * 30 if account else 0,
            "statut": account.status if account else "inactif",
        },
        "historique": {
            "credits_passes": [
                {
                    "montant": _num(c.amount),
                    "statut": c.status,
                    "nb_retards": c.late_count or 0,
                    "jours_max_retard": c.max_days_late or 0,
                }
                for c in credits
            ],
            "incidents": [{"gravite": i.severity} for i in incidents],
            "epargne_moy_3m": _num(snap.avg_balance_3m) if snap else 0,
            "epargne_moy_6m": _num(snap.avg_balance_6m) if snap else 0,
            "nb_mouvements_90j": 4 if snap and _num(snap.avg_balance_3m) > 50000 else 1,
            "credits_ailleurs": bool(app.has_external_credits),
            "preuves_externes_ok": bool(app.external_proofs_ok),
        },
        "demande": {
            "montant": _num(app.requested_amount),
            "duree_mois": app.term_months,
            "objet": app.purpose,
            "produit_id": app.product_id,
            "plafond_produit": _num(product.max_amount) if product else 3_000_000,
            "seuil_caution": _num(product.guarantor_threshold) if product else 2_000_000,
            "exceptionnel": bool(product.is_exceptional) if product else False,
            "situation_fiscale": app.tax_status,
            "exclusion_esg": bool(app.esg_exclusion),
            "nb_cautions_eligibles": nb_ok,
            "nb_cautions_min": product.min_guarantors if product else 1,
        },
        "analyse": {
            "ca": _num(ie.revenue) if ie else 0,
            "cmv": _num(ie.cogs) if ie else 0,
            "charges_exploitation": _num(ie.operating_costs) if ie else 0,
            "produits_financiers": _num(ie.financial_income) if ie else 0,
            "revenu_perso": _num(ie.personal_income) if ie else 0,
            "charge_familiale": _num(ie.family_cost) if ie else 0,
            "charge_credits_en_cours": _num(ie.existing_debt_service) if ie else 0,
            "fonds_propres": _num(ie.equity) if ie else 0,
            "total_dettes": _num(ie.total_debt) if ie else 0,
            "actif_total": _num(ie.total_assets) if ie else 0,
            "actif_circulant": _num(ie.current_assets) if ie else 0,
            "passif_circulant": _num(ie.current_liabilities) if ie else 0,
            "stock_moyen": _num(ie.avg_inventory) if ie else 0,
            "resultat_net": _num(ie.net_income) if ie else 0,
            "valeur_garanties": sum(_num(g.value_amount) for g in gars),
            "preuve_revenu": ie.income_proof_level if ie else "N1",
            "preuve_charge": ie.expense_proof_level if ie else "N1",
            "saisonnier": bool(act.is_seasonal) if act else False,
            "tresorerie": [
                {"mois": t.month_no, "flux_entrant": _num(t.inflow), "flux_sortant": _num(t.outflow)}
                for t in cash
            ],
            "patrimoine": {
                "actifs_productifs": _num(wealth.productive_assets) if wealth else 0,
                "actifs_non_productifs": _num(wealth.non_productive_assets) if wealth else 0,
                "passifs_formels": _num(wealth.formal_liabilities) if wealth else 0,
                "passifs_informels": _num(wealth.informal_liabilities) if wealth else 0,
                "signal_erosion_ca": bool(wealth.signal_revenue_erosion) if wealth else False,
                "signal_marge": bool(wealth.signal_margin) if wealth else False,
                "signal_creances": bool(wealth.signal_receivables) if wealth else False,
                "signal_fournisseurs": bool(wealth.signal_payables) if wealth else False,
                "signal_nette": bool(wealth.signal_net_worth) if wealth else False,
            },
        },
    }
