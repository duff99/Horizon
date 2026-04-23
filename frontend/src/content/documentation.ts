/**
 * Contenu éditorial de la page /documentation.
 *
 * Chaque section décrit une page de l'application Horizon :
 *  - `sees`  : ce que l'utilisateur voit à l'écran (éléments visuels)
 *  - `does`  : actions concrètes disponibles (verbes d'action)
 *  - `tips`  : astuces, raccourcis, cas limites (optionnel)
 *
 * Les données sont séparées des composants pour simplifier la maintenance :
 *  quand une feature évolue, il suffit d'éditer ce fichier.
 */

export interface DocSectionData {
  id: string;
  title: string;
  subtitle: string;
  sees: string[];
  does: string[];
  tips?: string[];
}

export const DOC_SECTIONS: DocSectionData[] = [
  {
    id: "premiers-pas",
    title: "Premiers pas",
    subtitle: "Se connecter, choisir sa société, comprendre la barre latérale.",
    sees: [
      "Un écran de connexion demandant email et mot de passe à l'adresse /connexion.",
      "Une barre latérale sombre à gauche avec trois groupes de liens : Pilotage, Configuration, Administration.",
      "En haut à droite de la plupart des pages, un sélecteur de société (EntitySelector) et un sélecteur de période (PeriodSelector).",
      "En bas de la sidebar, votre avatar avec vos initiales, votre rôle (admin ou utilisateur), et un bouton de déconnexion.",
    ],
    does: [
      "Saisissez vos identifiants pour ouvrir une session. La session reste active jusqu'à la déconnexion manuelle ou l'expiration du cookie.",
      "Cliquez sur le sélecteur de société pour filtrer toute l'application sur une entité précise, ou choisissez Toutes les sociétés pour une vue consolidée.",
      "Cliquez sur un preset de période (30 j, 90 j, 12 m, Année, Mois-1) ou Perso. pour saisir une plage de dates manuelle.",
      "Cliquez sur votre avatar en bas de la sidebar pour ouvrir la page Profil. Cliquez sur l'icône à droite pour vous déconnecter.",
      "Accédez à cette documentation à tout moment via le groupe Aide en bas de la sidebar.",
    ],
    tips: [
      "Les présélections de période sont partagées entre les pages compatibles : Tableau de bord, Analyse, Transactions, Imports, Prévisionnel.",
      "Si vous n'avez accès qu'à une seule société, elle est sélectionnée automatiquement.",
    ],
  },
  {
    id: "tableau-de-bord",
    title: "Tableau de bord",
    subtitle:
      "Vue d'ensemble de la trésorerie, des flux et des alertes sur la période choisie.",
    sees: [
      "Quatre KPI en haut : Solde total, Entrées, Sorties, Non catégorisées. Les flux affichent la variation en pourcentage vs la période précédente.",
      "Un bandeau d'alertes automatiques (solde bas, transactions non catégorisées, imports en échec, factures en retard).",
      "Un widget Comparaison mois courant vs mois précédent.",
      "Deux graphiques côte à côte : évolution du solde bancaire dans le temps, et cashflow Entrées/Sorties par jour.",
      "Un bloc Soldes par compte bancaire (un compte par ligne, avec la date du dernier import).",
      "Deux colonnes Top entrées et Top sorties : catégories principales (camembert) et tiers principaux (liste classée).",
    ],
    does: [
      "Changez la période avec le PeriodSelector en haut à droite pour recalculer tous les indicateurs.",
      "Filtrez par société avec l'EntitySelector pour isoler une entité ou consolider toutes les sociétés.",
      "Cliquez sur les tooltips des graphiques pour voir la valeur exacte à une date donnée.",
      "Suivez les alertes pour savoir quelles actions entreprendre en priorité (catégoriser, relancer un import, vérifier une facture).",
    ],
    tips: [
      "Le label de période affiché sous le titre (par ex. 30 derniers jours) confirme la fenêtre appliquée.",
      "Un KPI teinté rouge signale une alerte ou une dérive négative ; vert, une évolution favorable.",
    ],
  },
  {
    id: "analyse",
    title: "Analyse",
    subtitle: "Six widgets KPI pour détecter dérives, tendances et concentrations.",
    sees: [
      "Dérives par catégorie : tableau qui compare le mois courant à la moyenne des trois derniers mois. Un badge Dérive apparaît au-delà de 20 % d'écart.",
      "Top mouvements : catégories en plus forte hausse et plus forte baisse sur les trois derniers mois, avec sparkline.",
      "Runway : nombre de mois de trésorerie restants au rythme de burn actuel, plus la courbe du solde projeté sur six mois.",
      "Comparaison année / année : graphique des revenus et dépenses mois par mois, par rapport à l'année précédente.",
      "Concentration clients : part du top 5 dans le chiffre d'affaires, indice HHI, et niveau de risque (faible, moyen, élevé).",
      "Comparaison des sociétés : revenus, dépenses, variation nette, solde, burn et runway pour chaque entité accessible.",
    ],
    does: [
      "Filtrez par société pour n'analyser qu'une entité ; sinon tous les widgets sont consolidés.",
      "Changez la période d'en-tête pour ajuster visuellement, mais chaque widget garde son propre horizon métier (mois, 3 mois, 6 mois, 12 mois).",
      "Utilisez Top mouvements pour identifier en un coup d'œil les postes qui décalent votre résultat.",
      "Utilisez Concentration clients comme alerte commerciale : un indice HHI supérieur à 2500 signale une dépendance forte.",
    ],
    tips: [
      "Le widget Comparaison des sociétés se masque automatiquement si une seule société est accessible.",
      "Un runway inférieur à six mois passe en rouge pour signaler une urgence de trésorerie.",
    ],
  },
  {
    id: "previsionnel",
    title: "Prévisionnel",
    subtitle:
      "Plan de trésorerie Agicap-like sur 15 mois glissants (3 passés + 12 à venir).",
    sees: [
      "Un graphique en barres Encaissements vs. décaissements par mois, avec hachures sur les mois prévisionnels et une ligne de solde projeté.",
      "Un tableau pivot catégorie × mois : chaque cellule contient le montant réel, prévu ou mixte pour cette catégorie sur ce mois.",
      "En haut : sélecteur de société, sélecteur de scénario, popover Comptes consolidés, et PeriodSelector au mois.",
    ],
    does: [
      "Choisissez ou créez un scénario (référence, optimiste, pessimiste…) pour comparer plusieurs hypothèses.",
      "Sélectionnez précisément les comptes bancaires à consolider dans le pivot via la popover dédiée.",
      "Cliquez sur n'importe quelle cellule pour ouvrir le tiroir d'édition : saisissez une entrée prévisionnelle ponctuelle ou récurrente.",
      "Ajustez la fenêtre de 15 mois avec le PeriodSelector (granularité mois).",
    ],
    tips: [
      "Les mois passés sont remplis à partir des transactions réelles ; les mois futurs combinent engagements et entrées manuelles.",
      "Un scénario est lié à une société : changez de société pour gérer un autre jeu de scénarios.",
      "Si aucun scénario n'existe pour la société, un message vous invite à en créer un.",
    ],
  },
  {
    id: "transactions",
    title: "Transactions",
    subtitle:
      "Liste paginée et filtrable de toutes les opérations bancaires importées.",
    sees: [
      "Une barre de filtres : recherche plein texte (libellé, tiers, montant), PeriodSelector, et toggle Non catégorisées uniquement.",
      "Un tableau avec : date, société (si vue consolidée), tiers/libellé, catégorie, montant (coloré vert crédit / rouge débit).",
      "Une case à cocher par ligne et une case globale pour tout sélectionner sur la page.",
      "Une barre d'actions verte qui apparaît dès qu'une ligne est cochée : combobox catégorie, boutons Catégoriser, Suggérer une règle, Désélectionner.",
      "Un pied de tableau avec pagination (50 par page par défaut).",
    ],
    does: [
      "Recherchez une opération par fragment de libellé, nom de tiers ou montant exact.",
      "Cochez plusieurs lignes, choisissez une catégorie dans la combobox, cliquez sur Catégoriser pour appliquer en masse.",
      "Cliquez sur Suggérer une règle pour générer automatiquement une règle de catégorisation à partir de la sélection (opérateur, libellé, direction, compte, catégorie pré-remplis).",
      "Activez Non catégorisées uniquement pour n'afficher que les opérations qui attendent un traitement.",
      "Naviguez page par page avec les boutons Précédent / Suivant en bas.",
    ],
    tips: [
      "Les opérations aggrégées (parents d'agrégation) apparaissent sur fond gris plus dense pour les distinguer des lignes unitaires.",
      "Les transactions sans catégorie portent un badge ambre « Non catégorisée » très visible.",
    ],
  },
  {
    id: "imports",
    title: "Imports",
    subtitle: "Téléversement de relevés bancaires PDF et historique des imports.",
    sees: [
      "Sur /imports : la liste des imports avec date, nom de fichier, banque, période, statut (En cours, Terminé, Échoué), compteurs Importées et Ignorées, soldes début et fin.",
      "Sur /imports/nouveau : un sélecteur de compte bancaire puis une zone de dépôt de fichier PDF.",
      "Après un import réussi : un encart récapitulant les transactions importées, les doublons ignorés et les éventuels tiers créés à valider.",
      "Une icône œil par ligne dans l'historique pour prévisualiser le PDF original.",
    ],
    does: [
      "Depuis /imports, cliquez sur Nouvel import pour accéder à l'écran de téléversement.",
      "Choisissez le compte bancaire cible dans le menu déroulant, puis glissez-déposez le PDF ou cliquez pour parcourir vos fichiers.",
      "Cliquez sur l'icône œil d'une ligne pour ouvrir un aperçu plein écran du PDF original.",
      "Cliquez sur Ouvrir dans un onglet depuis l'aperçu pour consulter le PDF dans un nouvel onglet.",
      "Filtrez l'historique par société et par période via les sélecteurs d'en-tête.",
    ],
    tips: [
      "Les doublons sont détectés automatiquement : une même transaction ne sera jamais comptée deux fois si vous rechargez un relevé.",
      "Un import échoué (statut rouge) n'impacte aucune donnée : vous pouvez le relancer après correction du fichier.",
      "Les nouveaux tiers détectés passent en statut À valider dans la page Tiers.",
    ],
  },
  {
    id: "engagements",
    title: "Engagements",
    subtitle: "Factures prévues et appariement automatique avec les transactions.",
    sees: [
      "Trois onglets de statut : En attente, Payés, Annulés.",
      "Un filtre de direction : Toutes, Entrées, Sorties.",
      "Deux champs de date (Du... au...) pour restreindre la plage de dates prévues.",
      "Un tableau avec : date d'émission, date prévue, tiers, catégorie, direction (pastille Entrée/Sortie), montant signé, statut, actions.",
      "Pour chaque engagement en attente : boutons Matcher, Modifier, Annuler. Pour les payés : référence de la transaction appariée. Pour les annulés : bouton Réactiver.",
    ],
    does: [
      "Cliquez sur Nouvel engagement en haut à droite pour créer une facture prévue (tiers, catégorie, direction, montant, dates, récurrence).",
      "Cliquez sur Matcher pour apparier manuellement un engagement avec une transaction bancaire existante.",
      "Cliquez sur Modifier pour ajuster montant, date ou catégorie. Sur Annuler pour basculer l'engagement en Annulé (confirmation requise).",
      "Cliquez sur Réactiver pour remettre un engagement annulé en attente.",
      "Filtrez par société pour n'afficher que les engagements liés.",
    ],
    tips: [
      "L'appariement automatique s'exécute à chaque import : il relie un engagement à une transaction quand tiers, montant et date concordent.",
      "Le matching manuel est utile quand la transaction réelle diffère légèrement du prévu (montant arrondi, date décalée).",
    ],
  },
  {
    id: "tiers",
    title: "Tiers",
    subtitle:
      "Validation des clients et fournisseurs détectés automatiquement lors des imports.",
    sees: [
      "Trois onglets : À valider, Actives, Ignorées.",
      "Un tableau simple avec le nom du tiers et les actions disponibles.",
      "Pour les tiers À valider : boutons Valider (bascule en Active) et Ignorer (bascule en Ignorée).",
    ],
    does: [
      "Validez un tiers pour qu'il remonte dans les règles, les engagements et les analyses de concentration.",
      "Ignorez un tiers si vous ne souhaitez pas le suivre individuellement (frais bancaires, virements internes, bruit).",
      "Filtrez par société pour ne voir que les tiers associés à une entité donnée.",
    ],
    tips: [
      "Les nouveaux tiers apparaissent dès le premier import qui les détecte.",
      "Un tiers ignoré peut être relaissé en attente plus tard si besoin (via l'onglet correspondant).",
    ],
  },
  {
    id: "regles",
    title: "Règles de catégorisation",
    subtitle:
      "Règles de matching automatique qui catégorisent les transactions lors de chaque import.",
    sees: [
      "Un compteur en en-tête : total de règles, dont règles système et règles personnalisées.",
      "Un tableau réordonnable par glisser-déposer : priorité, nom, conditions (libellé, direction, montant, tiers, compte), catégorie cible.",
      "Des badges distinguant les règles système (figées) des règles personnalisées (modifiables).",
      "Des actions Modifier et Supprimer (admin uniquement) sur chaque règle.",
    ],
    does: [
      "Cliquez sur Nouvelle règle pour ouvrir le tiroir de création : définissez opérateur de libellé (contient, commence par, regex…), direction, plage de montants, tiers, compte, catégorie cible.",
      "Glissez-déposez une ligne pour changer l'ordre d'évaluation. Les règles sont appliquées de haut en bas, la première qui matche gagne.",
      "Cliquez sur Modifier pour ajuster les conditions d'une règle existante.",
      "Cliquez sur Supprimer (admin seulement) pour retirer définitivement une règle personnalisée.",
      "Filtrez par société pour ne voir que les règles d'une entité donnée.",
    ],
    tips: [
      "Depuis la page Transactions, sélectionnez plusieurs opérations puis Suggérer une règle : Horizon vous pré-remplit le formulaire.",
      "Les règles système ne sont ni modifiables ni supprimables (elles assurent des catégorisations de base comme frais bancaires ou cotisations).",
      "La priorité sert uniquement à trancher entre plusieurs règles qui matchent en même temps.",
    ],
  },
  {
    id: "profil",
    title: "Profil",
    subtitle: "Informations du compte et changement de mot de passe.",
    sees: [
      "Un bloc Informations : email, nom complet, rôle (Administrateur ou Lecture).",
      "Un bloc Changer mon mot de passe avec trois champs : mot de passe actuel, nouveau, confirmation.",
    ],
    does: [
      "Renseignez votre mot de passe actuel, puis un nouveau de 12 caractères minimum, et confirmez-le.",
      "Cliquez sur Mettre à jour le mot de passe : en cas d'erreur côté serveur (mot de passe actuel incorrect), un message s'affiche en rouge.",
    ],
    tips: [
      "Le rôle et le nom complet ne sont modifiables que par un administrateur depuis Administration > Utilisateurs.",
      "La validation du mot de passe est à la fois côté client (longueur, correspondance) et côté serveur.",
    ],
  },
  {
    id: "administration",
    title: "Administration",
    subtitle:
      "Gestion des utilisateurs, des sociétés et des comptes bancaires (admins uniquement).",
    sees: [
      "Utilisateurs (/administration/utilisateurs) : formulaire Créer un utilisateur et liste des comptes existants avec rôle et statut actif/inactif.",
      "Sociétés (/administration/societes) : formulaire Créer une société et liste des entités (raison sociale, SIREN, adresse…).",
      "Comptes bancaires (/administration/comptes-bancaires) : formulaire de création/édition (société, nom, IBAN, BIC, banque, code banque, actif/inactif) et liste des comptes.",
    ],
    does: [
      "Créez un utilisateur en saisissant email, nom complet, rôle (Administrateur ou Lecture) et mot de passe initial.",
      "Modifiez un utilisateur (nom, rôle, statut actif) ou réinitialisez son mot de passe via la boîte de dialogue dédiée.",
      "Créez, modifiez ou désactivez une société dans Sociétés.",
      "Créez un compte bancaire rattaché à une société, avec IBAN formaté automatiquement par bloc de 4.",
    ],
    tips: [
      "Seuls les administrateurs voient les trois pages d'administration. Un utilisateur Lecture ne voit que Pilotage et Configuration.",
      "Désactiver un compte bancaire ou une société le fait disparaître des sélecteurs, sans supprimer l'historique associé.",
      "Un utilisateur Lecture peut consulter toutes les pages non-admin mais ne peut ni créer ni supprimer.",
    ],
  },
  {
    id: "securite",
    title: "Sécurité et sauvegardes",
    subtitle: "Comment vos données sont protégées et restaurables.",
    sees: [
      "Une sauvegarde complète de la base PostgreSQL est exécutée automatiquement chaque nuit à 2h du matin.",
      "Les sauvegardes sont conservées localement sur le serveur, avec rotation pour limiter l'espace disque.",
      "L'API /api/admin/backups (admin uniquement) liste les sauvegardes disponibles et leurs métadonnées.",
      "Le serveur nginx applique des en-têtes de sécurité renforcés : HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.",
    ],
    does: [
      "Consultez régulièrement /api/admin/backups pour vérifier que les snapshots récents sont présents.",
      "Demandez à l'administrateur technique de déclencher une restauration en cas d'incident — elle se fait à partir du dump le plus récent.",
      "Changez votre mot de passe depuis la page Profil si vous soupçonnez une compromission.",
    ],
    tips: [
      "Les sessions reposent sur un cookie HTTP-only : impossible à lire depuis du JavaScript, ce qui bloque les attaques XSS.",
      "En cas de doute, fermez toutes vos sessions en changeant votre mot de passe (les cookies actifs restent valides, mais un admin peut forcer une invalidation).",
      "Les PDF importés sont stockés à part pour permettre la prévisualisation, et ne sont jamais exposés en dehors de l'application authentifiée.",
    ],
  },
];
