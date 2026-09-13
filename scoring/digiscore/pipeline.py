from digiscore.financials import compute_all
from digiscore.limits import compute_plafond, is_thin_file
from digiscore.messages import render
from digiscore.scorecard import compute_score
from digiscore.types import DossierInput, ScoreResult


def _zone(score: float) -> str:
    if score <= 40:
        return "rejet"
    if score <= 70:
        return "analyse"
    return "approbation"


def run(dossier: dict | DossierInput) -> ScoreResult:
    d = dossier if isinstance(dossier, DossierInput) else DossierInput.model_validate(dossier)
    knockouts: list[dict] = []

    if d.membre.statut != "actif":
        knockouts.append({"code": "COMPTE_INACTIF", "detail": "Membre ou statut non actif"})
    if d.compte.statut != "actif":
        knockouts.append({"code": "COMPTE_INACTIF", "detail": "Compte inactif / gele"})
    if d.demande.exclusion_esg:
        knockouts.append({"code": "KNOCKOUT_ESG", "detail": "Exclusion ESG"})
    if d.historique.credits_ailleurs and not d.historique.preuves_externes_ok:
        knockouts.append(
            {"code": "PREUVES_EXTERNES_MANQUANTES", "detail": "Pieces externes exigibles absentes"}
        )
    if d.demande.situation_fiscale in ("non_conforme",) or (
        d.demande.montant >= 500000 and d.demande.situation_fiscale == "non_fourni"
    ):
        knockouts.append({"code": "BIC_OU_FISCAL_MANQUANT", "detail": "Fiscalite / BIC non conforme"})
    if (
        d.demande.montant >= d.demande.seuil_caution
        and d.demande.nb_cautions_eligibles < d.demande.nb_cautions_min
    ):
        knockouts.append({"code": "CAUTION_REQUISE", "detail": "Cautionnaire eligible manquant"})

    fin = compute_all(d.analyse, d.demande)
    if fin["rcsd"] < 1.0:
        knockouts.append({"code": "KNOCKOUT_RCSD", "detail": f"RCSD={fin['rcsd']}"})

    graves = [i for i in d.historique.incidents if i.gravite == "grave"]
    if graves:
        knockouts.append({"code": "INCIDENTS_RECENTS", "detail": f"{len(graves)} incident(s) grave(s)"})

    thin = is_thin_file(d)
    score, criteres = compute_score(d, fin)
    eligible_amt, suggestion = compute_plafond(d, fin, score, thin)

    zone = _zone(score)
    if knockouts:
        zone = "rejet"
        # Un knockout est un refus : aucun montant ne doit être présenté comme éligible.
        eligible_amt = 0
        suggestion = None

    code = "MONTANT_OK"
    if any(k["code"] == "COMPTE_INACTIF" for k in knockouts):
        code = "COMPTE_INACTIF"
    elif any(k["code"] == "PREUVES_EXTERNES_MANQUANTES" for k in knockouts):
        code = "PREUVES_EXTERNES_MANQUANTES"
    elif any(k["code"] == "CAUTION_REQUISE" for k in knockouts):
        code = "CAUTION_REQUISE"
    elif any(k["code"] == "KNOCKOUT_RCSD" for k in knockouts):
        code = "KNOCKOUT_RCSD"
    elif any(k["code"] == "KNOCKOUT_ESG" for k in knockouts):
        code = "KNOCKOUT_ESG"
    elif any(k["code"] == "BIC_OU_FISCAL_MANQUANT" for k in knockouts):
        code = "BIC_OU_FISCAL_MANQUANT"
    elif any(k["code"] == "INCIDENTS_RECENTS" for k in knockouts):
        code = "INCIDENTS_RECENTS"
    elif thin and d.demande.montant > eligible_amt:
        code = "HISTORIQUE_INSUFFISANT"
    elif d.demande.exceptionnel or d.demande.montant >= 8_000_000:
        code = "VOIE_EXCEPTIONNELLE"
    elif zone == "rejet":
        code = "REJET_SCORE"
    elif d.demande.montant > eligible_amt:
        code = "MONTANT_PLAFONNE"
    elif suggestion and suggestion > d.demande.montant:
        code = "UPSELL_POSSIBLE"

    motif = knockouts[0]["detail"] if knockouts else zone
    humain = render(
        code,
        x=f"{int(eligible_amt):,}".replace(",", " "),
        y=f"{int(suggestion or 0):,}".replace(",", " "),
        motif=motif,
    )

    expl = [
        f"Score {score}/100 - zone {zone}",
        f"RCSD {fin['rcsd']} (norme >= 1,50 ; knockout < 1)",
        f"Plafond estime {int(eligible_amt):,} FCFA".replace(",", " "),
    ]
    if thin:
        expl.append("Profil thin-file : historique institutionnel leger")
    if fin["mois_critique"]:
        expl.append(f"Creux de tresorerie au mois {fin['mois_critique']}")

    eligible = code in ("MONTANT_OK", "UPSELL_POSSIBLE", "VOIE_EXCEPTIONNELLE", "MONTANT_PLAFONNE") and not knockouts
    if code == "MONTANT_PLAFONNE" and not knockouts:
        eligible = True

    return ScoreResult(
        eligible=eligible,
        thin_file=thin,
        score_global=score,
        criteres=criteres,
        knockouts=knockouts,
        montant_demande=d.demande.montant,
        montant_eligible=eligible_amt,
        montant_max_suggestion=suggestion,
        message_code=code,
        message_humain=humain,
        explication=expl,
        zone=zone,
        financials=fin,
    )
