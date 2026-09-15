import { useCallback, useEffect, useState } from "react";

/** Charge une ressource unique (GET, Promise.all…) avec un état
 * data/loading/error homogène. Évite de réécrire le même trio
 * useState + useEffect + try/catch dans chaque page.
 *
 * `deps` déclenche un rechargement (ex. l'id de la route change) ;
 * `reload()` relance le même appel après une mutation (soumettre,
 * décider…) sans dupliquer la logique de chargement.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const reload = useCallback(() => {
    setLoading(true);
    setError("");
    fetcher()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, error, loading, reload, setData, setError };
}
