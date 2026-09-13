from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.schemas.dossier import HealthOut

OPENAPI_TAGS = [
    {"name": "sante", "description": "Liveness de l'API."},
    {"name": "auth", "description": "Login démo (agent / chef / cic). Pas de JWT."},
    {"name": "membres", "description": "Lookup paginé (code, nom, account_no) et fiche historique."},
    {"name": "demandes", "description": "Création, collecte A–E, pièces, liste paginée."},
    {"name": "workflow", "description": "Analyse, soumission, décision, mémo, files chef/CIC."},
    {"name": "vision", "description": "Maquettes M6 portefeuille et M7 recouvrement."},
]

app = FastAPI(
    title="DigiScore-WA API",
    description="Copilote d'éligibilité et de plafond — institutions CIF. Contrat Front ↔ Back (clés JSON FR).",
    version="0.2.0",
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["sante"], response_model=HealthOut)
def health():
    return {"status": "ok", "service": "digiscore-wa"}
