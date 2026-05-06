# Refonte des pages Tiers et Engagements

Date : 2026-05-06
Auteur : Tristan + Claude (brainstorming)

## Contexte

Quatre utilisateurs (profil pilotage trésorerie, pas saisie comptable) se partagent Horizon. Un test utilisateur élargi a montré que les pages **Tiers** et **Engagements** ne sont comprises par personne : objectif flou, vocabulaire opaque, impact des actions invisible.

L'audit du code (services, API, modèles) a confirmé deux constats forts :

1. **Sur Tiers** : valider un tiers (`pending` → `active`) n'a aucun effet fonctionnel. Le backend traite `pending` comme `active` partout (catégorisation, matching, dashboard, analyses, forecast). La todo-list "À valider" est cosmétique. Seul `ignored` a un effet réel — et contient un bug : un tiers ignoré est recréé en `pending` au prochain import récurrent.
2. **Sur Engagements** : la donnée est utile (alimente le forecast et les indicateurs BFR/DSO/DPO) mais un engagement créé puis jamais matché double-compte indéfiniment dans le prévisionnel à côté de la transaction réelle. Aucun signal ne prévient l'utilisateur.

## Objectifs

- Rendre l'utilité de chaque page immédiatement compréhensible pour un nouvel utilisateur
- Supprimer les actions sans effet (théâtre cognitif)
- Exposer la valeur déjà calculée mais invisible (volumes, retards, totaux)
- Corriger les bugs structurels (recréation de doublons, engagements fantômes)
- Documenter de manière contraignante l'impact de chaque action

## Décisions cadrées (résumé des Q&R brainstorming)

| # | Sujet | Décision |
|---|-------|----------|
| 1 | Profil cible | 4 users en pilotage / visu, pas de saisie comptable |
| 2 | Approche Tiers | Hybride : suppression du concept "À valider", liste enrichie consultable, fusion de doublons |
| 3 | Approche Engagements | Refonte forte : split encaissements/décaissements, agrégats, alertes retard, gestion fantômes |
| 4 | Engagements fantômes | Bandeau d'alerte, action en masse "Clôturer". Pas d'auto-cancel |
| 5 | Onglet Ignorés | Supprimer l'onglet, remplacer par filtre "Inclure les ignorés" |
| 6 | Fusion de tiers | Préview obligatoire avant fusion irréversible |
| 7 | Nav Engagements | Un item, deux onglets (Encaissements / Décaissements) + onglet "Tout" |
| 8 | Libellés nav | "Clients & fournisseurs" et "À encaisser / À payer" |

## Page 1 — Clients & fournisseurs (ex-Tiers)

### Suppression

- Onglet **"À valider"** : retiré complètement de l'UI
- Bouton **"Valider"** : retiré (aucun effet fonctionnel à conserver)
- Onglet **"Ignorés"** : retiré, remplacé par une case à cocher "Inclure les tiers ignorés" dans la liste principale

### Liste enrichie

Colonnes :

- Nom (renommable inline, voir édition)
- Statut (`Actif` / `Ignoré`) — pastille discrète
- Nombre de transactions liées (calculé)
- Volume cumulé toutes périodes (somme valeur absolue, calculé)
- Date de la dernière opération (calculée)
- Nombre d'engagements en cours (`pending`, calculé)

Tri par défaut : volume cumulé décroissant. Recherche full-text sur le nom. Pagination 50 lignes.

### Actions par ligne

- **Renommer** : édition inline du nom (modifie `Counterparty.name`, n'altère pas `normalized_name` qui sert au matching à l'import)
- **Fusionner avec…** : ouvre un dialog de sélection d'un tiers cible, puis preview obligatoire (cf. ci-dessous)
- **Ignorer / Réactiver** : bascule du statut, avec tooltip explicite (cf. doc)
- **Voir les transactions** : redirige vers la page Transactions filtrée sur ce tiers (réutilisation de l'existant, pas de fiche dédiée)

### Création manuelle

Bouton "Nouveau tiers" : crée un `Counterparty` `active` avec un nom libre. Utile pour préparer un tiers avant le premier import (rare mais demandé).

### Fusion (workflow détaillé)

1. L'utilisateur choisit un tiers source et un tiers cible (le cible reste, le source disparaît)
2. Preview affichée :
   - "X transactions seront réattachées vers '<cible>'"
   - "Y engagements seront réattachés"
   - "Z règles de catégorisation seront mises à jour"
   - Liste des Y engagements et des Z règles affichée pour vérification
3. Bouton "Confirmer la fusion" — irréversible
4. Backend : transaction SQL atomique, UPDATE des FK, DELETE du tiers source
5. Toast de confirmation, retour sur la liste

### Fix du bug "Ignoré recréé en `pending`"

Cause : `services/imports.py:134-148` — le matching fuzzy ignore les entrées `IGNORED` et crée un nouveau `pending`.

Fix : élargir le matching fuzzy pour inclure les entrées `IGNORED`. Si un match est trouvé sur un tiers ignoré, **réutiliser** ce tiers ignoré (la transaction est rattachée mais le tiers reste ignoré). Pas de nouveau `pending` créé.

### Bandeau d'introduction permanent

Texte (non fermable, en haut de page) :

> **Clients & fournisseurs.** Cette page liste tous les tiers détectés à partir de tes imports bancaires. Tu peux les renommer, fusionner les doublons, et ignorer ceux qui polluent les sélecteurs. Pour voir les opérations d'un tiers, clique sur son nom.

### Empty states

- Liste vide : "Aucun tiers correspondant. Les tiers sont créés automatiquement à chaque import bancaire. Tu peux aussi en créer un manuellement."
- Recherche sans résultat : "Aucun résultat pour '<query>'."

## Page 2 — À encaisser / À payer (ex-Engagements)

### Structure

Une page, trois onglets :

1. **À encaisser** (direction = `in`) — créances, factures clients à venir
2. **À payer** (direction = `out`) — dettes, factures fournisseurs à payer
3. **Tout** (vue mixte) — utile pour totaux globaux

### KPI en tête (calculés sur l'onglet actif)

Bandeau de 3 cartes :

- **Total sous 30 jours** (somme `amount` des `pending` avec `expected_date` entre aujourd'hui et J+30)
- **Total en retard** (somme `amount` des `pending` avec `expected_date < aujourd'hui`)
- **Nombre de retards** (compte simple)

Sur l'onglet "Tout" : 6 cartes (3 par direction).

### Liste

Colonnes :

- Statut (avec badge **"En retard"** rouge si `pending` ET `expected_date < aujourd'hui`)
- Tiers (cliquable → ouvre la fiche transactions du tiers)
- Catégorie
- Date prévue (`expected_date`)
- Montant
- Référence
- Transaction matchée (cliquable si présente, ouvre la transaction dans la page Transactions)
- Actions (Modifier / Matcher manuellement / Clôturer)

Tri par défaut : retards en haut (badges rouges visibles immédiatement), puis par date prévue croissante.

Filtres : période, statut (`pending`, `paid`, `cancelled`), catégorie, tiers, plage de montant.

### Bandeau d'alerte "fantômes"

Si **N engagements** ont `expected_date` dépassée de plus de **7 jours** sans match (`pending` + `matched_transaction_id IS NULL` + `expected_date < today - 7`), afficher un bandeau jaune en haut de la liste :

> **N engagements probablement fantômes.** Ces lignes en retard de plus de 7 jours sans transaction associée gonflent peut-être ton prévisionnel à tort.
> **[Voir la liste]** **[Tout clôturer]**

- "Voir la liste" : applique un filtre rapide pour ne montrer que ces lignes
- "Tout clôturer" : action en masse, passe leur statut à `cancelled` après confirmation

Le seuil de 7 jours est en dur dans cette V1. Configurable plus tard si besoin.

### Score de matching exposé

Dans le dialog de matching manuel (`CommitmentMatchDialog.tsx`), pour chaque suggestion :

- Afficher le score numérique (0-100)
- Afficher la décomposition courte : "Montant ±X €, date ±Y jours, tiers identique +20"
- Mettre en évidence (bordure verte) les suggestions de score ≥ 80 (seuil de match auto à l'import)

L'utilisateur comprend pourquoi telle suggestion est en tête.

### Bandeau d'introduction permanent

> **À encaisser / À payer.** Saisis ici les factures que tu attends ou que tu dois payer. Elles alimentent ton prévisionnel de trésorerie et tes indicateurs BFR/DSO/DPO. Quand une transaction réelle correspond à un engagement, il est automatiquement marqué comme payé. Vérifie régulièrement les retards pour repérer les relances à faire ou les fantômes à clôturer.

### Empty states

- Liste vide : "Aucune échéance enregistrée. Crée une échéance pour qu'elle apparaisse dans ton prévisionnel."
- Filtre vide : "Aucune échéance ne correspond aux filtres sélectionnés."

### Hors scope V1 (réservé V2)

- Import CSV
- Upload PDF (le champ `pdf_attachment_id` existe en BDD mais pas d'UI dédiée)
- Engagements récurrents (génération automatique mensuelle)
- Notifications email/push pour les retards

## Documentation contraignante

### Règle d'équipe

Ajouter dans `CLAUDE.md` (ou un nouveau `AGENTS.md` à la racine du repo) :

> Toute nouvelle action UI à effet (création, modification, suppression d'état, déclenchement d'un workflow) doit livrer dans la même PR :
> 1. Un bandeau d'introduction sur la page concernée si le concept est nouveau
> 2. Un tooltip "?" sur l'action elle-même expliquant en une phrase ce qu'elle déclenche
> 3. Une section dans `frontend/src/content/documentation.ts` au format imposé (cf. ci-dessous)
> Une PR sans ces trois éléments est incomplète.

### Format imposé pour `documentation.ts`

Pour chaque feature ou action à effet, structurer en quatre paragraphes courts :

1. **À quoi ça sert** (intention métier)
2. **Ce que ça change quand tu cliques** (effets concrets backend + UI)
3. **Ce que ça ne change pas** (pour casser les fausses intuitions)
4. **Quand l'utiliser** (cas d'usage typiques)

À appliquer en V1 sur les sections "Clients & fournisseurs" et "À encaisser / À payer", puis rétroactivement sur les autres pages au fil de l'eau.

### Tooltips "?" en V1

À ajouter sur les actions suivantes :

- **Ignorer un tiers** : "Le tiers reste en base mais disparaît des sélecteurs et des prédictions de récurrence du prévisionnel. Les transactions liées restent visibles. Pour un tiers récurrent, mieux vaut le renommer."
- **Fusionner deux tiers** : "Réattache toutes les transactions, engagements et règles vers le tiers cible. Le tiers source est supprimé. Action irréversible."
- **Matcher un engagement** : "Lie cet engagement à la transaction réelle correspondante. L'engagement passe en 'Payé' et sort du prévisionnel."
- **Clôturer un engagement** : "Marque l'engagement comme annulé. Il sort du prévisionnel et des indicateurs DSO/DPO. Utilise pour les fantômes ou les factures finalement non émises."

## Migration / impact data

Aucune migration Alembic destructive nécessaire. Les changements sont :

- **UI** : retraits d'onglets, ajout de colonnes calculées, bandeaux, KPI
- **API** : ajout d'endpoints d'agrégat (totaux 30j, count retards, count fantômes), endpoint de fusion (POST `/counterparties/{id}/merge` avec body `{target_id}`), endpoint preview de fusion (GET `/counterparties/{id}/merge-preview?target_id=Y`)
- **Backend** : fix dans `services/imports.py` pour réutiliser les tiers `IGNORED` au lieu de créer un doublon `PENDING`. Pas de migration de données nécessaire mais les tests doivent couvrir ce cas.

Le statut `pending` reste dans la base pour les tiers existants — on n'écrit pas de migration pour les bascule en `active`. C'est sans effet car le backend les traite déjà comme tels. Côté UI, on cesse simplement de les distinguer.

## Tests

- Test unitaire fusion : 47 transactions + 3 engagements + 2 règles réattachées atomiquement, source supprimé
- Test unitaire fix import : un import récurrent sur un tiers `IGNORED` ne crée pas de doublon `PENDING`
- Test API agrégats : totaux 30j, count retards, count fantômes corrects
- Test E2E : workflow complet création engagement → import transaction matchante → engagement passe `paid`
- Test E2E : workflow fusion deux tiers depuis l'UI

## Hors scope (rappel)

- Import CSV / PDF d'engagements
- Engagements récurrents auto-générés
- Notifications retard
- Page admin dédiée pour les tiers (la page user couvre les besoins)
- Multi-types de tiers (client / fournisseur / salarié / État) — pas demandé, le modèle ne le porte pas

## Questions ouvertes

Aucune à ce stade. Le seuil de 7 jours pour les fantômes est figé en V1, ajustable en V2 si retour terrain.
