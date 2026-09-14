import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.orm import Session

from app.auth import (
    AgentUser,
    CicUser,
    ReviewerUser,
    StaffUser,
    create_token,
    verify_password,
)
from app.db import get_db
from app.models.tables import (
    Account,
    AccountMovement,
    Activity,
    Agency,
    AmortizationLine,
    AppUser,
    ApplicationGuarantee,
    AuditLog,
    BicConsent,
    BicReport,
    CreditApplication,
    CreditProduct,
    Decision,
    EconomicModel,
    ExternalAccount,
    ExternalAccountMovement,
    FinancialInstitution,
    FinancialRatio,
    FinancialRatioHistory,
    Household,
    IncomeExpense,
    Incident,
    Market,
    Member,
    MemberGuarantee,
    MonthlyCashflow,
    OutstandingLoan,
    ParIndicator,
    PastCredit,
    PortfolioFollowup,
    RecoveryAction,
    RecoveryCase,
    SavingsSnapshot,
    ScoreResult,
    ScoreResultHistory,
    SupportingDocument,
    Wealth,
)
from app.schemas.dossier import (
    AgenceOut,
    AmortissementOut,
    CapabilitiesOut,
    CollecteIn,
    DecisionIn,
    DecisionResultOut,
    DemandeCreate,
    DemandeCreateOut,
    DemandeDetail,
    InstitutionOut,
    LoginIn,
    LoginOut,
    MembreDetail,
    MemoOut,
    OkOut,
    PageDemandes,
    PageMembres,
    PageMouvements,
    PieceIn,
    ProduitOut,
    ReferentielsOut,
    SoumettreOut,
    TokenOut,
    VisionPortefeuilleOut,
    VisionRecouvrementOut,
)
from app.services.amortissement import generer
from app.services.dossier_builder import build_dossier
from app.services.workflow import can_chef_close, next_queue
from digiscore.pipeline import run
from digiscore.types import ScoreResult as ScoringOut

router = APIRouter()

ENGINE_VERSION = "rules-v1"
AVIS_OK = frozenset({"renvoyer", "escalader", "accorder", "valider", "conditionner", "refuser"})


def _clamp_page(page: int, page_size: int) -> tuple[int, int, int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    return page, page_size, (page - 1) * page_size


def _zone_score(score: float | None) -> str | None:
    if score is None:
        return None
    if score <= 40:
        return "rejet"
    if score <= 70:
        return "analyse"
    return "approbation"


def _user_out(u: AppUser) -> dict:
    return {"id": u.id, "login": u.login, "nom": u.full_name, "role": u.role, "agence_id": u.agency_id}


@router.get("/capabilities", tags=["sante"], response_model=CapabilitiesOut)
def capabilities():
    """Stub : ML masqué. Le moteur règles reste la seule décision exposée."""
    enabled = os.getenv("ML_ENABLED", "0") == "1"
    return {
        "ml_scorecard": False,
        "anomalies": False,
        "simulation": False,
        "early_warning": False,
        "model_version": "joblib-synth" if enabled else None,
    }


@router.get("/agences", tags=["referentiel"], response_model=list[AgenceOut])
def list_agences(_user: StaffUser, db: Session = Depends(get_db)):
    rows = db.scalars(select(Agency).order_by(Agency.id)).all()
    return [{"id": a.id, "code": a.code, "nom": a.name, "ville": a.city, "topologie": a.topology} for a in rows]


@router.get("/institutions", tags=["referentiel"], response_model=list[InstitutionOut])
def list_institutions(_user: StaffUser, db: Session = Depends(get_db)):
    rows = db.scalars(select(FinancialInstitution).order_by(FinancialInstitution.id)).all()
    return [{"id": i.id, "code": i.code, "nom": i.name, "ville": i.city, "type": i.kind} for i in rows]


@router.get("/referentiels", tags=["referentiel"], response_model=ReferentielsOut)
def referentiels(_user: StaffUser):
    return {
        "statuts_membre": ["actif", "gele", "radie"],
        "statuts_demande": [
            "brouillon", "analyse", "soumis_chef", "renvoye", "soumis_cic",
            "accorde", "conditionne", "refuse", "clos",
        ],
        "avis": ["soumettre", "valider", "refuser", "renvoyer", "escalader", "accorder", "conditionner"],
        "niveaux": ["agent", "chef_agence", "cic"],
        "zones": ["rejet", "analyse", "approbation"],
        "preuves": ["N1", "N2", "N3"],
        "types_piece": ["BIC", "FISCAL", "RELEVE", "CARNET", "ECHEANCIER", "ATTESTATION_SOLDE", "CNI", "AUTRE"],
        "qualite_ocr": ["ok", "flou", "sombre", "coupe"],
    }


@router.post("/auth/login", tags=["auth"], response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalars(select(AppUser).where(AppUser.login == body.login)).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Login ou mot de passe incorrect (agent / chef / cic + demo)")
    return {"access_token": create_token(u), "token_type": "bearer", "user": _user_out(u)}


@router.get("/moi", tags=["auth"], response_model=LoginOut)
def moi(user: StaffUser):
    return _user_out(user)


@router.get("/produits", tags=["demandes"], response_model=list[ProduitOut])
def list_produits(_user: StaffUser, db: Session = Depends(get_db)):
    rows = db.scalars(select(CreditProduct)).all()
    return [
        {
            "id": p.id,
            "code": p.code,
            "libelle": p.label,
            "montant_max": float(p.max_amount),
            "seuil_montant_caution": float(p.guarantor_threshold or 0),
            "exceptionnel": bool(p.is_exceptional),
        }
        for p in rows
    ]


@router.get("/membres", tags=["membres"], response_model=PageMembres)
def search_membres(
    _user: StaffUser,
    q: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    page, page_size, offset = _clamp_page(page, page_size)
    stmt = select(Member)
    if q:
        like = f"%{q}%"
        acc_match = exists().where(Account.member_id == Member.id, Account.account_no.ilike(like))
        stmt = stmt.where(
            or_(
                Member.external_code.ilike(like),
                Member.last_name.ilike(like),
                Member.first_name.ilike(like),
                acc_match,
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Member.id).offset(offset).limit(page_size)).all()
    return {
        "items": [
            {
                "id": m.id,
                "code_externe": m.external_code,
                "nom": m.last_name,
                "prenom": m.first_name,
                "statut": m.status,
                "date_adhesion": str(m.joined_on),
                "agence_id": m.agency_id,
            }
            for m in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/membres/{membre_id}", tags=["membres"], response_model=MembreDetail)
def get_membre(membre_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    m = db.get(Member, membre_id)
    if not m:
        raise HTTPException(404, "Membre introuvable")
    account = db.scalars(select(Account).where(Account.member_id == m.id)).first()
    snap = None
    if account:
        snap = db.scalars(select(SavingsSnapshot).where(SavingsSnapshot.account_id == account.id)).first()
    credits = db.scalars(select(PastCredit).where(PastCredit.member_id == m.id)).all()
    incidents = db.scalars(select(Incident).where(Incident.member_id == m.id)).all()
    today = date.today()
    anciennete = (today.year - m.joined_on.year) * 12 + today.month - m.joined_on.month
    thin = anciennete < 3 or (not credits and (not snap or float(snap.avg_balance_6m or 0) < 80000))
    ag = db.get(Agency, m.agency_id) if m.agency_id else None
    n_mvt = 0
    if account:
        n_mvt = db.scalar(select(func.count()).select_from(AccountMovement).where(AccountMovement.account_id == account.id)) or 0
    n_apps = db.scalar(select(func.count()).select_from(CreditApplication).where(CreditApplication.member_id == m.id)) or 0
    n_ext = db.scalar(select(func.count()).select_from(ExternalAccount).where(ExternalAccount.member_id == m.id)) or 0
    gars = db.scalars(select(MemberGuarantee).where(MemberGuarantee.member_id == m.id)).all()
    inst_map = {i.id: i.name for i in db.scalars(select(FinancialInstitution)).all()}
    return {
        "id": m.id,
        "code_externe": m.external_code,
        "nom": m.last_name,
        "prenom": m.first_name,
        "telephone": m.phone,
        "adresse": m.address,
        "occupation": m.occupation,
        "statut": m.status,
        "zone": m.area,
        "date_adhesion": str(m.joined_on),
        "anciennete_mois": anciennete,
        "thin_file": thin,
        "agence": None if not ag else {"id": ag.id, "code": ag.code, "nom": ag.name, "ville": ag.city},
        "compte": None
        if not account
        else {
            "numero": account.account_no,
            "statut": account.status,
            "solde": float(account.current_balance),
            "epargne_moy_6m": float(snap.avg_balance_6m) if snap else 0,
        },
        "credits_passes": [
            {
                "montant": float(c.amount),
                "statut": c.status,
                "nb_retards": c.late_count,
                "jours_max_retard": c.max_days_late,
                "source": c.source,
                "institution": inst_map.get(c.institution_id) if c.institution_id else None,
                "date_octroi": str(c.granted_on) if c.granted_on else None,
            }
            for c in credits
        ],
        "incidents": [
            {
                "type": i.incident_type,
                "gravite": i.severity,
                "detail": i.detail,
                "date": str(i.occurred_on),
            }
            for i in incidents
        ],
        "nb_mouvements": int(n_mvt),
        "nb_credits_passes": len(credits),
        "nb_demandes": int(n_apps),
        "nb_comptes_externes": int(n_ext),
        "garanties": [{"nature": g.kind, "valeur": float(g.value_amount or 0)} for g in gars],
    }


def _member_account(db: Session, membre_id: int) -> tuple[Member, Account | None]:
    m = db.get(Member, membre_id)
    if not m:
        raise HTTPException(404, "Membre introuvable")
    account = db.scalars(select(Account).where(Account.member_id == m.id)).first()
    return m, account


@router.get("/membres/{membre_id}/historique", tags=["membres"])
def historique(membre_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    m, account = _member_account(db, membre_id)
    inst_map = {i.id: i.name for i in db.scalars(select(FinancialInstitution)).all()}
    credits = db.scalars(select(PastCredit).where(PastCredit.member_id == m.id)).all()
    incidents = db.scalars(select(Incident).where(Incident.member_id == m.id)).all()
    mvts = []
    total_mvt = 0
    if account:
        total_mvt = db.scalar(select(func.count()).select_from(AccountMovement).where(AccountMovement.account_id == account.id)) or 0
        mvts = db.scalars(
            select(AccountMovement)
            .where(AccountMovement.account_id == account.id)
            .order_by(AccountMovement.moved_on.desc())
            .limit(30)
        ).all()
    n_ext = db.scalar(select(func.count()).select_from(ExternalAccount).where(ExternalAccount.member_id == m.id)) or 0
    return {
        "id": m.id,
        "code_externe": m.external_code,
        "credits_passes": [
            {
                "montant": float(c.amount),
                "statut": c.status,
                "nb_retards": c.late_count,
                "jours_max_retard": c.max_days_late,
                "source": c.source,
                "institution": inst_map.get(c.institution_id) if c.institution_id else None,
            }
            for c in credits
        ],
        "incidents": [
            {"type": i.incident_type, "gravite": i.severity, "detail": i.detail, "date": str(i.occurred_on)}
            for i in incidents
        ],
        "mouvements": [
            {"date": str(x.moved_on), "type": x.movement_type, "montant": float(x.amount), "libelle": x.label}
            for x in mvts
        ],
        "total_mouvements": int(total_mvt),
        "nb_comptes_externes": int(n_ext),
    }


@router.get("/membres/{membre_id}/mouvements", tags=["membres"], response_model=PageMouvements)
def membre_mouvements(
    membre_id: int,
    _user: StaffUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _m, account = _member_account(db, membre_id)
    page, page_size, offset = _clamp_page(page, page_size)
    if not account:
        return {"items": [], "page": page, "page_size": page_size, "total": 0}
    total = db.scalar(select(func.count()).select_from(AccountMovement).where(AccountMovement.account_id == account.id)) or 0
    rows = db.scalars(
        select(AccountMovement)
        .where(AccountMovement.account_id == account.id)
        .order_by(AccountMovement.moved_on.desc())
        .offset(offset)
        .limit(page_size)
    ).all()
    return {
        "items": [{"date": str(x.moved_on), "type": x.movement_type, "montant": float(x.amount), "libelle": x.label} for x in rows],
        "page": page,
        "page_size": page_size,
        "total": int(total),
    }


@router.get("/membres/{membre_id}/credits-passes", tags=["membres"])
def membre_credits(membre_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    m, _ = _member_account(db, membre_id)
    inst_map = {i.id: i.name for i in db.scalars(select(FinancialInstitution)).all()}
    rows = db.scalars(select(PastCredit).where(PastCredit.member_id == m.id)).all()
    return [
        {
            "montant": float(c.amount),
            "statut": c.status,
            "nb_retards": c.late_count,
            "jours_max_retard": c.max_days_late,
            "source": c.source,
            "institution": inst_map.get(c.institution_id) if c.institution_id else None,
            "date_octroi": str(c.granted_on) if c.granted_on else None,
        }
        for c in rows
    ]


@router.get("/membres/{membre_id}/incidents", tags=["membres"])
def membre_incidents(membre_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    m, _ = _member_account(db, membre_id)
    rows = db.scalars(select(Incident).where(Incident.member_id == m.id)).all()
    return [{"type": i.incident_type, "gravite": i.severity, "detail": i.detail, "date": str(i.occurred_on)} for i in rows]


@router.get("/membres/{membre_id}/garanties", tags=["membres"])
def membre_garanties(membre_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    m, _ = _member_account(db, membre_id)
    rows = db.scalars(select(MemberGuarantee).where(MemberGuarantee.member_id == m.id)).all()
    return [{"nature": g.kind, "valeur": float(g.value_amount or 0)} for g in rows]


@router.get("/membres/{membre_id}/prets", tags=["membres"])
def membre_prets(membre_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    m, _ = _member_account(db, membre_id)
    rows = db.scalars(select(OutstandingLoan).where(OutstandingLoan.member_id == m.id)).all()
    return [
        {
            "principal": float(p.principal),
            "encours": float(p.outstanding),
            "jours_retard": p.days_late,
            "statut": p.status,
            "decaissement": str(p.disbursed_on) if p.disbursed_on else None,
            "echeance": str(p.due_on) if p.due_on else None,
            "observation": str(p.observed_on) if p.observed_on else None,
        }
        for p in rows
    ]


@router.get("/membres/{membre_id}/demandes", tags=["membres"], response_model=PageDemandes)
def membre_demandes(
    membre_id: int,
    user: StaffUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _member_account(db, membre_id)
    return list_demandes(user, statut=None, page=page, page_size=page_size, db=db, membre_id=membre_id)


@router.get("/membres/{membre_id}/bic", tags=["membres"])
def membre_bic(membre_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    m, _ = _member_account(db, membre_id)
    consent = db.scalars(select(BicConsent).where(BicConsent.member_id == m.id)).first()
    report = db.scalars(select(BicReport).where(BicReport.member_id == m.id)).first()
    return {
        "consentement": None
        if not consent
        else {"statut": consent.status, "signe_le": str(consent.signed_on), "scan": consent.scan_path},
        "rapport": None
        if not report
        else {
            "nb_credits_externes": report.external_credit_count,
            "nb_incidents": report.bic_incident_count,
            "synthese": report.indebtedness_summary,
            "source": report.source,
        },
    }


@router.get("/membres/{membre_id}/suivi", tags=["membres"])
def membre_suivi(membre_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    m, _ = _member_account(db, membre_id)
    rows = db.scalars(select(PortfolioFollowup).where(PortfolioFollowup.member_id == m.id)).all()
    return [
        {"visite": r.visit_code, "date": str(r.visit_on) if r.visit_on else None, "jours_retard": r.days_late, "signal": r.signal}
        for r in rows
    ]


@router.get("/membres/{membre_id}/recouvrement", tags=["membres"])
def membre_recouvrement(membre_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    m, _ = _member_account(db, membre_id)
    rows = db.scalars(select(RecoveryCase).where(RecoveryCase.member_id == m.id)).all()
    out = []
    for r in rows:
        acts = db.scalars(select(RecoveryAction).where(RecoveryAction.case_id == r.id)).all()
        out.append(
            {
                "niveau": r.level,
                "action": r.action,
                "responsable": r.owner_name,
                "ouvert_le": str(r.opened_on) if r.opened_on else None,
                "journal": [{"date": str(a.action_on), "type": a.action_type, "note": a.note} for a in acts],
            }
        )
    return out


@router.get("/membres/{membre_id}/comptes-externes", tags=["membres"])
def membre_comptes_externes(membre_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    m, _ = _member_account(db, membre_id)
    rows = db.scalars(select(ExternalAccount).where(ExternalAccount.member_id == m.id)).all()
    inst_map = {i.id: i for i in db.scalars(select(FinancialInstitution)).all()}
    return [
        {
            "id": a.id,
            "numero_masque": a.account_no_mask,
            "solde": float(a.current_balance),
            "statut": a.status,
            "ouvert_le": str(a.opened_on),
            "institution": {
                "id": a.institution_id,
                "code": inst_map[a.institution_id].code,
                "nom": inst_map[a.institution_id].name,
                "type": inst_map[a.institution_id].kind,
            }
            if a.institution_id in inst_map
            else None,
        }
        for a in rows
    ]


@router.get("/membres/{membre_id}/mouvements-externes", tags=["membres"], response_model=PageMouvements)
def membre_mouvements_externes(
    membre_id: int,
    _user: StaffUser,
    institution_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    m, _ = _member_account(db, membre_id)
    page, page_size, offset = _clamp_page(page, page_size)
    accs = db.scalars(select(ExternalAccount).where(ExternalAccount.member_id == m.id)).all()
    if institution_id:
        accs = [a for a in accs if a.institution_id == institution_id]
    ids = [a.id for a in accs]
    if not ids:
        return {"items": [], "page": page, "page_size": page_size, "total": 0}
    total = db.scalar(
        select(func.count()).select_from(ExternalAccountMovement).where(ExternalAccountMovement.account_id.in_(ids))
    ) or 0
    rows = db.scalars(
        select(ExternalAccountMovement)
        .where(ExternalAccountMovement.account_id.in_(ids))
        .order_by(ExternalAccountMovement.moved_on.desc())
        .offset(offset)
        .limit(page_size)
    ).all()
    return {
        "items": [{"date": str(x.moved_on), "type": x.movement_type, "montant": float(x.amount), "libelle": x.label} for x in rows],
        "page": page,
        "page_size": page_size,
        "total": int(total),
    }


def _persist_collecte(db: Session, application_id: int, c: CollecteIn) -> None:
    existing = db.scalars(select(IncomeExpense).where(IncomeExpense.application_id == application_id)).first()
    fields = dict(
        application_id=application_id,
        revenue=c.ca,
        cogs=c.cmv,
        operating_costs=c.charges_exploitation,
        financial_income=c.produits_financiers,
        personal_income=c.revenu_perso,
        family_cost=c.charge_familiale,
        existing_debt_service=c.charge_credits_en_cours,
        equity=c.fonds_propres,
        total_debt=c.total_dettes,
        total_assets=c.actif_total,
        current_assets=c.actif_circulant,
        current_liabilities=c.passif_circulant,
        avg_inventory=c.stock_moyen,
        net_income=c.resultat_net,
        income_proof_level=c.preuve_revenu,
        expense_proof_level=c.preuve_charge,
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(IncomeExpense(**fields))
    act = db.scalars(select(Activity).where(Activity.application_id == application_id)).first()
    if act:
        act.is_seasonal = c.saisonnier
        act.activity_type = c.type_activite
    else:
        db.add(
            Activity(
                application_id=application_id,
                activity_type=c.type_activite,
                is_seasonal=c.saisonnier,
            )
        )
    if c.valeur_garanties:
        db.add(
            ApplicationGuarantee(
                application_id=application_id,
                kind="Saisie terrain",
                value_amount=c.valeur_garanties,
            )
        )


@router.post("/demandes", tags=["demandes"], response_model=DemandeCreateOut)
def create_demande(body: DemandeCreate, user: AgentUser, db: Session = Depends(get_db)):
    m = db.get(Member, body.membre_id)
    if not m:
        raise HTTPException(400, "NON_MEMBRE")
    account = db.scalars(select(Account).where(Account.member_id == m.id)).first()
    if m.status != "actif" or not account or account.status != "actif":
        raise HTTPException(400, "COMPTE_INACTIF")
    app = CreditApplication(
        member_id=body.membre_id,
        product_id=body.produit_id,
        agent_id=user.id,
        agency_id=m.agency_id,
        purpose=body.objet,
        requested_amount=body.montant_demande,
        term_months=body.duree_mois,
        status="brouillon",
        tax_status=body.situation_fiscale,
        has_external_credits=body.credits_ailleurs,
        external_proofs_ok=body.preuves_externes_ok,
        esg_exclusion=False,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    if body.collecte:
        _persist_collecte(db, app.id, body.collecte)
    db.add(AuditLog(application_id=app.id, user_id=user.id, action="create", detail=body.objet))
    db.commit()
    return {"id": app.id, "statut": app.status}


@router.post("/demandes/{demande_id}/collecte", tags=["demandes"], response_model=OkOut)
def save_collecte(demande_id: int, body: CollecteIn, _user: AgentUser, db: Session = Depends(get_db)):
    if not db.get(CreditApplication, demande_id):
        raise HTTPException(404, "Demande introuvable")
    _persist_collecte(db, demande_id, body)
    db.commit()
    return {"ok": True}


@router.post("/demandes/{demande_id}/pieces", tags=["demandes"], response_model=OkOut)
def add_piece(demande_id: int, body: PieceIn, _user: AgentUser, db: Session = Depends(get_db)):
    if not db.get(CreditApplication, demande_id):
        raise HTTPException(404, "Demande introuvable")
    if body.qualite_ocr in ("flou", "sombre", "coupe"):
        raise HTTPException(400, "Qualite photo insuffisante : recommencer la prise")
    db.add(
        SupportingDocument(
            application_id=demande_id,
            document_type=body.type_piece,
            file_path=body.fichier,
            ocr_quality=body.qualite_ocr,
            status="recu",
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/demandes", tags=["demandes"], response_model=PageDemandes)
def list_demandes(
    _user: StaffUser,
    statut: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    membre_id: int | None = None,
    db: Session = Depends(get_db),
):
    page, page_size, offset = _clamp_page(page, page_size)
    stmt = select(CreditApplication)
    if statut:
        stmt = stmt.where(CreditApplication.status == statut)
    if membre_id:
        stmt = stmt.where(CreditApplication.member_id == membre_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(CreditApplication.id.desc()).offset(offset).limit(page_size)).all()
    items = []
    for d in rows:
        m = db.get(Member, d.member_id)
        sc = db.scalars(select(ScoreResult).where(ScoreResult.application_id == d.id)).first()
        score = float(sc.score_total) if sc else None
        items.append(
            {
                "id": d.id,
                "membre": f"{m.first_name} {m.last_name}" if m else "",
                "membre_id": d.member_id,
                "montant_demande": float(d.requested_amount),
                "statut": d.status,
                "score": score,
                "message_code": sc.message_code if sc else None,
                "zone": _zone_score(score),
            }
        )
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/demandes/{demande_id}", tags=["demandes"], response_model=DemandeDetail)
def get_demande(demande_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    d = db.get(CreditApplication, demande_id)
    if not d:
        raise HTTPException(404, "Demande introuvable")
    sc = db.scalars(select(ScoreResult).where(ScoreResult.application_id == d.id)).first()
    ratios = db.scalars(select(FinancialRatio).where(FinancialRatio.application_id == d.id)).first()
    decs = db.scalars(select(Decision).where(Decision.application_id == d.id)).all()
    pieces = db.scalars(select(SupportingDocument).where(SupportingDocument.application_id == d.id)).all()
    score_val = float(sc.score_total) if sc else None
    membre = db.get(Member, d.member_id)
    prod = db.get(CreditProduct, d.product_id)
    ie = db.scalars(select(IncomeExpense).where(IncomeExpense.application_id == d.id)).first()
    wealth = db.scalars(select(Wealth).where(Wealth.application_id == d.id)).first()
    hh = db.scalars(select(Household).where(Household.application_id == d.id)).first()
    act = db.scalars(select(Activity).where(Activity.application_id == d.id)).first()
    cash = db.scalars(select(MonthlyCashflow).where(MonthlyCashflow.application_id == d.id).order_by(MonthlyCashflow.month_no)).all()
    ecom = db.scalars(select(EconomicModel).where(EconomicModel.application_id == d.id)).first()
    mkt = db.scalars(select(Market).where(Market.application_id == d.id)).first()
    return {
        "id": d.id,
        "membre_id": d.member_id,
        "produit_id": d.product_id,
        "objet": d.purpose,
        "montant_demande": float(d.requested_amount),
        "duree_mois": d.term_months,
        "statut": d.status,
        "situation_fiscale": d.tax_status,
        "membre": None
        if not membre
        else {"id": membre.id, "code_externe": membre.external_code, "nom": membre.last_name, "prenom": membre.first_name},
        "produit": None
        if not prod
        else {"id": prod.id, "code": prod.code, "libelle": prod.label, "exceptionnel": bool(prod.is_exceptional)},
        "score": None
        if not sc
        else {
            "score_global": score_val,
            "thin_file": sc.thin_file,
            "eligible": sc.eligible,
            "montant_eligible": float(sc.eligible_amount),
            "montant_max_suggestion": float(sc.suggested_max_amount or 0),
            "message_code": sc.message_code,
            "message_humain": sc.message_text,
            "criteres": sc.criteria,
            "knockouts": sc.knockouts,
            "explication": sc.explanation,
            "zone": _zone_score(score_val),
        },
        "ratios": None
        if not ratios
        else {
            "caf": float(ratios.caf or 0),
            "rcsd": float(ratios.rcsd or 0),
            "ebe": float(ratios.ebe or 0),
        },
        "decisions": [
            {"niveau": x.level, "avis": x.opinion, "motif": x.reason, "override": x.is_override}
            for x in decs
        ],
        "pieces": [{"type_piece": p.document_type, "qualite_ocr": p.ocr_quality} for p in pieces],
        "collecte": None
        if not ie
        else {
            "ca": float(ie.revenue or 0),
            "cmv": float(ie.cogs or 0),
            "charges_exploitation": float(ie.operating_costs or 0),
            "produits_financiers": float(ie.financial_income or 0),
            "revenu_perso": float(ie.personal_income or 0),
            "charge_familiale": float(ie.family_cost or 0),
            "preuve_revenu": ie.income_proof_level,
            "preuve_charge": ie.expense_proof_level,
            "modele": None
            if not ecom
            else {"segments": ecom.client_segments, "offre": ecom.product_service, "prix": float(ecom.avg_price or 0)},
            "marche": None
            if not mkt
            else {"haute_saison": mkt.high_season, "basse_saison": mkt.low_season, "concurrents": mkt.competitor_count},
        },
        "tresorerie": [
            {
                "mois": c.month_no,
                "periode": str(c.period_month) if c.period_month else None,
                "encaissements": float(c.inflow or 0),
                "decaissements": float(c.outflow or 0),
            }
            for c in cash
        ],
        "patrimoine": None
        if not wealth
        else {
            "actifs_productifs": float(wealth.productive_assets or 0),
            "actifs_non_productifs": float(wealth.non_productive_assets or 0),
        },
        "menage": None if not hh else {"taille": hh.household_size, "logement": hh.housing, "charges": hh.dependents},
        "activite": None
        if not act
        else {"type": act.activity_type, "saisonnier": act.is_seasonal, "description": act.description},
    }


@router.get("/demandes/{demande_id}/score", tags=["workflow"])
def get_score(demande_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    d = db.get(CreditApplication, demande_id)
    if not d:
        raise HTTPException(404, "Demande introuvable")
    sc = db.scalars(select(ScoreResult).where(ScoreResult.application_id == d.id)).first()
    if not sc:
        raise HTTPException(404, "Pas encore analyse")
    score_val = float(sc.score_total)
    return {
        "score_global": score_val,
        "thin_file": sc.thin_file,
        "eligible": sc.eligible,
        "montant_eligible": float(sc.eligible_amount),
        "montant_max_suggestion": float(sc.suggested_max_amount or 0),
        "message_code": sc.message_code,
        "message_humain": sc.message_text,
        "zone": _zone_score(score_val),
        "engine_version": sc.engine_version,
    }


@router.get("/demandes/{demande_id}/scores", tags=["workflow"])
def get_score_history(demande_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    if not db.get(CreditApplication, demande_id):
        raise HTTPException(404, "Demande introuvable")
    rows = db.scalars(
        select(ScoreResultHistory)
        .where(ScoreResultHistory.application_id == demande_id)
        .order_by(ScoreResultHistory.history_id.desc())
    ).all()
    return [
        {
            "score_global": float(r.score_total),
            "message_code": r.message_code,
            "eligible": r.eligible,
            "montant_eligible": float(r.eligible_amount),
            "engine_version": r.engine_version,
            "analyse_le": str(r.scored_at) if r.scored_at else None,
        }
        for r in rows
    ]


@router.get("/demandes/{demande_id}/ratios", tags=["workflow"])
def get_ratios(demande_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    ratios = db.scalars(select(FinancialRatio).where(FinancialRatio.application_id == demande_id)).first()
    if not ratios:
        raise HTTPException(404, "Pas de ratios")
    return {"caf": float(ratios.caf or 0), "rcsd": float(ratios.rcsd or 0), "ebe": float(ratios.ebe or 0)}


@router.get("/demandes/{demande_id}/collecte", tags=["demandes"])
def get_collecte(demande_id: int, user: StaffUser, db: Session = Depends(get_db)):
    body = get_demande(demande_id, user, db)
    return {"collecte": body.get("collecte"), "tresorerie": body.get("tresorerie"), "patrimoine": body.get("patrimoine")}


@router.get("/demandes/{demande_id}/tresorerie", tags=["demandes"])
def get_tresorerie(demande_id: int, user: StaffUser, db: Session = Depends(get_db)):
    return get_demande(demande_id, user, db).get("tresorerie") or []


@router.get("/demandes/{demande_id}/pieces", tags=["demandes"])
def get_pieces(demande_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    if not db.get(CreditApplication, demande_id):
        raise HTTPException(404, "Demande introuvable")
    pieces = db.scalars(select(SupportingDocument).where(SupportingDocument.application_id == demande_id)).all()
    return [{"type_piece": p.document_type, "qualite_ocr": p.ocr_quality, "fichier": p.file_path} for p in pieces]


@router.get("/demandes/{demande_id}/decisions", tags=["workflow"])
def get_decisions(demande_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    if not db.get(CreditApplication, demande_id):
        raise HTTPException(404, "Demande introuvable")
    decs = db.scalars(select(Decision).where(Decision.application_id == demande_id)).all()
    return [{"niveau": x.level, "avis": x.opinion, "motif": x.reason, "override": x.is_override} for x in decs]


@router.get("/demandes/{demande_id}/audit", tags=["workflow"])
def get_audit(demande_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    if not db.get(CreditApplication, demande_id):
        raise HTTPException(404, "Demande introuvable")
    rows = db.scalars(select(AuditLog).where(AuditLog.application_id == demande_id)).all()
    return [{"action": r.action, "detail": r.detail} for r in rows]


@router.get("/demandes/{demande_id}/cautions", tags=["demandes"])
def get_cautions(demande_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    if not db.get(CreditApplication, demande_id):
        raise HTTPException(404, "Demande introuvable")
    gars = db.scalars(select(ApplicationGuarantee).where(ApplicationGuarantee.application_id == demande_id)).all()
    return [{"nature": g.kind, "valeur": float(g.value_amount or 0)} for g in gars]


def _archive_score(db: Session, existing: ScoreResult) -> None:
    db.add(
        ScoreResultHistory(
            application_id=existing.application_id,
            score_total=existing.score_total,
            thin_file=existing.thin_file,
            eligible=existing.eligible,
            requested_amount=existing.requested_amount,
            eligible_amount=existing.eligible_amount,
            suggested_max_amount=existing.suggested_max_amount,
            message_code=existing.message_code,
            message_text=existing.message_text,
            criteria=existing.criteria,
            knockouts=existing.knockouts,
            explanation=existing.explanation,
            engine_version=existing.engine_version or ENGINE_VERSION,
            scored_at=existing.created_at,
        )
    )


def _archive_ratio(db: Session, ratio: FinancialRatio) -> None:
    db.add(
        FinancialRatioHistory(
            application_id=ratio.application_id,
            ebe=ratio.ebe,
            caf=ratio.caf,
            rcsd=ratio.rcsd,
            gross_margin_pct=ratio.gross_margin_pct,
            net_margin_pct=ratio.net_margin_pct,
            solvency=ratio.solvency,
            inventory_days=ratio.inventory_days,
            equity_ratio_pct=ratio.equity_ratio_pct,
            working_capital_pct=ratio.working_capital_pct,
            net_worth=ratio.net_worth,
            weak_ratio_count=ratio.weak_ratio_count,
            stress_month=ratio.stress_month,
            computed_at=ratio.computed_at,
        )
    )


@router.post("/demandes/{demande_id}/analyser", tags=["workflow"], response_model=ScoringOut)
def analyser(demande_id: int, user: StaffUser, db: Session = Depends(get_db)):
    try:
        dossier = build_dossier(db, demande_id)
    except ValueError:
        raise HTTPException(404, "Demande introuvable")
    result = run(dossier)
    existing = db.scalars(select(ScoreResult).where(ScoreResult.application_id == demande_id)).first()
    payload = dict(
        application_id=demande_id,
        score_total=result.score_global,
        thin_file=result.thin_file,
        eligible=result.eligible,
        requested_amount=result.montant_demande,
        eligible_amount=result.montant_eligible,
        suggested_max_amount=result.montant_max_suggestion,
        message_code=result.message_code,
        message_text=result.message_humain,
        criteria=[c.model_dump() for c in result.criteres],
        knockouts=[k.model_dump() for k in result.knockouts],
        explanation=result.explication,
        engine_version=ENGINE_VERSION,
    )
    if existing:
        _archive_score(db, existing)
        for k, v in payload.items():
            setattr(existing, k, v)
    else:
        db.add(ScoreResult(**payload))

    fin = result.financials
    ratio = db.scalars(select(FinancialRatio).where(FinancialRatio.application_id == demande_id)).first()
    rdata = dict(
        application_id=demande_id,
        ebe=fin.get("ebe"),
        caf=fin.get("caf"),
        rcsd=fin.get("rcsd"),
        gross_margin_pct=fin.get("marge_brute_pct"),
        net_margin_pct=fin.get("benefice_net_pct"),
        solvency=fin.get("solvabilite"),
        inventory_days=fin.get("rotation_stocks_jours"),
        equity_ratio_pct=fin.get("participation_pct"),
        working_capital_pct=fin.get("fonds_roulement_pct"),
        net_worth=fin.get("situation_nette"),
        weak_ratio_count=fin.get("nb_ratios_degrades"),
        stress_month=fin.get("mois_critique"),
    )
    if ratio:
        _archive_ratio(db, ratio)
        for k, v in rdata.items():
            setattr(ratio, k, v)
    else:
        db.add(FinancialRatio(**rdata))

    app = db.get(CreditApplication, demande_id)
    app.status = "analyse"
    db.add(AuditLog(application_id=demande_id, user_id=user.id, action="analyser", detail=result.message_code))
    db.commit()
    return result.model_dump()


@router.post("/demandes/{demande_id}/soumettre", tags=["workflow"], response_model=SoumettreOut)
def soumettre(demande_id: int, user: AgentUser, db: Session = Depends(get_db)):
    app = db.get(CreditApplication, demande_id)
    sc = db.scalars(select(ScoreResult).where(ScoreResult.application_id == demande_id)).first()
    if not app or not sc:
        raise HTTPException(400, "Analyser le dossier avant soumission")
    zone = _zone_score(float(sc.score_total)) or "analyse"
    cible = next_queue(zone, sc.message_code, float(app.requested_amount))
    app.status = "soumis_cic" if cible == "cic" else "soumis_chef"
    db.add(
        Decision(
            application_id=demande_id,
            level="agent",
            opinion="soumettre",
            user_id=user.id,
        )
    )
    db.add(
        AuditLog(
            application_id=demande_id,
            user_id=user.id,
            action="soumettre",
            detail=app.status,
        )
    )
    db.commit()
    return {"statut": app.status, "file": cible}


@router.post("/demandes/{demande_id}/decision", tags=["workflow"], response_model=DecisionResultOut)
def decision(demande_id: int, body: DecisionIn, user: ReviewerUser, db: Session = Depends(get_db)):
    app = db.get(CreditApplication, demande_id)
    if not app:
        raise HTTPException(404)
    if body.avis not in AVIS_OK:
        raise HTTPException(400, f"Avis inconnu : {body.avis}")
    if body.niveau == "chef_agence" and user.role != "chef_agence":
        raise HTTPException(403, "Seul le chef d'agence peut signer a ce niveau")
    if body.niveau == "cic" and user.role != "cic":
        raise HTTPException(403, "Seul le CIC peut signer a ce niveau")
    if body.niveau not in ("chef_agence", "cic"):
        raise HTTPException(400, "niveau doit etre chef_agence ou cic")
    sc = db.scalars(select(ScoreResult).where(ScoreResult.application_id == demande_id)).first()
    zone = "approbation"
    if sc:
        zone = _zone_score(float(sc.score_total)) or "approbation"
    reco = "accorder" if zone == "approbation" else ("refuser" if zone == "rejet" else "escalader")
    override = body.override or (
        body.avis not in (reco, "renvoyer", "escalader", "soumettre", "valider", "conditionner")
    )
    if override and not body.motif:
        raise HTTPException(400, "Motif obligatoire en cas d'ecart a la recommandation")
    db.add(
        Decision(
            application_id=demande_id,
            level=body.niveau,
            opinion=body.avis,
            reason=body.motif,
            is_override=override,
            user_id=user.id,
        )
    )
    if body.avis == "renvoyer":
        app.status = "renvoye"
    elif body.avis == "escalader":
        app.status = "soumis_cic"
    elif body.avis in ("accorder", "valider"):
        if body.niveau == "chef_agence" and sc and not can_chef_close(
            zone, sc.message_code, float(app.requested_amount)
        ):
            app.status = "soumis_cic"
        else:
            app.status = "accorde"
    elif body.avis == "conditionner":
        app.status = "conditionne"
    elif body.avis == "refuser":
        app.status = "refuse"
    db.add(
        AuditLog(
            application_id=demande_id,
            user_id=user.id,
            action=body.avis,
            detail=body.motif,
        )
    )
    db.commit()
    return {"statut": app.status, "override": override}


@router.get("/demandes/{demande_id}/memo", tags=["workflow"], response_model=MemoOut)
def memo(demande_id: int, user: StaffUser, db: Session = Depends(get_db)):
    d = get_demande(demande_id, user, db)
    m = db.get(Member, d["membre_id"])
    return {
        "titre": "Memo de credit DigiScore-WA",
        "client": f"{m.first_name} {m.last_name}" if m else "",
        "projet": d["objet"],
        "demande": d["montant_demande"],
        "analyse": d.get("ratios"),
        "score": d.get("score"),
        "avis": (d.get("score") or {}).get("message_humain"),
        "rubriques": [
            "1. Presentation client et projet",
            "2. Demande de credit",
            "3. Analyse economique et financiere",
            "4. Risques et attenuation",
            "5. Garanties et conditions",
            "6. Avis motive",
        ],
    }


@router.get("/demandes/{demande_id}/amortissement", tags=["workflow"], response_model=AmortissementOut)
def amortissement(demande_id: int, _user: StaffUser, db: Session = Depends(get_db)):
    app = db.get(CreditApplication, demande_id)
    if not app:
        raise HTTPException(404)
    sc = db.scalars(select(ScoreResult).where(ScoreResult.application_id == demande_id)).first()
    montant = float(sc.eligible_amount) if sc else float(app.requested_amount)
    rows = generer(montant, app.term_months)
    db.execute(delete(AmortizationLine).where(AmortizationLine.application_id == demande_id))
    for r in rows:
        db.add(
            AmortizationLine(
                application_id=demande_id,
                installment_no=r["numero"],
                installment_amount=r["echeance"],
                principal=r["capital"],
                interest_amount=r["interet"],
                remaining_principal=r["restant"],
            )
        )
    db.commit()
    return {"montant": montant, "duree_mois": app.term_months, "lignes": rows}


@router.get("/files/chef", tags=["workflow"], response_model=PageDemandes)
def file_chef(
    user: ReviewerUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if user.role not in ("chef_agence", "cic"):
        raise HTTPException(403, "File chef reservee")
    return list_demandes(user, statut="soumis_chef", page=page, page_size=page_size, db=db)


@router.get("/files/cic", tags=["workflow"], response_model=PageDemandes)
def file_cic(
    _user: CicUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_demandes(_user, statut="soumis_cic", page=page, page_size=page_size, db=db)


@router.get("/vision/portefeuille", tags=["vision"], response_model=VisionPortefeuilleOut)
def vision_m6(_user: ReviewerUser, db: Session = Depends(get_db)):
    pars = db.scalars(select(ParIndicator)).all()
    return {
        "module": "M6 maquette",
        "par": [{"agence_id": p.agency_id, "par30": float(p.par30_pct), "par90": float(p.par90_pct)} for p in pars],
        "alertes": [
            {"signal": "Absence aux visites", "membre_id": 3},
            {"signal": "Baisse de stock saisonniere", "membre_id": 6},
        ],
    }


@router.get("/vision/recouvrement", tags=["vision"], response_model=VisionRecouvrementOut)
def vision_m7(_user: ReviewerUser, db: Session = Depends(get_db)):
    rows = db.scalars(select(RecoveryCase)).all()
    return {
        "module": "M7 maquette",
        "dossiers": [
            {"membre_id": r.member_id, "niveau": r.level, "action": r.action, "responsable": r.owner_name}
            for r in rows
        ],
    }
