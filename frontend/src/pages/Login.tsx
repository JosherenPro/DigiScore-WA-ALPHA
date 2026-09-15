import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { getUser, homeFor, setSession } from "../auth";
import Alert from "../components/Alert";

// Démo/pilote : les 3 comptes partagent le même mot de passe (voir README).
// Choisir un profil suffit à entrer — pas de formulaire à remplir. Design
// repris de la maquette Figma fournie par l'utilisateur (fond vert texturé,
// carte ivoire, bandeau kente, badges terracotta) — la mécanique reste la
// même, un clic, aucun code PIN réel à saisir.
const DEMO_PASSWORD = "demo";

const ROLES = [
  {
    login: "agent",
    title: "Agent de crédit",
    hint: "Lookup membre, collecte, analyse, soumission",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21c0-4 3.6-7 8-7s8 3 8 7" />
      </svg>
    ),
  },
  {
    login: "chef",
    title: "Chef d’agence",
    hint: "File à valider, renvoyer ou escalader au CIC",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="7" width="18" height="13" rx="2" />
        <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      </svg>
    ),
  },
  {
    login: "cic",
    title: "CIC",
    hint: "Décision finale : accorder, conditionner, refuser",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
        <path d="m9 12 2 2 4-4" />
      </svg>
    ),
  },
];

export default function Login() {
  const nav = useNavigate();
  const [err, setErr] = useState("");
  const [health, setHealth] = useState("");
  const [entering, setEntering] = useState<string | null>(null);
  const existing = getUser();

  useEffect(() => {
    api
      .health()
      .then((h) => {
        if (h.database !== "ok") setHealth("API up mais base inaccessible.");
      })
      .catch(() => setHealth("Lance uvicorn :8000 — l’API n’est pas joignable."));
  }, []);

  if (existing) return <Navigate to={homeFor(existing.role)} replace />;

  async function enter(login: string) {
    setErr("");
    setEntering(login);
    try {
      const out = await api.login(login, DEMO_PASSWORD);
      setSession(out.access_token, out.user);
      nav(homeFor(out.user.role));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "API indisponible");
      setEntering(null);
    }
  }

  return (
    <div className="login">
      <div className="login-panel">
        <div className="login-card">
          <div className="login-brand-row">
            <div className="login-logo">
              <img src="/logo-alpha.svg" alt="" />
            </div>
            <div>
              <h1>DigiScore-WA</h1>
              <span className="login-eyebrow">Copilote d’éligibilité · SFD</span>
            </div>
          </div>

          <p className="login-lede">Choisis ton profil pour entrer — démo, pas de mot de passe à saisir.</p>

          <div className="roles">
            {ROLES.map((r) => (
              <button key={r.login} type="button" disabled={entering !== null} onClick={() => enter(r.login)}>
                <span className="role-icon" aria-hidden="true">{r.icon}</span>
                <span>
                  <strong>{r.title}</strong>
                  <span>{r.hint}</span>
                </span>
                {entering === r.login ? (
                  <span className="spinner" aria-hidden="true" />
                ) : (
                  <span className="role-arrow" aria-hidden="true">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 6l6 6-6 6" />
                    </svg>
                  </span>
                )}
              </button>
            ))}
          </div>

          {health && <Alert kind="error">{health}</Alert>}
          {err && <Alert kind="error">{err}</Alert>}

          <p className="login-note">Démo — aucun mot de passe requis. Chaque interface a sa propre session.</p>
        </div>
      </div>
    </div>
  );
}
