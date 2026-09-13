"""Politique déterministe du moteur de scoring MVP.

Les valeurs sont centralisées pour rendre les règles auditables et modifiables
sans disperser les seuils dans le pipeline.
"""

CREDIT_SERVICE_RATE = 0.018
RCSD_KNOCKOUT_THRESHOLD = 1.0
RCSD_COMFORT_THRESHOLD = 1.5
FISCAL_DOCUMENT_AMOUNT_THRESHOLD = 500_000
EXCEPTIONAL_AMOUNT_THRESHOLD = 8_000_000

MESSAGE_PRIORITY = (
    "COMPTE_INACTIF",
    "PREUVES_EXTERNES_MANQUANTES",
    "CAUTION_REQUISE",
    "KNOCKOUT_RCSD",
    "KNOCKOUT_ESG",
    "BIC_OU_FISCAL_MANQUANT",
    "INCIDENTS_RECENTS",
)


def select_knockout_message(knockouts: list[dict]) -> str | None:
    """Retourne le message du premier knockout selon la politique métier."""
    present = {knockout["code"] for knockout in knockouts}
    return next((code for code in MESSAGE_PRIORITY if code in present), None)
