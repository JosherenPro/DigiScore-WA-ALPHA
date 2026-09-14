"""Auth démo 3 rôles : login + mot de passe + JWT HS256. Pas de HMAC SI."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.tables import AppUser

SECRET_KEY = os.getenv("SECRET_KEY", "digiscore-demo-change-me-32b-min-key!!")
JWT_ALG = "HS256"
JWT_HOURS = int(os.getenv("JWT_HOURS", "12"))
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo")

_bearer = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user: AppUser) -> str:
    payload = {
        "sub": str(user.id),
        "login": user.login,
        "role": user.role,
        "agency_id": user.agency_id,
        "exp": datetime.now(UTC) + timedelta(hours=JWT_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALG)


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Session = Depends(get_db),
) -> AppUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(401, "Token Bearer requis")
    try:
        data = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(401, "Token invalide ou expire") from None
    user = db.get(AppUser, int(data["sub"]))
    if not user:
        raise HTTPException(401, "Utilisateur inconnu")
    return user


def require_roles(*roles: str):
    def _dep(user: Annotated[AppUser, Depends(get_current_user)]) -> AppUser:
        if user.role not in roles:
            raise HTTPException(403, f"Role {user.role} non autorise")
        return user

    return _dep


AgentUser = Annotated[AppUser, Depends(require_roles("agent"))]
ChefUser = Annotated[AppUser, Depends(require_roles("chef_agence"))]
CicUser = Annotated[AppUser, Depends(require_roles("cic"))]
StaffUser = Annotated[AppUser, Depends(require_roles("agent", "chef_agence", "cic"))]
ReviewerUser = Annotated[AppUser, Depends(require_roles("chef_agence", "cic"))]
