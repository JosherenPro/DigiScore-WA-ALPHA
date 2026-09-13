"""Couche adapter — stub Postgres aujourd'hui, API SI en pilote."""

from abc import ABC, abstractmethod


class AdapterHistorique(ABC):
    @abstractmethod
    def lookup_code(self, code_externe: str):
        raise NotImplementedError


class AdapterStub(AdapterHistorique):
    """Lit le Postgres local (données synthétiques)."""

    def lookup_code(self, code_externe: str):
        return code_externe
