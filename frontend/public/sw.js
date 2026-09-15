/* Service worker DigiScore-WA — coquille PWA pour le terrain (connexion faible).
 *
 * Stratégie par type de requête, et non une seule pour tout :
 *
 *  - Navigation (HTML) : réseau d'abord, cache en secours. La version
 *    précédente servait `/index.html` depuis le cache en priorité, donc un
 *    agent qui revenait après une mise en production gardait indéfiniment
 *    l'ancienne application — et l'ancien index pointe vers un bundle JS dont
 *    le nom est haché, qui n'existe plus après nettoyage. L'écran restait
 *    blanc sans qu'aucun rechargement n'y change quoi que ce soit.
 *
 *  - Ressources statiques (JS/CSS/images) : cache d'abord. Leur nom porte un
 *    hachage de contenu, une version en cache est donc toujours la bonne.
 *
 *  - API : jamais interceptée. Un score ou un encours mis en cache serait pire
 *    qu'une erreur réseau : l'agent déciderait sur des chiffres périmés sans
 *    le savoir.
 */

const CACHE = "digiscore-shell-v3";
const SHELL = ["/", "/index.html", "/manifest.json", "/logo-alpha.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

/** Chemins qui doivent toujours passer par le réseau, sans cache ni secours. */
function horsCache(pathname) {
  return (
    pathname.startsWith("/api") ||
    pathname.startsWith("/src") ||
    pathname.startsWith("/@") ||
    pathname.startsWith("/node_modules")
  );
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  // Requêtes vers un autre domaine : laissées au navigateur.
  if (url.origin !== self.location.origin) return;
  if (horsCache(url.pathname)) return;

  // Navigation : on tente le réseau, on rafraîchit le cache au passage, et on
  // ne retombe sur la coquille en cache que si le réseau fait défaut.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copie = res.clone();
          caches.open(CACHE).then((c) => c.put("/index.html", copie));
          return res;
        })
        .catch(() => caches.match("/index.html").then((c) => c || caches.match("/"))),
    );
    return;
  }

  // Statique : cache d'abord, et on garnit le cache au premier passage.
  event.respondWith(
    caches.match(req).then(
      (cached) =>
        cached ||
        fetch(req)
          .then((res) => {
            if (res && res.ok && res.type === "basic") {
              const copie = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copie));
            }
            return res;
          })
          .catch(() => cached),
    ),
  );
});
