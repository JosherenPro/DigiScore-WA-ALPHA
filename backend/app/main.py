from dotenv import load_dotenv

load_dotenv()

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.db import ping_db
from app.schemas.dossier import HealthOut

OPENAPI_TAGS = [
    {"name": "sante", "description": "Liveness + capabilities ML (stub)."},
    {"name": "referentiel", "description": "Agences, autres IF (pas mobile money), enums."},
    {"name": "auth", "description": "Login demo agent / chef / cic + JWT."},
    {"name": "membres", "description": "Lookup paginé (code, nom, account_no) et fiche historique."},
    {"name": "demandes", "description": "Création, collecte A–E, pièces, liste paginée."},
    {"name": "workflow", "description": "Analyse, soumission, décision, mémo, files chef/CIC."},
    {"name": "vision", "description": "Maquettes M6 portefeuille et M7 recouvrement."},
]

_cors = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

app = FastAPI(
    title="DigiScore-WA API",
    description="Copilote d'éligibilité et de plafond — institutions CIF. Contrat Front ↔ Back (clés JSON FR).",
    version="0.3.0",
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        raise exc
    return JSONResponse(status_code=500, content={"detail": "Erreur interne"})


@app.get("/health", tags=["sante"], response_model=HealthOut)
def health():
    ok = ping_db()
    return {
        "status": "ok" if ok else "degraded",
        "service": "digiscore-wa",
        "database": "ok" if ok else "down",
    }
