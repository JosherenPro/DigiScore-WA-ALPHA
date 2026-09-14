from digiscore.financials import compute_all
from digiscore.limits import compute_plafond, is_thin_file
from digiscore.messages import render
from digiscore.policy import (
    EXCEPTIONAL_AMOUNT_THRESHOLD,
    FISCAL_DOCUMENT_AMOUNT_THRESHOLD,
    RCSD_KNOCKOUT_THRESHOLD,
    SCORE_ANALYSIS_MAX,
    SCORE_REJECTION_MAX,
    select_knockout_message,
)
from digiscore.scorecard import compute_score
from digiscore.types import DossierInput, ScoreResult


def _zone(score: float) -> str:
    if score <= SCORE_REJECTION_MAX:
        return "rejet"
    if score <= SCORE_ANALYSIS_MAX:
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
        d.demande.montant >= FISCAL_DOCUMENT_AMOUNT_THRESHOLD
        and d.demande.situation_fiscale == "non_fourni"
    ):
        knockouts.append({"code": "BIC_OU_FISCAL_MANQUANT", "detail": "Fiscalite / BIC non conforme"})
    if (
        d.demande.montant >= d.demande.seuil_caution
        and d.demande.nb_cautions_eligibles < d.demande.nb_cautions_min
    ):
        knockouts.append({"code": "CAUTION_REQUISE", "detail": "Cautionnaire eligible manquant"})

    fin = compute_all(d.analyse, d.demande)
    if fin["rcsd"] < RCSD_KNOCKOUT_THRESHOLD:
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

    code = select_knockout_message(knockouts)
    if code is None:
        if thin and d.demande.montant > eligible_amt:
            code = "HISTORIQUE_INSUFFISANT"
        elif d.demande.exceptionnel or d.demande.montant >= EXCEPTIONAL_AMOUNT_THRESHOLD:
            code = "VOIE_EXCEPTIONNELLE"
        elif zone == "rejet":
            code = "REJET_SCORE"
        elif d.demande.montant > eligible_amt:
            code = "MONTANT_PLAFONNE"
        elif suggestion and suggestion > d.demande.montant:
            code = "UPSELL_POSSIBLE"
        else:
            code = "MONTANT_OK"

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

    eligible = (
        code in ("MONTANT_OK", "UPSELL_POSSIBLE", "VOIE_EXCEPTIONNELLE", "MONTANT_PLAFONNE")
        and not knockouts
        and eligible_amt > 0
    )

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
