# -*- coding: utf-8 -*-
MESSAGES = {
    "NON_MEMBRE": "Ouverture de compte prealable obligatoire.",
    "COMPTE_INACTIF": "Compte gele ou inactif : aucune demande possible.",
    "HISTORIQUE_INSUFFISANT": "Historique institutionnel insuffisant pour ce montant.",
    "EPARGNE_SOUS_SEUIL": "Volume d'epargne / activite inferieur au seuil requis.",
    "INCIDENTS_RECENTS": "Comportement de remboursement non conforme.",
    "MONTANT_PLAFONNE": "Montant demande superieur au plafond : {x} FCFA proposes.",
    "MONTANT_OK": "Demande dans le plafond.",
    "UPSELL_POSSIBLE": "Capacite estimee jusqu'a {y} FCFA (suggestion, non automatique).",
    "VOIE_EXCEPTIONNELLE": "Montant exceptionnel : passage CIC + garanties renforcees.",
    "REJET_SCORE": "Rejet recommande -- {motif}.",
    "CAUTION_REQUISE": "Montant au-dela du seuil : cautionnaire eligible obligatoire.",
    "BIC_OU_FISCAL_MANQUANT": "Pieces BIC ou fiscales exigibles manquantes ou non conformes.",
    "PREUVES_EXTERNES_MANQUANTES": "Credits ailleurs declares sans pieces justificatives : refus.",
    "KNOCKOUT_RCSD": "RCSD inferieur a 1 : capacite de remboursement insuffisante.",
    "KNOCKOUT_ESG": "Activite exclue (ESG) : rejet immediat.",
}


def render(code: str, **kwargs) -> str:
    tpl = MESSAGES.get(code, code)
    return tpl.format(**kwargs)
