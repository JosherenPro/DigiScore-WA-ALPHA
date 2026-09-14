import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { getUser, homeFor, setSession } from "../auth";

const ROLES = [
  { login: "agent", title: "Agent de crédit", hint: "Lookup membre, collecte, analyse, soumission" },
  { login: "chef", title: "Chef d’agence", hint: "File à valider, renvoyer ou escalader au CIC" },
  { login: "cic", title: "CIC", hint: "Décision finale : accorder, conditionner, refuser" },
];

export default function Login() {
  const nav = useNavigate();
  const [err, setErr] = useState("");
  const [health, setHealth] = useState("");
  const [picked, setPicked] = useState("agent");
  const [password, setPassword] = useState("demo");
  const [busy, setBusy] = useState(false);
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

  async function enter() {
    setErr("");
    setBusy(true);
    try {
      const out = await api.login(picked, password);
      setSession(out.access_token, out.user);
      nav(homeFor(out.user.role));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "API indisponible");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <div className="login-panel">
        <img className="login-logo" src="/logo-alpha.svg" alt="Équipe Alpha" />
        <h1>DigiScore-WA</h1>
        <p>Copilote d’éligibilité et de plafond pour les SFD CIF. Score /100 — un humain décide toujours.</p>
        <div className="roles">
          {ROLES.map((r) => (
            <button key={r.login} type="button" className={picked === r.login ? "picked" : ""} onClick={() => setPicked(r.login)}>
              <strong>{r.title}</strong>
              <span>{r.hint}</span>
            </button>
          ))}
        </div>
        <label className="password-row">
          Mot de passe démo
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        </label>
        <div className="actions">
          <button className="btn teal" type="button" disabled={busy} onClick={enter}>
            Entrer
          </button>
        </div>
        {health && <p className="error">{health}</p>}
        {err && <p className="error">{err}</p>}
      </div>
    </div>
  );
}
