# ClearFreight — Roadmap

> Format : ✅ Fait · 🔄 En cours · ⬜ À faire · ❌ Abandonné
> Mise à jour à chaque feature ajoutée.

---

## Phase 1 — Backend minimal
_Objectif : une API qui reçoit un PDF et retourne une analyse simulée crédible._

- ✅ Créer `backend/main.py` — FastAPI avec endpoint `POST /analyze`
- ✅ Créer `backend/scenarios.py` — 4 scénarios réalistes (normale, BAF élevé, surestaries, multi-anomalies)
- ✅ Configurer CORS pour le frontend
- ✅ Créer `backend/requirements.txt`
- ✅ Générer un vrai rapport PDF téléchargeable (`POST /report`)
- ✅ Template email de contestation généré automatiquement (`POST /contestation`)

---

## Phase 2 — Frontend connecté
_Objectif : remplacer les données hardcodées par un vrai appel API._

- ✅ Connecter `clearfreight.html` au backend via `fetch()`
- ✅ `showResult(data)` accepte les données dynamiques de l'API
- ✅ Gestion d'erreur si le backend est indisponible
- ✅ Formulaire email avant d'afficher le rapport (capture de leads → `leads.json`)
- ✅ Bouton "Télécharger le rapport PDF" fonctionnel

---

## Phase 3 — Scénarios de démo réalistes
_Objectif : que chaque upload semble unique et crédible._

- ✅ 4 scénarios prédéfinis avec routes et transporteurs réels (Maersk, CMA CGM, MSC, Hapag-Lloyd)
- ✅ Sélection du scénario selon le nom du fichier (ex: "MSC" dans le nom → scénario MSC)
- ✅ Variation légère des montants (±5%) pour éviter l'effet "toujours pareil"

---

## Phase 4 — Parsing basique réel (Claude API)
_Objectif : extraire transporteur + montant total + route du PDF uploadé et les injecter dans le rapport simulé._

- ✅ Intégrer Claude API dans le backend (graceful fallback si clé absente)
- ✅ Extraire le transporteur du PDF via Claude (Haiku)
- ✅ Injecter le transporteur extrait pour sélectionner le bon scénario
- ✅ Fallback sur sélection par nom de fichier si extraction échoue
- ⬜ Extraire montant total + route + date B/L et les injecter dans le rapport
- ⬜ Validation regex sur les montants extraits

---

## Phase 5 — Déploiement
_Objectif : un lien partageable pour les prospects._

- ⬜ Déployer backend sur Railway ou Fly.io
- ⬜ Déployer frontend sur Vercel ou Netlify (ou servir statiquement depuis le backend)
- ⬜ Domaine (clearfreight.fr ou clearfreight.io)
- ⬜ Variables d'environnement pour les clés API

---

## Backlog (post-démo)

- ⬜ Authentification (magic link email)
- ⬜ Base de données PostgreSQL (historique des analyses par utilisateur)
- ⬜ Migrer le frontend vers React
- ⬜ Parsing BAF réel (rétro-ingénierie des formules transporteur)
- ⬜ Vérification ETS via prix EUA à la date du B/L
- ⬜ Couche D&D : scraping portails terminaux (Le Havre, Marseille)
- ⬜ API / intégration pour transitaires et TMS
- ⬜ Tableau de bord multi-factures
