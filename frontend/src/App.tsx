import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { clearSession, getUser, homeFor } from "./auth";
import Login from "./pages/Login";
import AgentHome from "./pages/AgentHome";
import Membre from "./pages/Membre";
import DemandeWizard from "./pages/DemandeWizard";
import Resultat from "./pages/Resultat";
import Memo from "./pages/Memo";
import FileChef from "./pages/FileChef";
import FileCic from "./pages/FileCic";
import Portefeuille from "./pages/Portefeuille";
import Recouvrement from "./pages/Recouvrement";

function RoleGate({ allow, children }: { allow: string[]; children: ReactNode }) {
  const user = getUser();
  if (!user) return <Navigate to="/" replace />;
  if (!allow.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return <>{children}</>;
}

function Shell({ children }: { children: ReactNode }) {
  const user = getUser();
  const nav = useNavigate();
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  if (!user) return <Navigate to="/" replace />;
  const role = user.role;
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to={homeFor(role)}>
          <img src="/logo-alpha.svg" alt="Équipe Alpha" />
          DigiScore-WA
        </NavLink>
        <nav className="nav">
          {role === "agent" && (
            <>
              <NavLink to="/agent">Membres</NavLink>
              <NavLink to="/demandes">Dossiers</NavLink>
            </>
          )}
          {role === "chef_agence" && (
            <>
              <NavLink to="/chef">File chef</NavLink>
              <NavLink to="/m6">Portefeuille</NavLink>
              <NavLink to="/m7">Recouvrement</NavLink>
            </>
          )}
          {role === "cic" && (
            <>
              <NavLink to="/cic">File CIC</NavLink>
              <NavLink to="/m6">Portefeuille</NavLink>
              <NavLink to="/m7">Recouvrement</NavLink>
            </>
          )}
        </nav>
        <div className="user-chip">
          {user.nom} · {role.replace("_", " ")}
          <button
            className="btn ghost sm"
            style={{ color: "#fff", borderColor: "rgba(255,255,255,.45)" }}
            type="button"
            onClick={() => {
              clearSession();
              nav("/");
            }}
          >
            Sortir
          </button>
        </div>
      </header>
      {!online && <div className="offline">Mode dégradé — connexion faible. Le shell PWA reste disponible.</div>}
      <div className="copilote">Copilote d’éligibilité — le système ne décide jamais seul. Un humain tranche.</div>
      {children}
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/agent" element={<Shell><AgentHome /></Shell>} />
      <Route path="/membres/:id" element={<Shell><Membre /></Shell>} />
      <Route
        path="/membres/:id/demande"
        element={
          <Shell>
            <RoleGate allow={["agent"]}>
              <DemandeWizard />
            </RoleGate>
          </Shell>
        }
      />
      <Route path="/demandes" element={<Shell><AgentHome dossiers /></Shell>} />
      <Route path="/demandes/:id" element={<Shell><Resultat /></Shell>} />
      <Route path="/demandes/:id/memo" element={<Shell><Memo /></Shell>} />
      <Route
        path="/chef"
        element={
          <Shell>
            <RoleGate allow={["chef_agence", "cic"]}>
              <FileChef />
            </RoleGate>
          </Shell>
        }
      />
      <Route
        path="/cic"
        element={
          <Shell>
            <RoleGate allow={["cic"]}>
              <FileCic />
            </RoleGate>
          </Shell>
        }
      />
      <Route
        path="/m6"
        element={
          <Shell>
            <RoleGate allow={["chef_agence", "cic"]}>
              <Portefeuille />
            </RoleGate>
          </Shell>
        }
      />
      <Route
        path="/m7"
        element={
          <Shell>
            <RoleGate allow={["chef_agence", "cic"]}>
              <Recouvrement />
            </RoleGate>
          </Shell>
        }
      />
    </Routes>
  );
}
