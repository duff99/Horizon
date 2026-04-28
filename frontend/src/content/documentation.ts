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
 *
 * Discipline éditoriale (cf. revue Phase B) :
 *  - Français, vouvoiement, factuel, sans emoji.
 *  - Nommer les boutons et libellés UI exactement comme dans le code.
 *  - Si une fonction n'existe pas dans le code : ne pas l'inventer.
 *  - Première occurrence d'un terme métier (HHI, runway, burn, scénario,
 *    engagement, tiers) : glose entre parenthèses.
 *  - `panel` : si la version page devient longue, on resserre l'aide drawer
 *    (summary court + does limité aux essentiels + hide des tips si possible).
 */

export interface DocSectionData {
  id: string;
  title: string;
  subtitle: string;
  sees: string[];
  does: string[];
  tips?: string[];
  /**
   * Override optionnel pour le panneau d'aide contextuel.
   * Si absent, le panneau réutilise subtitle / sees / does / tips.
   * Si présent : `summary` remplace subtitle, et `sees/does/tips` (s'ils sont
   * définis) remplacent leurs équivalents. `hide` permet de masquer un bloc
   * entier dans le panneau sans le retirer de la doc complète.
   */
  panel?: {
    summary?: string;
    sees?: string[];
    does?: string[];
    tips?: string[];
    hide?: ("sees" | "does" | "tips")[];
  };
}

export const DOC_SECTIONS: DocSectionData[] = [
  {
    id: "premiers-pas",
    title: "Premiers pas",
    subtitle:
      "Se connecter, choisir sa société, comprendre la barre latérale et les sélecteurs d'en-tête.",
    sees: [
      "Un écran de connexion à l'adresse /connexion : champ Email, champ Mot de passe, bouton Se connecter, et le logo « horizon ».",
      "Une barre latérale sombre à gauche, organisée en trois groupes : Pilotage (Tableau de bord, Analyse, Prévisionnel, Transactions, Imports), Configuration (Engagements, Tiers, Règles), Administration (Utilisateurs, Sociétés, Comptes bancaires, Journal d'audit).",
      "En haut à droite de la plupart des pages : un sélecteur de société (EntitySelector), souvent suivi d'un sélecteur de période (PeriodSelector).",
      "En haut à droite de chaque page de l'application, un bouton « Aide » avec une icône point d'interrogation, qui ouvre un panneau latéral contextuel décrivant la page courante.",
      "En bas de la sidebar : votre avatar (vos initiales), votre nom et votre rôle (Administrateur ou Lecture), et une icône de déconnexion à droite.",
    ],
    does: [
      "Pour vous connecter : saisissez votre email, votre mot de passe, puis cliquez sur Se connecter. La session reste active jusqu'à la déconnexion manuelle ou l'expiration du cookie de session.",
      "Pour changer de société : cliquez sur le sélecteur en haut à droite, puis choisissez une entité dans la liste. L'option Toutes les sociétés est disponible sur les pages où une vue consolidée a du sens (Tableau de bord, Transactions, Imports, Engagements, Tiers, Règles). Sur les pages Analyse et Prévisionnel, qui calculent des KPI ou un plan de trésorerie par société, vous devez choisir une société unique : la première société accessible est sélectionnée automatiquement à votre arrivée. Le filtre s'applique immédiatement à toute l'application.",
      "Pour changer de période : cliquez sur l'un des presets (30 j, 90 j, 12 m, Année, Mois-1) ou sur Perso. pour saisir deux dates manuellement (du... au...).",
      "Pour ouvrir l'aide d'une page : cliquez sur le bouton Aide en haut à droite, ou utilisez le raccourci clavier « ? » (sauf si vous êtes en train de saisir du texte dans un champ).",
      "Pour ouvrir votre profil : cliquez sur votre avatar en bas de la sidebar. Pour vous déconnecter : cliquez sur l'icône à droite de votre nom.",
      "Pour accéder à cette documentation complète : groupe Aide en bas de la sidebar, ou lien « Voir le guide complet → » au pied du panneau d'aide contextuel.",
    ],
    tips: [
      "Les présélections de période sont partagées entre les pages compatibles : Tableau de bord, Analyse, Transactions, Imports, Prévisionnel.",
      "Si vous n'avez accès qu'à une seule société, elle est sélectionnée automatiquement et le sélecteur peut ne pas s'afficher.",
      "Le bouton Aide n'apparaît pas sur la page de connexion ni sur la page Documentation elle-même : il n'a de sens que sur les pages métier.",
      "Le raccourci « ? » fonctionne uniquement quand le focus n'est pas dans un champ de saisie (input, textarea, select). Sinon le caractère est tapé dans le champ.",
      "Vous pouvez fermer le panneau d'aide en cliquant à l'extérieur, en appuyant sur Échap, ou en cliquant à nouveau sur le bouton Aide.",
      "À la navigation entre pages, le panneau d'aide se referme automatiquement pour ne pas afficher l'aide d'une page que vous avez quittée.",
    ],
    panel: {
      summary:
        "Connexion, sélecteurs de société et de période, bouton Aide. Le panneau s'ouvre via le bouton « Aide » ou le raccourci « ? ».",
      hide: ["tips"],
    },
  },
  {
    id: "tableau-de-bord",
    title: "Tableau de bord",
    subtitle:
      "Vue d'ensemble de la trésorerie, des flux et des alertes sur la période choisie.",
    sees: [
      "Un en-tête avec le titre Tableau de bord, et juste en dessous le libellé de la période active (par exemple « Période : 30 derniers jours »).",
      "Quatre indicateurs clés (KPI) en haut : Solde total (à la date du dernier import), Entrées de la période, Sorties de la période, Non catégorisées (nombre d'opérations à traiter).",
      "Pour Entrées et Sorties : une variation en pourcentage par rapport à la période précédente, en vert si l'évolution est favorable, en rouge sinon. Le KPI Non catégorisées passe en orange dès qu'il y a au moins une opération à traiter.",
      "Un bandeau d'alertes automatiques (codé info / warning / critical) : solde bas, opérations non catégorisées en nombre, imports en échec, factures en retard, etc. Aucune alerte affichée = situation saine.",
      "Un widget Comparaison mois courant vs mois précédent.",
      "Deux graphiques côte à côte : Solde estimé sur 90 jours (aire colorée, reconstruit à rebours depuis le dernier solde connu), et Entrées / Sorties quotidiennes (barres vertes pour les crédits, rouges pour les débits).",
      "Un tableau Soldes par compte : société, nom du compte, banque, solde courant, écart vs mois précédent (en vert ou rouge), date du dernier import.",
      "Deux colonnes en bas : à gauche les Entrées (Entrées par catégorie en camembert + Top encaissements), à droite les Sorties (Sorties par catégorie en camembert + Top décaissements).",
    ],
    does: [
      "Pour recalculer tous les indicateurs sur une autre période : utilisez le PeriodSelector en haut à droite (preset ou plage personnalisée).",
      "Pour isoler une société ou consolider toutes les sociétés : utilisez l'EntitySelector en haut à droite.",
      "Pour lire la valeur exacte d'un point sur un graphique : survolez avec la souris pour faire apparaître le tooltip (date + montant formaté en euros).",
      "Pour traiter une alerte : suivez la consigne décrite (catégoriser des opérations, vérifier un import en échec, relancer une facture). Les alertes ne sont pas cliquables — elles indiquent où agir, vous ouvrez ensuite la page concernée depuis la sidebar.",
      "Pour voir le détail d'une catégorie sur un camembert : passez la souris dessus ; le tooltip affiche le montant et le pourcentage.",
    ],
    tips: [
      "Le label « au JJ/MM/AAAA » sous le KPI Solde total indique la date du dernier import pris en compte. Aucun import = mention « Aucun import ».",
      "Une variation en gris « = » signifie une stabilité parfaite ; « · n/a » apparaît quand la période précédente était vide (division par zéro évitée).",
      "Le graphique Solde estimé est reconstruit à rebours à partir du dernier solde connu : il ne nécessite donc pas un solde de départ explicite.",
      "Si un compte n'a jamais reçu d'import, il n'apparaît pas dans le tableau Soldes par compte.",
      "Le widget Comparaison mois courant vs mois précédent compare le mois calendaire en cours au précédent, indépendamment de la période choisie en haut à droite.",
      "Voir aussi la section Analyse pour des indicateurs plus avancés (runway, dérives, concentration clients).",
    ],
    panel: {
      summary:
        "Vue d'ensemble : KPI, alertes, graphiques de solde et de cashflow, soldes par compte, top entrées/sorties.",
      does: [
        "Changez la période avec le PeriodSelector pour recalculer les indicateurs.",
        "Filtrez par société avec l'EntitySelector pour isoler ou consolider.",
        "Survolez les graphiques pour lire les valeurs exactes via les tooltips.",
        "Suivez les alertes pour savoir où agir en priorité.",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "analyse",
    title: "Analyse",
    subtitle:
      "Six widgets KPI pour détecter dérives, tendances et concentrations sur les 12 derniers mois.",
    sees: [
      "Autonomie de trésorerie (Runway) : nombre de mois pendant lesquels la société peut tenir si elle continue à dépenser au rythme actuel. Phrase d'interprétation contextuelle (Stable / Vigilance / Critique), consommation mensuelle (Burn rate), trésorerie disponible aujourd'hui, courbe projetée sur 6 mois.",
      "Besoin en fonds de roulement (BFR) : trois métriques combinées — DSO (délai moyen de paiement client), DPO (délai moyen de paiement fournisseur), BFR (créances clients à encaisser moins dettes fournisseurs à payer). Le widget reste vide tant qu'aucun engagement n'a été saisi sur la page Engagements.",
      "Précision du prévisionnel : tableau des 6 derniers mois comparant le prévu (saisi sur la page Prévisionnel) au réalisé (transactions importées). L'écart est coloré (vert si fiable, ambre si attention, rouge si écart fort). Ce widget reste vide tant qu'aucune prévision n'a été saisie.",
      "Dérives par catégorie : tableau qui compare le mois courant à la moyenne des trois derniers mois. Un badge « Dérive » apparaît au-delà de 20 % d'écart. Cliquez sur une ligne pour voir précisément les transactions du mois qui expliquent l'écart.",
      "Top mouvements : catégories en plus forte hausse et plus forte baisse sur les trois derniers mois, avec une mini-courbe (sparkline) pour visualiser la trajectoire. Les libellés longs sont affichés en entier (passez la souris pour le tooltip).",
      "Concentration clients : part du top 5 dans le chiffre d'affaires, indice HHI (Herfindahl-Hirschman, mesure standard de la concentration) et niveau de risque (faible, moyen, élevé).",
      "Comparaison année sur année (YoY) : graphique des revenus et dépenses mois par mois, comparés à l'année précédente.",
      "Comparaison des sociétés : pour chaque entité accessible, revenus, dépenses, variation nette, solde, consommation mensuelle et autonomie.",
      "En bas de page : un accordéon Lexique des sigles (Runway, Burn rate, YoY, HHI, DSO, DPO, BFR) explicitant chaque terme financier utilisé.",
    ],
    does: [
      "L'analyse se fait toujours sur une société à la fois : à votre arrivée, la première société accessible est sélectionnée automatiquement (ordre alphabétique). Pour basculer sur une autre société, utilisez l'EntitySelector en haut à droite. La page n'a pas de mode « Toutes les sociétés » car un agrégat cross-entité n'a pas de sens financier (chaque société a son propre business et ses propres tendances).",
      "Pour ajuster visuellement la période d'en-tête : utilisez le PeriodSelector. Attention : chaque widget garde son propre horizon métier (mois courant, 3 mois, 6 mois, 12 mois) ; le PeriodSelector ici n'a qu'un rôle de cohérence visuelle avec les autres pages.",
      "Pour identifier en un coup d'œil les postes qui décalent votre résultat : lisez la colonne « Dérive » du tableau Dérives par catégorie, puis le widget Top mouvements pour confirmer la tendance.",
      "Pour évaluer un risque commercial : ouvrez Concentration clients ; un indice HHI supérieur à 2500 signale une dépendance forte à quelques clients (le marché américain considère 2500 comme le seuil d'alerte antitrust).",
      "Pour comparer vos sociétés entre elles : descendez jusqu'au tableau Comparaison des sociétés (masqué si vous n'avez accès qu'à une seule entité).",
    ],
    tips: [
      "Le widget Comparaison des sociétés se masque automatiquement si une seule société est accessible (sinon il n'aurait rien à comparer).",
      "Une autonomie (Runway) inférieure à six mois passe en rouge pour signaler une urgence de trésorerie ; entre 6 et 12 mois, elle est marquée en orange.",
      "La sparkline du widget Top mouvements montre la tendance brute, pas un cumul : un pic isolé n'indique pas forcément une dérive durable.",
      "L'indice HHI varie de 0 (parfaitement diversifié) à 10 000 (un seul client). Repères usuels : <1500 = faible, 1500-2500 = modérée, >2500 = élevée.",
      "Voir aussi Tableau de bord pour la vue immédiate, et Prévisionnel pour la projection détaillée mois par mois.",
    ],
    panel: {
      summary:
        "Indicateurs clés (par société, sélection auto de la 1ère accessible) : autonomie (Runway), BFR (DSO/DPO), précision du prévisionnel, dérives par catégorie avec drill-down, top mouvements, concentration clients, YoY, comparaison entre sociétés.",
      does: [
        "Choisissez la société analysée dans l'EntitySelector (la première accessible est pré-sélectionnée).",
        "Cliquez une ligne du tableau Dérives pour voir les transactions du mois qui l'expliquent.",
        "Surveillez Autonomie (Runway, rouge < 6 mois), BFR (DSO élevé = clients lents), et la Précision du prévisionnel (écart > 20 % = forecast à revoir).",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "previsionnel",
    title: "Prévisionnel",
    subtitle:
      "Plan de trésorerie sur 15 mois glissants (3 passés + 12 à venir), façon Agicap.",
    sees: [
      "Un graphique en barres Encaissements vs. décaissements par mois, avec hachures sur les mois prévisionnels et une ligne représentant le solde projeté. Une mention « Hachures = prévisionnel · ligne = solde projeté » au-dessus le rappelle.",
      "Un tableau pivot catégorie × mois : chaque cellule contient le montant réel, prévu, ou un mix des deux pour cette catégorie sur ce mois.",
      "En haut à droite : EntitySelector, ScenarioSelector (sélection ou création d'un scénario), popover Comptes consolidés (choix des comptes bancaires inclus dans le pivot), PeriodSelector au mois.",
      "À votre arrivée sur la page, la première société accessible est sélectionnée automatiquement (l'agrégat « Toutes les sociétés » n'est pas proposé sur le Prévisionnel : chaque société a son propre scénario indépendant).",
      "Si la société n'a aucun scénario : un message « Créez votre premier scénario dans le menu ci-dessus pour démarrer ».",
    ],
    does: [
      "Pour comparer plusieurs hypothèses : créez plusieurs scénarios (référence, optimiste, pessimiste, etc.) via le ScenarioSelector et basculez de l'un à l'autre.",
      "Pour limiter le pivot à certains comptes bancaires : ouvrez la popover Comptes consolidés et cochez/décochez les comptes voulus.",
      "Pour saisir une entrée prévisionnelle (montant, date, récurrence simple) : cliquez sur n'importe quelle cellule du pivot. Le tiroir d'édition s'ouvre à droite, pré-rempli sur le mois et la catégorie cliqués.",
      "Pour ajuster la fenêtre temporelle : utilisez le PeriodSelector en haut à droite, en granularité mois (presets : 12 m, Année, Mois-1, Perso.).",
      "Pour fermer le tiroir d'édition sans enregistrer : cliquez en dehors ou utilisez le bouton Annuler du tiroir.",
    ],
    tips: [
      "Les mois passés du pivot sont remplis à partir des transactions réelles ; les mois futurs combinent les engagements existants et les saisies prévisionnelles manuelles.",
      "Un scénario est lié à une société : changer de société dans l'EntitySelector ouvre l'autre jeu de scénarios. Vous ne pouvez pas comparer deux scénarios de sociétés différentes côte à côte.",
      "Si vous n'avez accès qu'à une seule société, elle est utilisée automatiquement même sans sélection explicite.",
      "Si vous changez de scénario en cours de saisie, le tiroir se referme : enregistrez avant de basculer.",
      "Voir aussi la section Engagements pour saisir une facture précise à venir, et la section Analyse pour l'autonomie de trésorerie (Runway) calculée à partir de la consommation récente (Burn rate).",
    ],
    panel: {
      summary:
        "Pivot catégorie × mois sur 15 mois (3 passés + 12 à venir). Choix d'un scénario obligatoire ; clic sur une cellule pour saisir une prévision.",
      does: [
        "Choisissez ou créez un scénario via le ScenarioSelector.",
        "Sélectionnez les comptes bancaires à consolider via la popover dédiée.",
        "Cliquez sur une cellule pour saisir une entrée prévisionnelle (tiroir d'édition).",
        "Ajustez la fenêtre via le PeriodSelector (granularité mois).",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "transactions",
    title: "Transactions",
    subtitle:
      "Liste paginée et filtrable de toutes les opérations bancaires importées.",
    sees: [
      "Un en-tête avec le nombre total d'opérations et, si applicable, le nombre de non catégorisées sur la page courante.",
      "Une barre de filtres : un champ de recherche plein texte (placeholder « Rechercher par libellé, tiers, montant... »), un PeriodSelector, et à droite un toggle « Non catégorisées uniquement ».",
      "Un tableau avec : case à cocher, date, société (uniquement en vue consolidée), Tiers / Libellé (le tiers s'il est connu, sinon le libellé brut), Catégorie (badge gris si catégorisée, badge orange « Non catégorisée » sinon), Montant (vert avec « + » pour les crédits, rouge pour les débits).",
      "Une case à cocher en en-tête pour tout sélectionner sur la page.",
      "Une barre d'actions verte qui apparaît dès qu'au moins une ligne est cochée : « N sélectionnée(s) », une combobox catégorie, les boutons Catégoriser, Suggérer une règle, Désélectionner.",
      "Un pied de tableau avec une pagination complète : récapitulatif (« Affichage 51 à 100 sur 1234 · Page 2 sur 25 »), sélecteur Lignes (25 / 50 / 100 / 200), boutons « (première), ‹ (précédente), numéros de page directement cliquables avec ellipsis intelligente, › (suivante), » (dernière). Au-delà de 5 pages, un champ Aller à : permet de saisir un numéro et valider avec Entrée.",
    ],
    does: [
      "Pour rechercher une opération : saisissez un fragment de libellé, un nom de tiers ou un montant exact dans le champ de recherche (ex. : tapez « 500 » pour ne voir que les opérations contenant ce montant, ou « URSSAF » pour cibler un tiers).",
      "Pour catégoriser plusieurs opérations en masse : 1. Cochez les lignes concernées (ou la case d'en-tête pour toute la page). 2. Choisissez une catégorie dans la combobox de la barre verte. 3. Cliquez sur Catégoriser. Les opérations sont mises à jour, la sélection est vidée.",
      "Pour transformer la sélection en règle automatique : cliquez sur Suggérer une règle. Horizon analyse les libellés communs et ouvre le tiroir de création de règle pré-rempli (opérateur de libellé, valeur, sens, compte, catégorie).",
      "Pour vider la sélection sans agir : cliquez sur Désélectionner.",
      "Pour ne voir que les opérations à traiter : activez le toggle « Non catégorisées uniquement ». Toggle désactivé = liste complète.",
      "Pour naviguer rapidement dans la liste : la barre de pagination en bas du tableau propose plusieurs raccourcis. Cliquez directement sur un numéro de page, ou utilisez « (début), ‹ (précédente), › (suivante), » (fin). Au-delà de 5 pages, le champ Aller à : permet de sauter à une page précise (validez avec Entrée).",
      "Pour afficher plus de transactions par écran : changez le sélecteur Lignes : (25 / 50 / 100 / 200) dans la barre de pagination. À 200, vous parcourez plus vite un gros volume sans recharger.",
    ],
    tips: [
      "Les opérations agrégées (lignes parents qui regroupent plusieurs sous-écritures) apparaissent sur fond gris plus dense pour les distinguer des lignes unitaires.",
      "Une opération sans catégorie porte un badge ambre « Non catégorisée » très visible : c'est ce qui alimente le KPI du Tableau de bord.",
      "La barre d'actions verte ne s'affiche que s'il y a au moins une sélection. Le bouton Catégoriser reste désactivé tant qu'aucune catégorie n'a été choisie dans la combobox.",
      "Si Suggérer une règle échoue (ex. : libellés trop hétérogènes), un message rouge s'affiche dans la barre verte : ajustez la sélection puis recommencez.",
      "Les filtres et la pagination se réinitialisent à la page 1 dès que vous changez un filtre, pour éviter d'afficher une page vide.",
      "Voir aussi la section Règles de catégorisation pour automatiser durablement le travail de catégorisation, et la section Imports pour comprendre d'où viennent ces opérations.",
    ],
    panel: {
      summary:
        "Liste paginée des opérations bancaires. Filtres, recherche, sélection multiple, catégorisation en masse, suggestion de règle.",
      does: [
        "Recherchez par libellé, tiers ou montant dans la barre de filtres.",
        "Cochez plusieurs lignes, choisissez une catégorie, cliquez sur Catégoriser.",
        "Cliquez sur Suggérer une règle pour automatiser une catégorisation récurrente.",
        "Activez « Non catégorisées uniquement » pour vous concentrer sur les lignes à traiter.",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "imports",
    title: "Imports",
    subtitle:
      "Téléversement de relevés bancaires PDF et historique des imports précédents.",
    sees: [
      "Sur /imports : la liste des imports avec date, nom de fichier, banque (code court en majuscules), période couverte (du... au...), statut (En cours, Terminé, Échoué) coloré, compteurs Importées et Ignorées (doublons), soldes de début et de fin, et une icône œil par ligne pour prévisualiser le PDF.",
      "Sur /imports/nouveau : un titre « Importer un relevé bancaire », un menu déroulant Compte bancaire (libellé du compte + IBAN entre parenthèses), puis une zone de dépôt de fichier (FileDropzone) qui n'apparaît qu'après sélection d'un compte.",
      "Pendant l'analyse : un encart « Analyse en cours… ».",
      "En cas d'échec : un encart rouge « Erreur : ... » avec le message du serveur.",
      "Après un import réussi : un encart « Import terminé » récapitulant le nombre de transactions importées, les éventuels doublons ignorés, et les nouveaux tiers créés à valider.",
    ],
    does: [
      "Pour démarrer un import : depuis /imports, cliquez sur Nouvel import en haut à droite. Vous arrivez sur /imports/nouveau.",
      "Pour téléverser un PDF : 1. Choisissez le compte bancaire cible dans le menu déroulant. 2. La zone de dépôt apparaît : glissez-déposez le PDF, ou cliquez pour parcourir vos fichiers. 3. L'analyse démarre automatiquement (rien d'autre à valider).",
      "Pour prévisualiser un PDF déjà importé : cliquez sur l'icône œil dans la colonne Actions. Une fenêtre modale s'ouvre avec le PDF intégré ; cliquez à l'extérieur ou sur Fermer pour la quitter.",
      "Pour ouvrir le PDF dans un nouvel onglet (ex. : pour zoomer ou imprimer) : depuis l'aperçu modal, cliquez sur Ouvrir dans un onglet en haut à droite.",
      "Pour filtrer l'historique : utilisez l'EntitySelector (par société) et le PeriodSelector (sur la date d'import).",
    ],
    tips: [
      "Les doublons sont détectés automatiquement : si vous rechargez un relevé qui couvre une période déjà importée, les opérations identiques sont comptées dans la colonne Ignorées et ne créent pas de double écriture.",
      "Un import en statut Échoué (badge rouge) n'impacte aucune donnée. Vous pouvez relancer après correction du fichier (ex. : PDF incomplet, format inconnu).",
      "Les nouveaux tiers détectés lors d'un import passent en statut « À valider » dans la page Tiers. Le compteur « N nouveau(x) tiers à valider » de l'encart de fin d'import vous le rappelle.",
      "Le format accepté est exclusivement PDF. Tout autre format est refusé côté navigateur.",
      "Le sélecteur de compte ne liste que les comptes actifs. Pour ajouter ou réactiver un compte : Administration > Comptes bancaires (admin uniquement).",
      "Voir aussi la section Tiers pour traiter les tiers à valider, et la section Transactions pour vérifier les opérations importées.",
    ],
    panel: {
      summary:
        "Téléversement de relevés bancaires PDF et historique des imports. Détection automatique des doublons et des nouveaux tiers.",
      does: [
        "Cliquez sur Nouvel import pour téléverser un nouveau PDF.",
        "Choisissez le compte bancaire cible, puis déposez le PDF dans la zone prévue.",
        "Cliquez sur l'icône œil d'un import pour prévisualiser le PDF original.",
        "Filtrez l'historique par société et par période via les sélecteurs d'en-tête.",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "engagements",
    title: "Engagements",
    subtitle:
      "Factures et paiements prévus à venir, avec appariement automatique aux transactions bancaires.",
    sees: [
      "Trois onglets de statut en haut : En attente, Payés, Annulés.",
      "Un sélecteur de direction (Toutes, Entrées, Sorties) sous forme de pilule.",
      "Deux champs de date « Du... au... » pour restreindre la plage des dates prévues, plus un bouton Réinitialiser quand au moins une date est saisie.",
      "Un tableau avec : date d'émission, date prévue, tiers (avec description en dessous si renseignée), catégorie, direction (pastille verte « Entrée » ou rose « Sortie »), montant signé (vert pour entrée, rouge pour sortie), statut (badge), actions.",
      "Pour un engagement En attente : trois boutons Matcher, Modifier, Annuler. Pour un engagement Payé : la référence de la transaction appariée (« Tx #123 »). Pour un engagement Annulé : un bouton Réactiver.",
      "Si la liste est vide pour les filtres courants : un message « Aucun engagement — créez-en un pour suivre vos factures à venir ».",
    ],
    does: [
      "Pour créer un engagement (facture ou paiement à venir) : cliquez sur Nouvel engagement en haut à droite. Le formulaire demande la société (en mode création seulement), la direction (Sortie par défaut), le montant, la référence, la date d'émission, la date prévue, le tiers, la catégorie, une description.",
      "Pour apparier manuellement un engagement à une transaction réelle : sur la ligne, cliquez sur Matcher. Une boîte de dialogue propose les transactions candidates ; choisissez la bonne pour basculer l'engagement en Payé.",
      "Pour ajuster un engagement : cliquez sur Modifier sur la ligne ; le même formulaire s'ouvre, pré-rempli (sauf la société, qui n'est pas modifiable a posteriori).",
      "Pour annuler un engagement : cliquez sur Annuler ; une confirmation est demandée (« Annuler l'engagement \"...\" ? »). L'engagement bascule en Annulé sans supprimer son historique.",
      "Pour réactiver un engagement annulé : ouvrez l'onglet Annulés, puis cliquez sur Réactiver pour le remettre en statut En attente.",
      "Pour filtrer la liste : combinez l'onglet de statut, le sélecteur de direction, les bornes de date, et l'EntitySelector.",
    ],
    tips: [
      "L'appariement automatique s'exécute à chaque import : il relie un engagement à une transaction quand le tiers, le montant et la date concordent suffisamment. Pas besoin d'intervenir si tout colle.",
      "Le matching manuel est utile quand la transaction réelle diffère légèrement du prévu (ex. : montant arrondi, date décalée d'un jour, virement scindé).",
      "Côté formulaire : la date d'émission doit être antérieure ou égale à la date prévue ; le montant doit être strictement positif (un message rouge sinon).",
      "L'email/société d'un engagement existant ne peut pas être réaffecté à une autre société : créez-en un nouveau si vous vous êtes trompé de société.",
      "Voir aussi la section Tiers pour valider les tiers utilisés ici, et la section Prévisionnel qui agrège ces engagements dans le pivot mensuel.",
    ],
    panel: {
      summary:
        "Factures et paiements prévus, avec appariement aux transactions bancaires (automatique à l'import, manuel via Matcher).",
      does: [
        "Cliquez sur Nouvel engagement pour saisir une facture à venir (montant, dates, tiers, catégorie).",
        "Cliquez sur Matcher pour apparier manuellement avec une transaction existante.",
        "Filtrez par statut (onglets), direction (Entrées/Sorties) et plage de dates.",
        "Cliquez sur Annuler ou Réactiver pour basculer le statut.",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "tiers",
    title: "Tiers",
    subtitle:
      "Validation des clients et fournisseurs (« tiers ») détectés automatiquement lors des imports.",
    sees: [
      "Trois onglets en haut : À valider, Actives, Ignorées (le compteur réel se voit sur l'effectif affiché).",
      "Un tableau avec deux colonnes : Nom du tiers, et une colonne Actions à droite.",
      "Pour les tiers À valider uniquement : deux boutons Valider (vert) et Ignorer (variant ghost).",
      "Pour les onglets Actives et Ignorées : aucun bouton d'action en l'état actuel — la liste est en lecture seule (le statut a été figé après validation).",
      "Si la liste est vide pour le filtre courant : un message « Aucun tiers à valider / actives / ignorées ».",
    ],
    does: [
      "Pour valider un nouveau tiers : ouvrez l'onglet À valider, puis cliquez sur Valider sur la ligne. Le tiers passe en Active et devient utilisable dans les règles, les engagements et les analyses de concentration.",
      "Pour ignorer un tiers que vous ne voulez pas suivre individuellement (frais bancaires récurrents, virements internes, bruit) : cliquez sur Ignorer sur la ligne. Le tiers passe en Ignorée et n'apparaîtra plus dans les listes par défaut.",
      "Pour filtrer par société : utilisez l'EntitySelector en haut à droite afin de ne voir que les tiers associés à une entité donnée.",
    ],
    tips: [
      "Les nouveaux tiers apparaissent dans À valider dès le premier import qui les détecte, à condition que l'extracteur identifie un libellé suffisamment net.",
      "Une fois validé ou ignoré, le statut d'un tiers ne se rebascule pas depuis cette page : pour un changement de statut, contactez l'administrateur (qui peut intervenir en base).",
      "Valider un tiers ne crée pas automatiquement de règle : vous restez maître du lien tiers ↔ catégorie via la page Règles.",
      "Voir aussi la section Imports (origine des tiers détectés) et Règles de catégorisation (utiliser un tiers comme condition).",
    ],
    panel: {
      summary:
        "Validez ou ignorez les clients/fournisseurs détectés lors des imports. Trois onglets : À valider, Actives, Ignorées.",
      does: [
        "Onglet À valider : cliquez sur Valider pour activer un tiers, ou Ignorer pour l'écarter.",
        "Onglets Actives et Ignorées : lecture seule (les statuts y sont figés).",
        "Filtrez par société via l'EntitySelector pour ne voir que les tiers d'une entité.",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "regles",
    title: "Règles de catégorisation",
    subtitle:
      "Règles de matching automatique qui catégorisent les transactions à chaque import.",
    sees: [
      "Un compteur en en-tête : nombre total de règles, dont règles système et règles personnalisées.",
      "Un tableau réordonnable par glisser-déposer (icône poignée à gauche de chaque ligne) : priorité, nom, conditions (libellé, sens, plage de montants, tiers, compte), catégorie cible.",
      "Des badges qui distinguent les règles système (figées, posées par Horizon) des règles personnalisées (modifiables et supprimables).",
      "Sur chaque règle personnalisée : un bouton Modifier ; pour les administrateurs uniquement, un bouton Supprimer (avec confirmation).",
      "En haut à droite : EntitySelector et bouton Nouvelle règle.",
    ],
    does: [
      "Pour créer une règle : cliquez sur Nouvelle règle. Un tiroir s'ouvre avec : Nom, Priorité (par défaut 5000), Scope (Globale ou société précise), Filtre libellé (opérateur contient / commence par / finit par / égal à + valeur), Sens (Tous / Crédits uniquement / Débits uniquement), Catégorie cible.",
      "Pour tester une règle avant de la créer : cliquez sur Aperçu dans le tiroir pour voir combien de transactions existantes seraient capturées.",
      "Pour appliquer immédiatement une règle nouvellement créée à l'historique : cliquez sur Créer et appliquer (au lieu de Créer simple). Sinon la règle ne joue qu'à partir des prochains imports et des prochaines actions.",
      "Pour réordonner les règles : glissez-déposez une ligne. Les règles sont évaluées de haut en bas, la première qui matche gagne.",
      "Pour modifier une règle existante : cliquez sur Modifier sur la ligne. Le même tiroir s'ouvre, pré-rempli.",
      "Pour supprimer une règle personnalisée (admin uniquement) : cliquez sur Supprimer ; une confirmation est demandée (« Supprimer la règle \"...\" ? »).",
    ],
    tips: [
      "Depuis la page Transactions, sélectionnez plusieurs opérations puis Suggérer une règle : Horizon vous pré-remplit le formulaire (libellé commun, sens, compte, catégorie déjà choisie le cas échéant).",
      "Les règles système ne sont ni modifiables ni supprimables. Elles assurent les catégorisations de base (frais bancaires, cotisations, virements internes) et garantissent une couverture minimale même sans configuration.",
      "Les opérateurs de libellé disponibles sont contient, commence par, finit par, égal à. Il n'y a pas d'opérateur regex (expression régulière) : pour des cas complexes, créez plusieurs règles plus simples.",
      "La priorité numérique sert uniquement à trancher entre plusieurs règles qui matchent en même temps : plus le nombre est petit, plus la règle passe en premier dans l'ordre d'évaluation. L'ordre visible dans le tableau reflète déjà cet ordre d'évaluation.",
      "Le scope « Globale » s'applique à toutes les sociétés ; un scope société restreint l'évaluation aux opérations de cette société uniquement.",
      "Voir aussi la section Transactions (origine des règles via Suggérer une règle) et la section Tiers (un tiers validé peut servir de condition).",
    ],
    panel: {
      summary:
        "Règles automatiques qui catégorisent les opérations à chaque import. Évaluées de haut en bas, première règle qui matche gagne.",
      does: [
        "Cliquez sur Nouvelle règle pour ouvrir le tiroir : libellé, sens, scope, catégorie cible.",
        "Cliquez sur Aperçu pour vérifier l'impact avant validation.",
        "Cliquez sur Créer et appliquer pour rejouer la règle sur l'historique.",
        "Glissez-déposez les lignes pour réordonner ; Modifier ou Supprimer (admin) sur chaque règle personnalisée.",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "profil",
    title: "Profil",
    subtitle: "Informations du compte et changement de votre mot de passe.",
    sees: [
      "Un bloc Informations affichant trois champs en lecture seule : Email, Nom complet, Rôle (« Administrateur » ou « Lecture »).",
      "Un bloc Changer mon mot de passe avec trois champs masqués : Mot de passe actuel, Nouveau mot de passe (12 caractères min.), Confirmer le nouveau mot de passe.",
      "Un bouton Mettre à jour le mot de passe en bas du formulaire ; pendant l'envoi, son libellé devient « Mise à jour… ».",
      "Des messages d'état contextuels : un encart vert « Mot de passe mis à jour » en cas de succès, ou un encart rouge décrivant l'erreur en cas d'échec.",
    ],
    does: [
      "Pour changer de mot de passe : 1. Saisissez votre mot de passe actuel. 2. Saisissez un nouveau mot de passe (12 caractères minimum). 3. Confirmez-le à l'identique. 4. Cliquez sur Mettre à jour le mot de passe.",
      "En cas d'erreur côté client (longueur insuffisante, ou les deux nouveaux ne correspondent pas) : un message rouge s'affiche immédiatement, sans appel au serveur.",
      "En cas d'erreur côté serveur (mot de passe actuel incorrect notamment) : un message rouge « Mot de passe actuel incorrect » apparaît après l'envoi.",
    ],
    tips: [
      "Le rôle et le nom complet ne sont modifiables que par un administrateur depuis Administration > Utilisateurs. Vous ne pouvez pas vous auto-promouvoir.",
      "La validation du mot de passe est faite à la fois côté client (longueur, correspondance) et côté serveur (politique de sécurité, vérification du mot de passe actuel).",
      "Pour des raisons de sécurité, l'email associé à votre compte ne peut pas être modifié. Demandez à un administrateur de créer un nouveau compte si nécessaire.",
      "Voir aussi la section Sécurité et sauvegardes pour comprendre la durée de vie de votre session.",
    ],
    panel: {
      summary:
        "Informations du compte (email, nom, rôle) en lecture seule, et changement du mot de passe (12 caractères minimum).",
      hide: ["tips"],
    },
  },
  {
    id: "administration",
    title: "Administration",
    subtitle:
      "Gestion des utilisateurs, des sociétés et des comptes bancaires (réservée aux administrateurs).",
    sees: [
      "Utilisateurs (/administration/utilisateurs) : un formulaire « Créer un utilisateur » (Email, Nom complet, Mot de passe 12 caractères min., Rôle), suivi de la liste des comptes existants avec leur Email, Nom, Rôle, Statut (badge Actif vert ou Inactif gris), date de création, et trois actions par ligne : Éditer, Réinit. mdp, Désactiver.",
      "Sociétés (/administration/societes) : un formulaire de création (raison sociale, SIREN, adresse...) et la liste des entités existantes.",
      "Comptes bancaires (/administration/comptes-bancaires) : un formulaire de création/édition (Société, Nom du compte, IBAN — formaté automatiquement en blocs de 4 chiffres —, BIC, Banque, Code banque, case Actif) et la liste des comptes.",
      "En mode édition d'un utilisateur ou d'un compte, le formulaire bascule en mode « Modifier » avec un bouton Annuler en plus.",
    ],
    does: [
      "Pour créer un utilisateur : remplissez Email, Nom complet (optionnel), Mot de passe initial (12 caractères min.), choisissez un Rôle (Lecture par défaut, ou Administrateur), puis cliquez sur Créer.",
      "Pour modifier un utilisateur : cliquez sur Éditer dans la liste ; le formulaire bascule en mode édition (l'email n'est pas modifiable, c'est précisé sous le champ). Vous pouvez ajuster Nom, Rôle, et la case Utilisateur actif. Cliquez sur Enregistrer ou Annuler.",
      "Pour réinitialiser le mot de passe d'un utilisateur : cliquez sur Réinit. mdp ; une boîte de dialogue dédiée vous demande le nouveau mot de passe à appliquer.",
      "Pour désactiver un utilisateur : cliquez sur Désactiver (visible uniquement si le compte est encore Actif) ; une confirmation est demandée. L'utilisateur reste en base mais ne peut plus se connecter ; pour le réactiver, repassez par Éditer puis cochez Utilisateur actif.",
      "Pour créer une société : remplissez le formulaire de Sociétés et validez.",
      "Pour créer un compte bancaire : choisissez la Société, saisissez l'IBAN (formaté automatiquement par bloc de 4 caractères pendant la saisie), le BIC (optionnel), la Banque, le Code banque, et validez.",
      "Pour modifier un compte bancaire : cliquez sur Éditer ; vous pouvez changer Nom, BIC, Banque, Code banque et statut Actif. La société de rattachement et l'IBAN sont figés après création.",
    ],
    tips: [
      "Seuls les administrateurs voient les pages d'administration. Un utilisateur Lecture ne voit que les groupes Pilotage et Configuration dans la sidebar.",
      "Désactiver un compte bancaire ou une société le fait disparaître des sélecteurs et des nouveaux imports, sans supprimer l'historique associé : les transactions et engagements existants restent intacts.",
      "Un utilisateur Lecture peut consulter toutes les pages non-admin, mais ne peut ni créer ni modifier ni supprimer (les boutons d'action sont masqués ou désactivés selon les pages).",
      "Le rôle Administrateur donne aussi accès au Journal d'audit : voir la section Journal d'audit pour vérifier qui a modifié quoi.",
      "Le mot de passe initial choisi à la création d'un utilisateur doit être communiqué à l'intéressé ; il pourra le changer ensuite depuis sa page Profil.",
    ],
    panel: {
      summary:
        "Gestion des utilisateurs, des sociétés, des comptes bancaires (admins uniquement). Désactiver = invisible mais historique préservé.",
      does: [
        "Créez un utilisateur : Email, Nom, Mot de passe (12 car.), Rôle (Lecture ou Administrateur).",
        "Éditez un utilisateur ou réinitialisez son mot de passe via les boutons de la liste.",
        "Créez ou modifiez une société depuis Sociétés.",
        "Créez un compte bancaire rattaché à une société (IBAN auto-formaté).",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "sauvegardes",
    title: "Sauvegardes",
    subtitle:
      "Supervision et déclenchement manuel des sauvegardes de l'application (réservée aux administrateurs).",
    sees: [
      "Quatre cartes de synthèse en haut de page : Dernier backup réussi (avec sa date relative et la taille DB + Imports), Dernier verify-restore (test de restauration), Dernier échec (vide si aucun problème récent), Espace disque (pourcentage utilisé sur le serveur, seuil d'alerte 85 %).",
      "Un bandeau d'alerte rouge si la situation est anormale : pas de backup réussi depuis plus de 26 heures, pas de test de restauration depuis plus de 8 jours, ou plusieurs échecs récents.",
      "Un tableau Historique listant les 50 dernières opérations : date, type (Automatique, Manuel, Pré-opération, Test restore), statut (En attente, En cours, Réussi, Vérifié, Échec), taille DB, taille Imports, date du dernier verify, résumé. Cliquez sur une ligne pour voir les détails (lignes capturées par table, chemin du fichier dump, hash SHA256, message d'erreur complet le cas échéant).",
      "Deux boutons d'action en haut à droite : Lancer un backup (crée immédiatement une sauvegarde DB + tar des PDF importés) et Tester un restore (restaure le dernier backup dans un container Postgres jetable pour vérifier qu'il est intact).",
      "Un accordéon Aide & dépannage en bas de page avec les questions courantes.",
    ],
    does: [
      "Pour déclencher un backup manuel : cliquez sur Lancer un backup. Une ligne « En attente » apparaît dans le tableau, puis bascule sur « En cours » au bout d'environ 2 secondes, puis « Réussi » au bout de quelques secondes. La page se rafraîchit automatiquement (toutes les 3 secondes pendant qu'une opération tourne, 30 secondes sinon).",
      "Pour tester qu'un backup est restaurable : cliquez sur Tester un restore. Le dernier backup réussi est restauré dans un container Postgres éphémère, les comptages de lignes sont vérifiés, puis le container est détruit. Aucun impact sur la production.",
      "Pour rafraîchir manuellement la liste : cliquez sur Rafraîchir.",
      "Pour consulter le détail d'une opération (notamment en cas d'échec) : cliquez sur la ligne correspondante du tableau.",
    ],
    tips: [
      "Une seule opération à la fois est autorisée : les boutons Lancer un backup et Tester un restore sont désactivés tant qu'une opération est En attente ou En cours, pour éviter de saturer le serveur. Le tooltip indique pourquoi.",
      "Le backup automatique tourne tous les jours à 2h du matin (heure du serveur). Le test de restauration automatique tourne tous les dimanches à 4h. Les deux sont indépendants des opérations manuelles.",
      "Le verify-restore prouve qu'un backup est techniquement restaurable : c'est ce qui distingue Horizon d'une simple sauvegarde « espérons que ça marche ».",
      "Les sauvegardes sont conservées localement 30 jours, avec rotation automatique des plus anciennes.",
      "Voir aussi la section Sécurité et sauvegardes pour la stratégie globale, et le Journal d'audit pour l'historique général des modifications.",
    ],
    panel: {
      summary:
        "Supervision des sauvegardes (admins). Déclenchement manuel d'un backup ou d'un test de restauration. Une seule opération à la fois.",
      does: [
        "Cliquez sur Lancer un backup pour créer une sauvegarde immédiate.",
        "Cliquez sur Tester un restore pour vérifier que le dernier backup est restaurable.",
        "Cliquez sur une ligne du tableau pour voir les détails (notamment en cas d'échec).",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "audit",
    title: "Journal d'audit",
    subtitle:
      "Trace historique de toutes les mutations finance-sensibles (réservée aux administrateurs).",
    sees: [
      "Une table paginée listant chaque mutation : création, modification ou suppression sur les données critiques — utilisateurs, sociétés, comptes bancaires, transactions, engagements, tiers, règles de catégorisation, scénarios et lignes prévisionnelles.",
      "Pour chaque événement : horodatage précis (date + heure + secondes), utilisateur auteur, IP source, action (badge create / update / delete avec un code couleur), type d'entité, identifiant interne, et un résumé des champs modifiés (« champ : avant → après »).",
      "Des filtres en haut de page : type d'entité, action (create/update/delete), utilisateur, période.",
      "Au clic sur une ligne : un panneau de détail (drawer) qui expose les JSON complets — état avant, état après, et diff champ par champ, en mono-espacé pour la lisibilité.",
    ],
    does: [
      "Pour ouvrir le journal : groupe Administration de la sidebar, lien Journal d'audit. La page est accessible via /administration/audit.",
      "Pour cibler une catégorie d'événements : utilisez le filtre Type d'entité (par ex. Transaction, Commitment, User) puis le filtre Action.",
      "Pour identifier qui a fait une modification donnée : filtrez par utilisateur, ou trouvez la ligne dans la table puis lisez la colonne Auteur.",
      "Pour reconstituer un changement problématique : ouvrez la ligne, lisez le diff champ par champ ou comparez les JSON avant / après.",
    ],
    tips: [
      "Les mots de passe et secrets sont toujours masqués (« <redacted> ») dans les snapshots : aucune donnée sensible n'est exposée dans le journal, même pour un administrateur.",
      "Les lectures (consultations, GET) ne sont pas tracées, seulement les mutations (create/update/delete). Impossible donc de savoir qui a simplement consulté une donnée — c'est volontaire (volume et bruit).",
      "Les imports massifs (par exemple 500 transactions créées d'un coup) ne génèrent qu'une seule entrée d'audit résumée, pas une par transaction. Vous gardez la traçabilité globale sans noyer le journal.",
      "La rétention par défaut est de 365 jours : les événements plus anciens peuvent être purgés via un endpoint admin dédié (intervention technique).",
      "Voir aussi la section Sécurité et sauvegardes pour la stratégie globale de protection des données.",
    ],
    panel: {
      summary:
        "Trace de toutes les mutations finance-sensibles. Filtres par entité, action, utilisateur et période ; diff complet sur clic.",
      does: [
        "Filtrez par type d'entité, action, utilisateur, période.",
        "Cliquez sur une ligne pour ouvrir le détail (avant / après / diff JSON).",
        "Lisez la colonne Auteur pour identifier qui a fait quoi.",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "securite",
    title: "Sécurité et sauvegardes",
    subtitle: "Comment vos données sont protégées, sauvegardées et restaurables.",
    sees: [
      "Une politique de sauvegarde automatique : un dump complet de la base PostgreSQL est exécuté chaque nuit à 2h du matin (heure du serveur).",
      "Une rotation locale : les sauvegardes sont conservées sur le serveur avec une rotation pour limiter l'espace disque.",
      "Une page d'administration dédiée Sauvegardes (groupe Administration de la sidebar, réservée aux administrateurs) qui liste les sauvegardes disponibles avec leurs métadonnées (date, taille, statut, hash) et permet de déclencher manuellement un backup ou un test de restauration.",
      "Des en-têtes HTTP de sécurité renforcés appliqués par nginx : HSTS (force HTTPS), X-Frame-Options (anti-clickjacking), X-Content-Type-Options, Referrer-Policy, Permissions-Policy.",
    ],
    does: [
      "Pour vérifier la santé des sauvegardes : un administrateur ouvre la page Sauvegardes (groupe Administration) et lit les 4 cartes en haut. Si la dernière sauvegarde réussie a plus de 26h ou que le dernier test de restauration a plus de 8 jours, un bandeau rouge s'affiche.",
      "Pour déclencher une restauration en cas d'incident : demandez à l'administrateur technique. La restauration se fait à partir du dump le plus récent (perte maximale = activité depuis le dernier snapshot nocturne).",
      "Pour réagir à une compromission soupçonnée de votre compte : changez immédiatement votre mot de passe depuis la page Profil, puis prévenez un administrateur qui pourra forcer une invalidation des sessions actives si nécessaire.",
    ],
    tips: [
      "Les sessions reposent sur un cookie HTTP-only : il ne peut pas être lu depuis du JavaScript exécuté dans le navigateur, ce qui bloque les attaques XSS classiques.",
      "Les PDF importés sont stockés à part pour permettre la prévisualisation, et ne sont jamais accessibles en dehors d'une session authentifiée.",
      "Une restauration de la base écrase l'état actuel : c'est une opération irréversible côté production. Toute modification faite depuis le dernier snapshot est perdue.",
      "L'audit (voir section Journal d'audit) couvre les mutations métier ; les sauvegardes couvrent l'intégralité des données. Les deux sont complémentaires.",
      "Voir aussi la section Profil pour le changement de mot de passe, et Journal d'audit pour la traçabilité.",
    ],
    panel: {
      summary:
        "Sauvegarde nocturne automatique de la base, en-têtes HTTP de sécurité renforcés, sessions par cookie HTTP-only.",
      does: [
        "Vérifiez régulièrement la page Sauvegardes (groupe Administration) pour la santé des snapshots.",
        "Lancez un test de restore régulièrement depuis la page Sauvegardes pour vous assurer qu'un backup est exploitable.",
        "Changez votre mot de passe depuis Profil au moindre doute.",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "lexique",
    title: "Lexique des sigles",
    subtitle:
      "Glossaire des termes techniques et financiers utilisés dans l'application.",
    sees: [
      "Cette section regroupe les sigles et acronymes que vous pouvez croiser dans l'application, classés par catégorie. Quand un sigle est utilisé dans une page, il est suivi de sa traduction française entre parenthèses (ex. « Autonomie de trésorerie (Runway) »).",
    ],
    does: [
      "Termes financiers — Runway (autonomie de trésorerie) : nombre de mois pendant lesquels la société peut tenir à son rythme actuel de consommation de cash. Burn rate (consommation mensuelle) : différence moyenne entre les sorties et les entrées de cash sur la période récente. YoY (Year over Year, année sur année) : comparaison d'un indicateur entre l'année courante et la même période l'année précédente. KPI (Key Performance Indicator, indicateur clé de performance) : chiffre synthétique mesurant la santé d'un aspect de l'activité.",
      "Concentration et risque — HHI (Herfindahl-Hirschman Index, indice de concentration de Herfindahl-Hirschman) : somme des carrés des parts de marché. Varie de 0 (parfaitement diversifié) à 10 000 (un seul acteur). Repères : moins de 1500 = concentration faible, 1500 à 2500 = modérée, plus de 2500 = forte (seuil d'alerte antitrust américain).",
      "Identifiants bancaires — IBAN (International Bank Account Number, numéro de compte bancaire international) : identifiant standardisé d'un compte bancaire. BIC (Bank Identifier Code, code identifiant bancaire) : identifie l'établissement bancaire à l'échelle internationale. SIREN (Système d'Identification du Répertoire des Entreprises) : identifiant à 9 chiffres d'une entreprise française. SIRET (Système d'Identification du Répertoire des Établissements) : identifiant à 14 chiffres d'un établissement (SIREN + 5 chiffres NIC).",
      "Technique — SHA256 : empreinte cryptographique de 64 caractères qui prouve qu'un fichier n'a pas été modifié. RGPD (Règlement Général sur la Protection des Données) : réglementation européenne sur la confidentialité des données personnelles. HTTP (HyperText Transfer Protocol) / HTTPS (HTTP Secure) : protocoles de communication web, le second chiffré.",
    ],
    tips: [
      "Si vous croisez un terme non listé ici, signalez-le à un administrateur — il sera ajouté au lexique pour les autres utilisateurs.",
      "Les acronymes anglais conservés (Runway, Burn rate, YoY, HHI) sont des standards de la finance d'entreprise : les rapports d'audit, les analystes financiers et les outils tiers (Agicap, Pennylane, etc.) utilisent les mêmes termes. Connaître la version anglaise vous évite d'être perdu dans ces contextes.",
    ],
    panel: {
      summary:
        "Glossaire des sigles utilisés dans l'application (financiers, bancaires, techniques).",
      hide: ["tips"],
    },
  },
];
