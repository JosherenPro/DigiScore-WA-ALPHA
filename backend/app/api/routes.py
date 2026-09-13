from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.tables import (
    Account,
    Activity,
    AmortizationLine,
    AppUser,
    ApplicationGuarantee,
    AuditLog,
    CreditApplication,
    CreditProduct,
    Decision,
    FinancialRatio,
    IncomeExpense,
    Incident,
    Member,
    ParIndicator,
    PastCredit,
    RecoveryCase,
    SavingsSnapshot,
    ScoreResult,
    SupportingDocument,
)
from app.schemas.dossier import (
    AmortissementOut,
    CollecteIn,
    DecisionIn,
    DecisionResultOut,
    DemandeCreate,
    DemandeCreateOut,
    DemandeDetail,
    LoginIn,
    LoginOut,
    MembreDetail,
    MemoOut,
    OkOut,
    PageDemandes,
    PageMembres,
    PieceIn,
    ProduitOut,
    SoumettreOut,
    VisionPortefeuilleOut,
    VisionRecouvrementOut,
)
from app.services.amortissement import generer
from app.services.dossier_builder import build_dossier
from app.services.workflow import can_chef_close, next_queue
from digiscore.pipeline import run
from digiscore.types import ScoreResult as ScoringOut

router = APIRouter()


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


@router.post("/auth/login", tags=["auth"], response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalars(select(AppUser).where(AppUser.login == body.login)).first()
    if not u:
        raise HTTPException(404, "Utilisateur inconnu (agent / chef / cic)")
    return {"id": u.id, "login": u.login, "nom": u.full_name, "role": u.role}


@router.get("/produits", tags=["demandes"], response_model=list[ProduitOut])
def list_produits(db: Session = Depends(get_db)):
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
def get_membre(membre_id: int, db: Session = Depends(get_db)):
    m = db.get(Member, membre_id)
    if not m:
        raise HTTPException(404, "Membre introuvable")
    account = db.scalars(select(Account).where(Account.member_id == m.id)).first()
    snap = None
    if account:
        snap = db.scalars(select(SavingsSnapshot).where(SavingsSnapshot.account_id == account.id)).first()
    credits = db.scalars(select(PastCredit).where(PastCredit.member_id == m.id)).all()
    incidents = db.scalars(select(Incident).where(Incident.member_id == m.id)).all()
    today = date(2026, 9, 13)
    anciennete = (today.year - m.joined_on.year) * 12 + today.month - m.joined_on.month
    thin = anciennete < 3 or (not credits and (not snap or float(snap.avg_balance_6m or 0) < 80000))
    return {
        "id": m.id,
        "code_externe": m.external_code,
        "nom": m.last_name,
        "prenom": m.first_name,
        "telephone": m.phone,
        "statut": m.status,
        "zone": m.area,
        "date_adhesion": str(m.joined_on),
        "anciennete_mois": anciennete,
        "thin_file": thin,
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
    }


@router.get("/membres/{membre_id}/historique", tags=["membres"], response_model=MembreDetail)
def historique(membre_id: int, db: Session = Depends(get_db)):
    return get_membre(membre_id, db)


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
def create_demande(body: DemandeCreate, db: Session = Depends(get_db)):
    m = db.get(Member, body.membre_id)
    if not m:
        raise HTTPException(400, "NON_MEMBRE")
    account = db.scalars(select(Account).where(Account.member_id == m.id)).first()
    if m.status != "actif" or not account or account.status != "actif":
        raise HTTPException(400, "COMPTE_INACTIF")
    app = CreditApplication(
        member_id=body.membre_id,
        product_id=body.produit_id,
        agent_id=body.agent_id,
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
    db.add(AuditLog(application_id=app.id, user_id=body.agent_id, action="create", detail=body.objet))
    db.commit()
    return {"id": app.id, "statut": app.status}


@router.post("/demandes/{demande_id}/collecte", tags=["demandes"], response_model=OkOut)
def save_collecte(demande_id: int, body: CollecteIn, db: Session = Depends(get_db)):
    if not db.get(CreditApplication, demande_id):
        raise HTTPException(404, "Demande introuvable")
    _persist_collecte(db, demande_id, body)
    db.commit()
    return {"ok": True}


@router.post("/demandes/{demande_id}/pieces", tags=["demandes"], response_model=OkOut)
def add_piece(demande_id: int, body: PieceIn, db: Session = Depends(get_db)):
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
    statut: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    page, page_size, offset = _clamp_page(page, page_size)
    stmt = select(CreditApplication)
    if statut:
        stmt = stmt.where(CreditApplication.status == statut)
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
def get_demande(demande_id: int, db: Session = Depends(get_db)):
    d = db.get(CreditApplication, demande_id)
    if not d:
        raise HTTPException(404, "Demande introuvable")
    sc = db.scalars(select(ScoreResult).where(ScoreResult.application_id == d.id)).first()
    ratios = db.scalars(select(FinancialRatio).where(FinancialRatio.application_id == d.id)).first()
    decs = db.scalars(select(Decision).where(Decision.application_id == d.id)).all()
    pieces = db.scalars(
        select(SupportingDocument).where(SupportingDocument.application_id == d.id)
    ).all()
    score_val = float(sc.score_total) if sc else None
    return {
        "id": d.id,
        "membre_id": d.member_id,
        "objet": d.purpose,
        "montant_demande": float(d.requested_amount),
        "duree_mois": d.term_months,
        "statut": d.status,
        "situation_fiscale": d.tax_status,
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
    }


@router.post("/demandes/{demande_id}/analyser", tags=["workflow"], response_model=ScoringOut)
def analyser(demande_id: int, db: Session = Depends(get_db)):
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
    )
    if existing:
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
        for k, v in rdata.items():
            setattr(ratio, k, v)
    else:
        db.add(FinancialRatio(**rdata))

    app = db.get(CreditApplication, demande_id)
    app.status = "analyse"
    db.add(AuditLog(application_id=demande_id, action="analyser", detail=result.message_code))
    db.commit()
    return result.model_dump()


@router.post("/demandes/{demande_id}/soumettre", tags=["workflow"], response_model=SoumettreOut)
def soumettre(demande_id: int, utilisateur_id: int = 1, db: Session = Depends(get_db)):
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
            user_id=utilisateur_id,
        )
    )
    db.add(
        AuditLog(
            application_id=demande_id,
            user_id=utilisateur_id,
            action="soumettre",
            detail=app.status,
        )
    )
    db.commit()
    return {"statut": app.status, "file": cible}


@router.post("/demandes/{demande_id}/decision", tags=["workflow"], response_model=DecisionResultOut)
def decision(demande_id: int, body: DecisionIn, db: Session = Depends(get_db)):
    app = db.get(CreditApplication, demande_id)
    if not app:
        raise HTTPException(404)
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
            user_id=body.utilisateur_id,
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
            user_id=body.utilisateur_id,
            action=body.avis,
            detail=body.motif,
        )
    )
    db.commit()
    return {"statut": app.status, "override": override}


@router.get("/demandes/{demande_id}/memo", tags=["workflow"], response_model=MemoOut)
def memo(demande_id: int, db: Session = Depends(get_db)):
    d = get_demande(demande_id, db)
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
def amortissement(demande_id: int, db: Session = Depends(get_db)):
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
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_demandes(statut="soumis_chef", page=page, page_size=page_size, db=db)


@router.get("/files/cic", tags=["workflow"], response_model=PageDemandes)
def file_cic(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_demandes(statut="soumis_cic", page=page, page_size=page_size, db=db)


@router.get("/vision/portefeuille", tags=["vision"], response_model=VisionPortefeuilleOut)
def vision_m6(db: Session = Depends(get_db)):
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
def vision_m7(db: Session = Depends(get_db)):
    rows = db.scalars(select(RecoveryCase)).all()
    return {
        "module": "M7 maquette",
        "dossiers": [
            {"membre_id": r.member_id, "niveau": r.level, "action": r.action, "responsable": r.owner_name}
            for r in rows
        ],
    }
