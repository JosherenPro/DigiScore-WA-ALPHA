import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { api, type Capabilities } from "./api/client";
import { clearSession, getUser, homeFor } from "./auth";
import Login from "./pages/Login";
import AgentHome from "./pages/AgentHome";
import Dashboard from "./pages/Dashboard";
import Membre from "./pages/Membre";
import DemandeWizard from "./pages/DemandeWizard";
import Resultat from "./pages/Resultat";
import Memo from "./pages/Memo";
import FileChef from "./pages/FileChef";
import FileCic from "./pages/FileCic";
import Portefeuille from "./pages/Portefeuille";
import Recouvrement from "./pages/Recouvrement";
import Suivi from "./pages/Suivi";

function RoleGate({ allow, children }: { allow: string[]; children: ReactNode }) {
  const user = getUser();
  if (!user) return <Navigate to="/" replace />;
  if (!allow.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return <>{children}</>;
}

// Icônes de nav — un seul jeu, réutilisé identique entre la sidebar (grand
// écran) et la barre du bas (mobile), pour ne jamais désynchroniser les deux.
const ICONS: Record<string, ReactNode> = {
  dashboard: (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </svg>
  ),
  dossiers: (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
    </svg>
  ),
  suivi: (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="4" y="3" width="16" height="18" rx="2" />
      <path d="M9 3v2h6V3" />
      <path d="m9 13 2 2 4-4" />
    </svg>
  ),
  portefeuille: (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="6" width="18" height="13" rx="2" />
      <path d="M3 10h18" />
      <path d="M16 14h2" />
    </svg>
  ),
  recouvrement: (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M15 7h6v6" />
    </svg>
  ),
  file: (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22 12h-6l-2 3h-4l-2-3H2" />
      <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
    </svg>
  ),
};

type NavItem = { to: string; label: string; icon: string };

const NAV_BY_ROLE: Record<string, NavItem[]> = {
  agent: [
    { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
    { to: "/demandes", label: "Dossiers", icon: "dossiers" },
    { to: "/suivi", label: "Suivi", icon: "suivi" },
    { to: "/m6", label: "Portefeuille", icon: "portefeuille" },
    { to: "/m7", label: "Recouvrement", icon: "recouvrement" },
  ],
  chef_agence: [
    { to: "/chef", label: "File chef", icon: "file" },
    { to: "/m6", label: "Portefeuille", icon: "portefeuille" },
    { to: "/m7", label: "Recouvrement", icon: "recouvrement" },
  ],
  cic: [
    { to: "/cic", label: "File CIC", icon: "file" },
    { to: "/m6", label: "Portefeuille", icon: "portefeuille" },
    { to: "/m7", label: "Recouvrement", icon: "recouvrement" },
  ],
};

function NavLinks({ role }: { role: string }) {
  const items = NAV_BY_ROLE[role] || [];
  return (
    <>
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} className="nav-link">
          <span className="nav-icon" aria-hidden="true">{ICONS[item.icon]}</span>
          {item.label}
        </NavLink>
      ))}
    </>
  );
}

// Barre de navigation du bas (mobile) — mêmes destinations que la sidebar,
// jamais un sous-ensemble : sur petit écran la nav principale vit ici, plus
// dans un tiroir à ouvrir/fermer.
function BottomNav({ role }: { role: string }) {
  const items = NAV_BY_ROLE[role] || [];
  return (
    <nav className="bottom-nav">
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} className="bottom-nav-link">
          <span className="nav-icon" aria-hidden="true">{ICONS[item.icon]}</span>
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

function Shell({ children }: { children: ReactNode }) {
  const user = getUser();
  const nav = useNavigate();
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  const [caps, setCaps] = useState<Capabilities | null>(null);
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
  useEffect(() => {
    api.capabilities().then(setCaps).catch(() => undefined);
  }, []);
  if (!user) return <Navigate to="/" replace />;
  const mlOn = !!(caps && (caps.ml_scorecard || caps.anomalies || caps.simulation || caps.early_warning));
  const role = user.role;

  function logout() {
    clearSession();
    nav("/");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <NavLink className="brand" to={homeFor(role)}>
            <img src="/logo-alpha.svg" alt="Équipe Alpha" />
            DigiScore-WA
          </NavLink>
          {mlOn && (
            <span className="ml-tag sidebar-ml-tag">
              <span className="ml-dot" aria-hidden="true" /> ML actif
            </span>
          )}
        </div>
        <nav className="sidebar-nav">
          <NavLinks role={role} />
        </nav>
        <div className="sidebar-user">
          <span>{user.nom} · {role.replace("_", " ")}</span>
          <button className="btn ghost sm" type="button" onClick={logout}>
            Sortir
          </button>
        </div>
      </aside>
      <div className="main">
        <header className="mobile-topbar">
          <NavLink className="brand" to={homeFor(role)}>
            <img src="/logo-alpha.svg" alt="Équipe Alpha" />
            DigiScore-WA
          </NavLink>
          <button className="btn ghost sm" type="button" aria-label="Se déconnecter" onClick={logout}>
            Sortir
          </button>
        </header>
        {!online && <div className="offline">Mode dégradé — connexion faible. Le shell PWA reste disponible.</div>}
        <div className="copilote">Copilote d’éligibilité — le système ne décide jamais seul. Un humain tranche.</div>
        <div className="page-body">{children}</div>
        <BottomNav role={role} />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/agent" element={<Shell><AgentHome /></Shell>} />
      <Route
        path="/dashboard"
        element={
          <Shell>
            <RoleGate allow={["agent"]}>
              <Dashboard />
            </RoleGate>
          </Shell>
        }
      />
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
            <RoleGate allow={["agent", "chef_agence", "cic"]}>
              <Portefeuille />
            </RoleGate>
          </Shell>
        }
      />
      <Route
        path="/m7"
        element={
          <Shell>
            <RoleGate allow={["agent", "chef_agence", "cic"]}>
              <Recouvrement />
            </RoleGate>
          </Shell>
        }
      />
      <Route
        path="/suivi"
        element={
          <Shell>
            <RoleGate allow={["agent", "chef_agence", "cic"]}>
              <Suivi />
            </RoleGate>
          </Shell>
        }
      />
    </Routes>
  );
}
