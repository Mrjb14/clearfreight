# ClearFreight — Vision & Questions clés

---

## 1. La roadmap — Priorités & délais (1 personne)

Le piège classique d'un MVP : vouloir construire le vrai produit avant d'avoir validé que quelqu'un veut payer.

**Ce qui compte pour le prototype démo :**
- Quelqu'un upload un PDF → voit un rapport qui semble vrai → laisse son email → c'est gagné
- La vraie analyse peut être simulée tant que le rapport est crédible

**Ce qu'on peut couper sans remords :**
- Vraie base de données (inutile pour la démo, fichiers JSON suffisent)
- Auth / comptes utilisateurs (formulaire email avant rapport = suffisant)
- Parsing LLM réel (Phase 4, optionnel pour la démo)
- Scraping terminaux portuaires (trop fragile, données fixes pour la démo)

**Délai réaliste seul :** 3 semaines pour un prototype déployé et montrable à des prospects.

---

## 2. Architecture technique — Comment ça s'articule

### Version démo (maintenant)
```
Browser
  └── POST /analyze (PDF) ──► FastAPI
                                └── Scénario simulé (JSON)
                                      └── Rapport affiché
```
Pas de DB, pas de LLM, stateless. Le backend choisit un scénario crédible selon le fichier uploadé.

### Version réelle (dans 2-3 mois)
```
Browser
  └── POST /analyze (PDF) ──► FastAPI
                                ├── OCR (Textract)
                                ├── Claude API → JSON structuré
                                │     └── Validation regex (montants)
                                ├── Règles métier (BAF formula, FBX index)
                                └── PostgreSQL (historique, règles)
```

**Pourquoi Claude API pour le parsing ?**
Un LLM comprend "Bunker Surcharge", "BAF", "Fuel Adj." comme étant la même chose sans dictionnaire exhaustif. Il extrait la structure même sur des PDFs mal scannés. La validation regex ensuite protège contre les hallucinations sur les montants.

**Pourquoi Redis ?**
Le scraping des terminaux portuaires est asynchrone (peut prendre 30s). Redis sert de queue pour que l'API réponde immédiatement et notifie quand le résultat D&D est prêt.

---

## 3. Par où commencer — Ordre concret

1. `backend/main.py` — FastAPI avec `POST /analyze` qui retourne du JSON simulé ✅ (fait)
2. `backend/scenarios.py` — 4 scénarios réalistes avec vraies routes/transporteurs ✅ (fait)
3. Connecter `clearfreight.html` au backend via `fetch()` ✅ (fait)
4. Tester localement : `uvicorn main:app --reload` + ouvrir le HTML
5. Générer un vrai PDF rapport (WeasyPrint)
6. Capturer l'email avant d'afficher le rapport
7. Déployer sur Railway (backend) + Vercel (frontend)

---

## 4. Le métier maritime — Ce qu'on détecte vraiment

### Pourquoi les factures sont si opaques

Un conteneur 40' Shanghai → Le Havre génère une facture avec ~10-15 lignes. Seule la première (Ocean Freight) est négociée contractuellement. Tout le reste — les surcharges — est ajouté unilatéralement par le transporteur avec des formules que personne ne publie clairement.

### Les 3 types d'anomalies

**Surcharges mal calculées (40% des erreurs)**
- BAF (carburant) : calculé selon le prix du fuel lourd (VLSFO) à une date de référence. La formule varie par transporteur et n'est pas publiée. On la rétro-ingénierie sur les factures accumulées. Une déviation de +40% est clairement contestable.
- PSS (Peak Season Surcharge) : officiellement applicable Oct–Jan. Facturer en mars est une erreur pure.
- ETS/Green Levy : basé sur le prix des EUA (European Allowances) à la date du B/L. Vérifiable sur les marchés carbone.

**Taux contractuels non respectés (25% des erreurs)**
- L'Ocean Freight facturé ne correspond pas au contrat signé. Requiert d'avoir le contrat en référence.

**Surestaries contestables (cas le plus lucratif)**
- Le transporteur facture N jours à 150$/j. Mais il a compté les week-ends, jours fériés, et les jours où le terminal était fermé (grèves, congestion).
- La règle FMC (Federal Maritime Commission) oblige les armateurs à déduire ces jours depuis 2024.
- Un conteneur avec 8 jours facturés peut n'en avoir que 4-5 réellement contestables.

### Ce qu'on NE peut PAS détecter sans données contextuelles
- Erreurs de poids/dimensions (nécessite le packing list)
- Doublons de facturation (nécessite l'historique des paiements)

---

## 5. Business — Qui cibler et comment monétiser

### Cible prioritaire : les transitaires (freight forwarders), pas les PME

Contre-intuitif mais logique :
- Un transitaire gère **100-500 factures/mois** pour ses clients. ClearFreight lui fait gagner du temps ET de la crédibilité face à ses clients.
- Une PME importatrice reçoit 5-10 factures/mois. Le ROI est réel mais le volume est faible.
- Les transitaires sont le chemin le plus court vers du volume.

### Modèle économique

| Offre | Prix | Pour qui |
|---|---|---|
| Analyse unitaire | 9-15€/facture | PME occasionnelles |
| Abonnement Pro | 149-299€/mois | PME 20-50 factures/mois |
| API / Volume | Sur devis | Transitaires, TMS |

### Première validation à faire

Avant de coder quoi que ce soit de plus : envoyer 10 emails à des responsables logistique/import avec un lien vers la démo. Si 3 personnes laissent leur email après l'analyse → le problème est réel et le format démo fonctionne.

### Concurrence
- Les TMS (Cargowise, Shiptify) ont cette fonctionnalité mais pour les grandes entreprises (>50M€ de CA).
- Aucun outil accessible sous 300€/mois pour les PME et petits transitaires. C'est le créneau.
