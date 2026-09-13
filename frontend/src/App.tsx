import type { ReactNode } from "react";
import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { getUser, setUser } from "./auth";
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

function Shell({ children }: { children: ReactNode }) {
  const user = getUser();
  const nav = useNavigate();
  if (!user) return <Navigate to="/" replace />;
  const online = typeof navigator === "undefined" ? true : navigator.onLine;
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">DigiScore-WA</div>
        <nav className="nav">
          {user.role === "agent" && (
            <>
              <NavLink to="/agent">Membres</NavLink>
              <NavLink to="/demandes">Dossiers</NavLink>
            </>
          )}
          {(user.role === "chef_agence" || user.role === "agent") && <NavLink to="/chef">File chef</NavLink>}
          {(user.role === "cic" || user.role === "chef_agence") && <NavLink to="/cic">File CIC</NavLink>}
          <NavLink to="/m6">Portefeuille</NavLink>
          <NavLink to="/m7">Recouvrement</NavLink>
        </nav>
        <div className="user-chip">
          {user.nom} · {user.role}{" "}
          <button
            className="btn ghost"
            style={{ padding: "0.2rem 0.5rem", marginLeft: 8, color: "#fff", borderColor: "#fff" }}
            onClick={() => {
              setUser(null);
              nav("/");
            }}
          >
            Sortir
          </button>
        </div>
      </header>
      {!online && <div className="offline">Mode dégradé — connexion faible. Le shell PWA reste disponible.</div>}
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
      <Route path="/membres/:id/demande" element={<Shell><DemandeWizard /></Shell>} />
      <Route path="/demandes" element={<Shell><AgentHome dossiers /></Shell>} />
      <Route path="/demandes/:id" element={<Shell><Resultat /></Shell>} />
      <Route path="/demandes/:id/memo" element={<Shell><Memo /></Shell>} />
      <Route path="/chef" element={<Shell><FileChef /></Shell>} />
      <Route path="/cic" element={<Shell><FileCic /></Shell>} />
      <Route path="/m6" element={<Shell><Portefeuille /></Shell>} />
      <Route path="/m7" element={<Shell><Recouvrement /></Shell>} />
    </Routes>
  );
}
