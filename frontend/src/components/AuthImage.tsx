import { useEffect, useState } from "react";
import { fetchUploadUrl } from "../api/client";

/** Affiche une pièce stockée côté serveur. La route /uploads exige un
 * Bearer token — impossible en <img src> direct — donc on la récupère en
 * blob authentifié puis on affiche l'URL locale obtenue. */
export default function AuthImage({ path, className, alt }: { path: string; className?: string; alt: string }) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchUploadUrl(path).then((u) => {
      if (cancelled) {
        URL.revokeObjectURL(u);
        return;
      }
      objectUrl = u;
      setUrl(u);
    }).catch(() => undefined);
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  if (!url) return <div className={className} aria-hidden="true" />;
  return <img className={className} src={url} alt={alt} />;
}
