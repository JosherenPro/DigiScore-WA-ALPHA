import type { ReactNode } from "react";

/** Bandeau de feedback unique (erreur / succès / info) — remplace les
 * <p className="error"> et bandeaux ad hoc dispersés dans chaque page. */
export default function Alert({
  kind = "info",
  children,
}: {
  kind?: "error" | "success" | "info";
  children: ReactNode;
}) {
  return (
    <div className={`alert ${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}
