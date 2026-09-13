import { Navigate, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { getUser, setUser } from "../auth";
import { useState } from "react";

const ROLES = [
  { login: "agent", title: "Agent de crédit", hint: "Lookup membre, analyse, soumission" },
  { login: "chef", title: "Chef d’agence", hint: "File à valider, renvoyer, escalader" },
  { login: "cic", title: "CIC", hint: "Décision finale accorder / conditionner / refuser" },
];

export default function Login() {
  const nav = useNavigate();
  const [err, setErr] = useState("");
  const existing = getUser();
  if (existing) {
    const dest = existing.role === "cic" ? "/cic" : existing.role === "chef_agence" ? "/chef" : "/agent";
    return <Navigate to={dest} replace />;
  }

  async function enter(login: string) {
    try {
      const u = await api.login(login);
      setUser(u);
      nav(u.role === "cic" ? "/cic" : u.role === "chef_agence" ? "/chef" : "/agent");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "API indisponible");
    }
  }

  return (
    <div className="login">
      <div className="login-panel">
        <h1>DigiScore-WA</h1>
        <p>Copilote d’éligibilité et de plafond. Le système ne décide jamais seul.</p>
        <div className="roles">
          {ROLES.map((r) => (
            <button key={r.login} onClick={() => enter(r.login)}>
              <strong>{r.title}</strong>
              <span>{r.hint}</span>
            </button>
          ))}
        </div>
        {err && <p className="error">{err}</p>}
      </div>
    </div>
  );
}
