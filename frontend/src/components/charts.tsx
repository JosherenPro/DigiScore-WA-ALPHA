import { useState } from "react";
import { money, type Critere } from "../api/client";

/* Composants graphiques du dashboard résultat/ML.
 * Palette : réutilise les tokens de marque (--green/--danger/--warning) —
 * jamais une palette différente pour les graphiques, sinon le produit se
 * désharmonise. Un seul hue par série (single-series = pas de légende),
 * rouge/vert réservés à la polarité (positif/négatif, sous/au-dessus du seuil). */

/** Repères d'axe arrondis à des valeurs lisibles (0 / 1 000 / 2 000…). */
function niceTicks(min: number, max: number, count = 4): number[] {
  if (!isFinite(min) || !isFinite(max) || min === max) return [Math.round(min)];
  const span = max - min;
  const rawStep = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const norm = rawStep / mag;
  const step = (norm > 5 ? 10 : norm > 2 ? 5 : norm > 1 ? 2 : 1) * mag;
  const start = Math.ceil(min / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= max + 1e-9; v += step) ticks.push(Math.round(v));
  return ticks.length ? ticks : [Math.round(min)];
}

/** FCFA compact pour les axes (1,2M / 850k) — la valeur pleine reste dans le tooltip. */
function compactFcfa(n: number): string {
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(abs % 1_000_000 === 0 ? 0 : 1)}M`;
  if (abs >= 1_000) return `${sign}${Math.round(abs / 1000)}k`;
  return `${sign}${Math.round(abs)}`;
}

export const CRITERE_LABELS: Record<string, string> = {
  financier: "Analyse financière",
  capacite: "Capacité de remboursement",
  historique: "Historique de remboursement",
  activite: "Risque d'activité",
  garanties: "Garanties",
  documents: "Qualité documentaire",
};

// Vecteur scorecard-v3 (scoring/digiscore/adaptive/scorecard_ml.py::FEATURE_NAMES_V3) —
// libellés humains pour les facteurs ML, sinon le code brut reste affiché tel quel.
export const FEATURE_LABELS: Record<string, string> = {
  note_financier: "Analyse financière",
  note_capacite: "Capacité de remboursement",
  note_historique: "Historique de remboursement",
  note_activite: "Risque d'activité",
  note_garanties: "Garanties",
  note_documents: "Qualité documentaire",
  anciennete_mois: "Ancienneté (mois)",
  rcsd: "RCSD",
  epargne_regularite: "Régularité de l'épargne",
  incidents_graves: "Incidents graves",
  montant_sur_plafond: "Montant / plafond produit",
  has_external: "Comptes externes déclarés",
  ext_epargne_log: "Épargne externe",
  bic_incidents: "Incidents BIC",
  past_impayes: "Impayés passés",
  max_jours_retard: "Retard maximum constaté",
  preuves_score: "Niveau de preuve",
  dependance_debouche: "Dépendance à un débouché",
  concurrence: "Concurrence",
  signaux_patrimoine: "Signaux patrimoine",
};

// ---------- Jauge de score (arc semi-circulaire) ----------

function polar(cx: number, cy: number, r: number, t: number) {
  const a = Math.PI - Math.PI * t;
  return { x: cx + r * Math.cos(a), y: cy - r * Math.sin(a) };
}

function arcPath(cx: number, cy: number, r: number, t0: number, t1: number) {
  const p0 = polar(cx, cy, r, t0);
  const p1 = polar(cx, cy, r, t1);
  const large = t1 - t0 > 0.5 ? 1 : 0;
  return `M${p0.x},${p0.y} A${r},${r} 0 ${large} 1 ${p1.x},${p1.y}`;
}

export function ScoreGauge({ score, zone }: { score: number; zone?: string | null }) {
  const cx = 110;
  const cy = 100;
  const r = 84;
  const bounds = [0, 0.4, 0.7, 1];
  const colors = ["var(--zone-low)", "var(--zone-mid)", "var(--zone-high)"];
  const eps = 0.012;
  const t = Math.max(0, Math.min(1, score / 100));
  const marker = polar(cx, cy, r, t);
  return (
    <svg viewBox="0 0 220 120" className="gauge-svg" role="img" aria-label={`Score ${Math.round(score)} sur 100`}>
      {[0, 1, 2].map((i) => (
        <path
          key={i}
          d={arcPath(cx, cy, r, bounds[i] + (i > 0 ? eps : 0), bounds[i + 1] - (i < 2 ? eps : 0))}
          className="gauge-arc"
          stroke={colors[i]}
        />
      ))}
      {bounds.map((b, i) => {
        const p = polar(cx, cy, r + 14, b);
        return (
          <text key={i} x={p.x} y={p.y + 3} textAnchor="middle" className="chart-tick">{Math.round(b * 100)}</text>
        );
      })}
      <circle cx={marker.x} cy={marker.y} r={7} className="gauge-marker" />
      <text x={cx} y={cy - 4} textAnchor="middle" className="gauge-value">{Math.round(score)}</text>
      <text x={cx} y={cy + 16} textAnchor="middle" className="gauge-sub">/100{zone ? ` · ${zone}` : ""}</text>
    </svg>
  );
}

// ---------- Barres de critères (une couleur, magnitude) ----------

export function CriteriaBars({ criteres }: { criteres: Critere[] }) {
  return (
    <div className="crit-bars">
      {criteres.map((c, i) => {
        const note = Math.max(0, Math.min(100, Number(c.note ?? 0)));
        const code = String(c.code || "");
        const poids = c.poids != null ? Math.round(Number(c.poids) * 100) : null;
        const contribution = c.contribution != null ? Math.round(Number(c.contribution)) : null;
        return (
          <div className="crit-row" key={code || i}>
            <span className="crit-label">{CRITERE_LABELS[code] || code}</span>
            <div className="crit-track">
              <div className="crit-fill" style={{ width: `${note}%` }} />
            </div>
            <span className="crit-value">{Math.round(note)}</span>
            <span className="crit-weight muted">
              {poids != null ? `${poids}%` : ""}
              {poids != null && contribution != null ? " · " : ""}
              {contribution != null ? `+${contribution}` : ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ---------- Barre de comparaison (montant vs plafond, règles vs ML) ----------

export function CompareBar({
  label,
  value,
  max,
  valueLabel,
  tone = "ok",
}: {
  label: string;
  value: number;
  max: number;
  valueLabel: string;
  tone?: "ok" | "warn";
}) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div className="cmpbar">
      <div className="cmpbar-labels">
        <span className="muted">{label}</span>
        <strong>{valueLabel}</strong>
      </div>
      <div className="cmpbar-track">
        <div className={`cmpbar-fill ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ---------- Barres divergentes (facteurs ML : contribution +/-) ----------

export function FactorsChart({ factors }: { factors: { feature: string; contribution: number }[] }) {
  const maxAbs = Math.max(0.01, ...factors.map((f) => Math.abs(f.contribution)));
  return (
    <div className="factors-chart">
      {factors.map((f, i) => {
        const positive = f.contribution >= 0;
        const pct = (Math.abs(f.contribution) / maxAbs) * 50;
        return (
          <div className="factor-row" key={i}>
            <span className="factor-label">{FEATURE_LABELS[f.feature] || f.feature}</span>
            <div className="factor-track">
              <div className="factor-zero" />
              <div
                className={`factor-bar ${positive ? "pos" : "neg"}`}
                style={{ width: `${pct}%`, [positive ? "left" : "right"]: "50%" }}
              />
            </div>
            <span className={`factor-value ${positive ? "pos" : "neg"}`}>
              {positive ? "+" : ""}
              {f.contribution.toFixed(2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ---------- Trajectoire de résilience (p10/p50/p90) — s'adapte à l'horizon réel ----------

export function TrajectoryChart({
  p10,
  p50,
  p90,
  moisCritique,
}: {
  p10: number[];
  p50: number[];
  p90: number[];
  moisCritique: number | null;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const n = p50.length;
  const W = 640;
  const H = 260;
  const PAD_L = 68;
  const PAD_R = 16;
  const PAD_T = 20;
  const PAD_B = 30;

  if (n === 0) return null;

  const allVals = [...p10, ...p50, ...p90, 0];
  const yMin = Math.min(...allVals);
  const yMax = Math.max(...allVals);
  const pad = (yMax - yMin) * 0.12 || Math.max(1, Math.abs(yMax) * 0.12) || 1;
  const y0 = yMin - pad;
  const y1 = yMax + pad;

  const xFor = (i: number) => PAD_L + (n <= 1 ? 0 : (i / (n - 1)) * (W - PAD_L - PAD_R));
  const yFor = (v: number) => PAD_T + (1 - (v - y0) / (y1 - y0)) * (H - PAD_T - PAD_B);
  const zeroY = yFor(0);
  const plotBottom = H - PAD_B;
  const plotTop = PAD_T;

  // Courbes lissées (Catmull-Rom -> Bézier) : plus agréables à l'œil que des
  // segments droits, sans changer les valeurs sous-jacentes.
  function smooth(values: number[]): string {
    const pts = values.map((v, i) => ({ x: xFor(i), y: yFor(v) }));
    if (pts.length < 3) return pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
    let d = `M${pts[0].x},${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i - 1] || pts[i];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[i + 2] || p2;
      const c1x = p1.x + (p2.x - p0.x) / 6;
      const c1y = p1.y + (p2.y - p0.y) / 6;
      const c2x = p2.x - (p3.x - p1.x) / 6;
      const c2y = p2.y - (p3.y - p1.y) / 6;
      d += ` C${c1x},${c1y} ${c2x},${c2y} ${p2.x},${p2.y}`;
    }
    return d;
  }

  const p50Path = smooth(p50);
  const p10Path = smooth(p10);
  const p90Path = smooth(p90);
  const bandPath =
    p90.map((v, i) => `${i === 0 ? "M" : "L"}${xFor(i)},${yFor(v)}`).join(" ") +
    " " +
    p10
      .map((v, i) => ({ v, i }))
      .reverse()
      .map(({ v, i }) => `L${xFor(i)},${yFor(v)}`)
      .join(" ") +
    " Z";

  const yTicks = niceTicks(y0, y1, 4);
  const clipId = `traj-clip-${n}`;

  function onMove(e: React.PointerEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const idx = Math.round(((px - PAD_L) / (W - PAD_L - PAD_R)) * (n - 1));
    setHover(Math.max(0, Math.min(n - 1, idx)));
  }

  const lastX = xFor(n - 1);
  const lastY = yFor(p50[n - 1]);

  return (
    <div className="traj-wrap">
      <div className="chart-legend">
        <span><i className="legend-swatch line" /> Médiane (p50)</span>
        <span><i className="legend-swatch band" /> Plage 10–90 %</span>
        {moisCritique && <span><i className="legend-swatch dot" /> Creux critique</span>}
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="traj-svg"
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
        role="img"
        aria-label={`Trajectoire de trésorerie simulée sur ${n} mois`}
      >
        <defs>
          <clipPath id={`${clipId}-pos`}>
            <rect x={0} y={0} width={W} height={Math.max(0, zeroY)} />
          </clipPath>
          <clipPath id={`${clipId}-neg`}>
            <rect x={0} y={zeroY} width={W} height={Math.max(0, H - zeroY)} />
          </clipPath>
        </defs>

        {/* zone de danger (sous zéro) */}
        {zeroY < plotBottom && (
          <rect x={PAD_L} y={zeroY} width={W - PAD_L - PAD_R} height={plotBottom - zeroY} className="traj-danger-zone" />
        )}

        {/* grille horizontale + repères de montant */}
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={PAD_L} x2={W - PAD_R} y1={yFor(t)} y2={yFor(t)} className="chart-axis" />
            <text x={PAD_L - 8} y={yFor(t) + 3} textAnchor="end" className="chart-tick">{compactFcfa(t)}</text>
          </g>
        ))}
        <line x1={PAD_L} x2={W - PAD_R} y1={zeroY} y2={zeroY} className="chart-axis strong" />

        {/* bande d'incertitude + bornes p10/p90 */}
        <path d={bandPath} className="traj-band" />
        <path d={p90Path} className="traj-bound" />
        <path d={p10Path} className="traj-bound" />

        {/* p50 : vert au-dessus de zéro, rouge en dessous */}
        <path d={p50Path} className="traj-line pos" clipPath={`url(#${clipId}-pos)`} />
        <path d={p50Path} className="traj-line neg" clipPath={`url(#${clipId}-neg)`} />

        {moisCritique && moisCritique >= 1 && moisCritique <= n && (
          <circle cx={xFor(moisCritique - 1)} cy={yFor(p50[moisCritique - 1])} r={6} className="traj-critical" />
        )}

        {/* étiquette de fin (dernière valeur p50) */}
        <circle cx={lastX} cy={lastY} r={4} className={lastY <= zeroY ? "traj-dot pos" : "traj-dot neg"} />
        <text
          x={Math.min(lastX + 6, W - PAD_R)}
          y={lastY}
          textAnchor={lastX + 60 > W - PAD_R ? "end" : "start"}
          dx={lastX + 60 > W - PAD_R ? -8 : 0}
          className="traj-end-label"
        >
          {compactFcfa(p50[n - 1])}
        </text>

        {hover != null && (
          <>
            <line x1={xFor(hover)} x2={xFor(hover)} y1={plotTop} y2={plotBottom} className="traj-crosshair" />
            <circle cx={xFor(hover)} cy={yFor(p90[hover])} r={3} className="traj-dot bound" />
            <circle cx={xFor(hover)} cy={yFor(p10[hover])} r={3} className="traj-dot bound" />
            <circle cx={xFor(hover)} cy={yFor(p50[hover])} r={4} className="traj-dot" />
          </>
        )}
        <text x={PAD_L} y={H - 8} className="chart-tick">mois 1</text>
        <text x={W - PAD_R} y={H - 8} textAnchor="end" className="chart-tick">mois {n}</text>
      </svg>
      {hover != null && (() => {
        const pct = (xFor(hover) / W) * 100;
        const onRight = pct > 55;
        return (
          <div
            className="traj-tooltip"
            style={onRight ? { right: `${100 - pct}%` } : { left: `${pct}%` }}
          >
            <strong>Mois {hover + 1}</strong>
            <div><i className="legend-swatch line" /> p50 · {money(p50[hover])}</div>
            <div className="muted"><i className="legend-swatch bound" /> p10 {money(p10[hover])} · p90 {money(p90[hover])}</div>
          </div>
        );
      })()}
      {!hover && moisCritique && (
        <p className="muted mt-sm">Point rouge : creux critique au mois {moisCritique}.</p>
      )}
    </div>
  );
}

// ---------- Courbe simple (une série, aire dégradée) — tableau de bord agent ----------

export function TrendChart({ points }: { points: { date: string; total: number }[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const n = points.length;
  const W = 640;
  const H = 200;
  const PAD_L = 34;
  const PAD_R = 12;
  const PAD_T = 16;
  const PAD_B = 26;

  if (n === 0) return null;

  const vals = points.map((p) => p.total);
  const yMax = Math.max(...vals, 1);
  const y0 = 0;
  const y1 = yMax * 1.15;

  const xFor = (i: number) => PAD_L + (n <= 1 ? 0 : (i / (n - 1)) * (W - PAD_L - PAD_R));
  const yFor = (v: number) => PAD_T + (1 - (v - y0) / (y1 - y0)) * (H - PAD_T - PAD_B);
  const plotBottom = H - PAD_B;

  function smooth(values: number[]): string {
    const pts = values.map((v, i) => ({ x: xFor(i), y: yFor(v) }));
    if (pts.length < 3) return pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
    let d = `M${pts[0].x},${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i - 1] || pts[i];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[i + 2] || p2;
      const c1x = p1.x + (p2.x - p0.x) / 6;
      const c1y = p1.y + (p2.y - p0.y) / 6;
      const c2x = p2.x - (p3.x - p1.x) / 6;
      const c2y = p2.y - (p3.y - p1.y) / 6;
      d += ` C${c1x},${c1y} ${c2x},${c2y} ${p2.x},${p2.y}`;
    }
    return d;
  }

  const linePath = smooth(vals);
  const areaPath = `${linePath} L${xFor(n - 1)},${plotBottom} L${xFor(0)},${plotBottom} Z`;
  const yTicks = niceTicks(y0, y1, 3);

  function onMove(e: React.PointerEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const idx = Math.round(((px - PAD_L) / (W - PAD_L - PAD_R)) * (n - 1));
    setHover(Math.max(0, Math.min(n - 1, idx)));
  }

  const fmt = (iso: string) => {
    const d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
  };

  return (
    <div className="trend-wrap">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="trend-svg"
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
        role="img"
        aria-label={`Dossiers créés sur les ${n} dernières semaines`}
      >
        <defs>
          <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--green)" stopOpacity="0.28" />
            <stop offset="100%" stopColor="var(--green)" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={PAD_L} x2={W - PAD_R} y1={yFor(t)} y2={yFor(t)} className="chart-axis" />
            <text x={PAD_L - 6} y={yFor(t) + 3} textAnchor="end" className="chart-tick">{Math.round(t)}</text>
          </g>
        ))}
        <path d={areaPath} fill="url(#trend-fill)" stroke="none" />
        <path d={linePath} className="trend-line" />
        {points.map((p, i) => (
          <circle key={p.date} cx={xFor(i)} cy={yFor(p.total)} r={hover === i ? 4.5 : 2.5} className="trend-dot" />
        ))}
        {hover != null && (
          <line x1={xFor(hover)} x2={xFor(hover)} y1={PAD_T} y2={plotBottom} className="traj-crosshair" />
        )}
        <text x={PAD_L} y={H - 6} className="chart-tick">{fmt(points[0].date)}</text>
        <text x={W - PAD_R} y={H - 6} textAnchor="end" className="chart-tick">{fmt(points[n - 1].date)}</text>
      </svg>
      {hover != null && (() => {
        const pct = (xFor(hover) / W) * 100;
        const onRight = pct > 55;
        return (
          <div className="traj-tooltip" style={onRight ? { right: `${100 - pct}%` } : { left: `${pct}%` }}>
            <strong>Semaine du {fmt(points[hover].date)}</strong>
            <div>{points[hover].total} dossier{points[hover].total > 1 ? "s" : ""} créé{points[hover].total > 1 ? "s" : ""}</div>
          </div>
        );
      })()}
    </div>
  );
}
