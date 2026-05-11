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

/**
 * Documentation d'impact pour une action UI à effet (création, modification,
 * suppression d'état, déclenchement de workflow). Voir CLAUDE.md → section
 * "Documentation d'impact obligatoire".
 */
export type FeatureDoc = {
  id: string;
  title: string;
  whatItDoes: string;
  whatItChanges: string[];
  whatItDoesNotChange: string[];
  whenToUse: string[];
};

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
      "Une barre latérale sombre à gauche, organisée en trois groupes : Pilotage (Tableau de bord, Analyse, Prévisionnel, Transactions, Imports), Configuration (Engagements, Tiers, Règles), Administration (Utilisateurs, Sociétés, Comptes bancaires, Catégories, Sauvegardes, Journal d'audit).",
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
      "Six widgets KPI pour détecter dérives, tendances et concentrations sur les mois disponibles.",
    sees: [
      "Autonomie de trésorerie (Runway) : nombre de mois pendant lesquels la société peut tenir si elle continue à dépenser au rythme actuel. Phrase d'interprétation contextuelle (Stable / Vigilance / Critique), consommation mensuelle (Burn rate), trésorerie disponible aujourd'hui, courbe projetée sur 6 mois.",
      "Besoin en fonds de roulement (BFR) : trois métriques combinées — DSO (délai moyen de paiement client), DPO (délai moyen de paiement fournisseur), BFR (créances clients à encaisser moins dettes fournisseurs à payer). Le widget reste vide tant qu'aucun engagement n'a été saisi sur la page Engagements.",
      "Précision du prévisionnel : tableau des 6 derniers mois comparant le prévu (saisi sur la page Prévisionnel) au réalisé (transactions importées). L'écart est coloré (vert si fiable, ambre si attention, rouge si écart fort). Ce widget reste vide tant qu'aucune prévision n'a été saisie.",
      "Dérives par catégorie : tableau qui compare le mois précédent (M-1, dernier mois complet) à la moyenne des trois mois antérieurs (M-2 à M-4). Le mois en cours est volontairement exclu, car les relevés bancaires sont importés une fois le mois terminé : son inclusion fausserait la comparaison. Un badge « Dérive » apparaît au-delà de 20 % d'écart. Cliquez sur une ligne pour voir les transactions de M-1 qui expliquent l'écart.",
      "Top mouvements : catégories en plus forte hausse et plus forte baisse sur les trois derniers mois, avec une mini-courbe (sparkline) pour visualiser la trajectoire. Les libellés longs sont affichés en entier (passez la souris pour le tooltip).",
      "Concentration clients : part du top 5 dans le chiffre d'affaires, indice HHI (Herfindahl-Hirschman, mesure standard de la concentration) et niveau de risque (faible, moyen, élevé).",
      "Tendance mensuelle (MoM 6 mois) : graphique barres + ligne affichant encaissements, décaissements et net sur les 6 derniers mois complets avant le dernier import. La variation mensuelle en % est lisible au survol de chaque barre. Si moins de 6 mois de data sont disponibles, le graphique affiche les mois existants avec un avertissement.",
      "Comparaison des sociétés : pour chaque entité accessible, revenus, dépenses, variation nette, solde, consommation mensuelle et autonomie.",
      "En bas de page : un accordéon Lexique des sigles (Runway, Burn rate, MoM, HHI, DSO, DPO, BFR) explicitant chaque terme financier utilisé.",
    ],
    does: [
      "L'analyse se fait toujours sur une société à la fois : à votre arrivée, la première société accessible est sélectionnée automatiquement (ordre alphabétique). Pour basculer sur une autre société, utilisez l'EntitySelector en haut à droite. La page n'a pas de mode « Toutes les sociétés » car un agrégat cross-entité n'a pas de sens financier (chaque société a son propre business et ses propres tendances).",
      "Pour ajuster visuellement la période d'en-tête : utilisez le PeriodSelector. Attention : chaque widget garde son propre horizon métier (mois courant, 3 mois, 6 mois, 12 mois) ; le PeriodSelector ici n'a qu'un rôle de cohérence visuelle avec les autres pages.",
      "Pour identifier en un coup d'œil les postes qui décalent votre résultat : lisez la colonne « Dérive » du tableau Dérives par catégorie, puis le widget Top mouvements pour confirmer la tendance.",
      "Pour évaluer un risque commercial : ouvrez Concentration clients ; un indice HHI supérieur à 2500 signale une dépendance forte à quelques clients (le marché américain considère 2500 comme le seuil d'alerte antitrust).",
      "Pour comparer vos sociétés entre elles : descendez jusqu'au tableau Comparaison des sociétés (masqué si vous n'avez accès qu'à une seule entité).",
      "Pour exporter les données d'un widget : utilisez les boutons 'Exporter CSV' placés sous chaque tableau (Dérives par catégorie, Top mouvements, MoM). Le fichier CSV est téléchargé avec les données filtrées sur la société sélectionnée.",
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
        "Indicateurs clés (par société, sélection auto de la 1ère accessible) : autonomie (Runway), BFR (DSO/DPO), précision du prévisionnel, dérives par catégorie avec drill-down, top mouvements, concentration clients, MoM 6 mois, comparaison entre sociétés.",
      does: [
        "Choisissez la société analysée dans l'EntitySelector (la première accessible est pré-sélectionnée).",
        "Cliquez une ligne du tableau Dérives pour voir les transactions de M-1 qui l'expliquent.",
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
      "Pour saisir une entrée prévisionnelle : cliquez sur n'importe quelle cellule du pivot. Le tiroir d'édition s'ouvre à droite, pré-rempli sur le mois et la catégorie cliqués. Choisissez la méthode de calcul : Récurrent à montant fixe (un montant qui se répète chaque mois), Montant ponctuel — un seul mois (un montant fixe qui ne s'applique qu'au mois choisi, ex : encaissement client exceptionnel en juillet), Moyenne 3/6/12 mois, Mois précédent, Même mois l'année précédente, Basé sur une autre catégorie (% d'une catégorie tierce), ou Formule personnalisée.",
      "Pour pré-remplir une ligne depuis un flux récurrent détecté : dans le tiroir d'édition (onglet Prévisionnel), cliquez sur le bouton Suggérer depuis l'historique. Horizon analyse les 6 derniers mois de transactions et propose les contreparties dont le rythme est régulier (mensuel, hebdomadaire, trimestriel). Sélectionnez une suggestion pour pré-remplir la méthode Récurrent à montant fixe avec le montant médian calculé. Vous pouvez ajuster le montant avant d'enregistrer.",
      "Pour ajuster la fenêtre temporelle : utilisez le PeriodSelector en haut à droite, en granularité mois (presets : 12 m, Année, Mois-1, Perso.).",
      "Pour fermer le tiroir d'édition sans enregistrer : cliquez en dehors ou utilisez le bouton Annuler du tiroir.",
      "Pour supprimer une entrée prévisionnelle existante : ouvrez le tiroir sur la cellule concernée (la ligne actuelle est pré-chargée), puis cliquez sur Supprimer la ligne en bas à gauche du formulaire. Une confirmation est demandée. La cellule retombera sur le calcul par défaut (souvent 0) tant qu'aucune autre méthode n'est définie pour cette catégorie.",
      "Pour exporter le tableau pivot : cliquez sur le bouton 'Exporter le pivot CSV' placé sous le tableau. Le fichier contient toutes les colonnes catégorie × mois (réalisé, engagé, prévisionnel) pour le scénario et la période sélectionnés.",
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
        "Cliquez sur Suggérer depuis l'historique (onglet Prévisionnel du tiroir) pour détecter les flux récurrents et pré-remplir automatiquement la ligne.",
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
      "Une barre de filtres : un champ de recherche plein texte (placeholder « Rechercher par libellé, tiers, montant... »), un PeriodSelector, un filtre par catégorie (combobox arborescente avec bouton croix pour le retirer), deux champs numériques « Montant min (€) » et « Montant max (€) », un toggle « Afficher les virements SEPA détaillés », et à droite un toggle « Non catégorisées uniquement ».",
      "Un bandeau ambre en haut de page lorsqu'Horizon détecte que vous avez catégorisé manuellement le même libellé au moins 3 fois dans les 30 derniers jours. Le bandeau propose de créer une règle automatique via le bouton « Créer une règle » ou d'ignorer la suggestion pour la session via « Plus tard ».",
      "Un tableau avec : case à cocher, date, société (uniquement en vue consolidée), Tiers / Libellé (le tiers s'il est connu, sinon le libellé brut), Catégorie (badge gris si catégorisée, badge orange « Non catégorisée » sinon), Montant (vert avec « + » pour les crédits, rouge pour les débits).",
      "Une case à cocher en en-tête pour tout sélectionner sur la page.",
      "Quand vous cochez une ou plusieurs opérations, deux choses apparaissent : un mini-bandeau vert juste sous les filtres (« N opération(s) sélectionnée(s) · Désélectionner ») et un panneau latéral droit qui s'ouvre automatiquement avec les actions de catégorisation. Vous gardez votre position dans la liste pendant que vous agissez (plus besoin de remonter en haut de la page).",
      "Quand toutes les transactions de la page sont cochées et qu'il y a d'autres résultats hors page, un lien « Sélectionner les X résultats correspondant aux filtres actuels » apparaît dans le mini-bandeau vert. Le cliquer active le mode de catégorisation sur l'ensemble du résultat filtré.",
      "Un pied de tableau avec une pagination complète : récapitulatif (« Affichage 51 à 100 sur 1234 · Page 2 sur 25 »), sélecteur Lignes (25 / 50 / 100 / 200), boutons « (première), ‹ (précédente), numéros de page directement cliquables avec ellipsis intelligente, › (suivante), » (dernière). Au-delà de 5 pages, un champ Aller à : permet de saisir un numéro et valider avec Entrée.",
    ],
    does: [
      "Pour rechercher une opération : saisissez un fragment de libellé, un nom de tiers ou un montant exact dans le champ de recherche (ex. : tapez « 500 » pour ne voir que les opérations contenant ce montant, ou « URSSAF » pour cibler un tiers).",
      "Pour filtrer par montant : renseignez un ou deux champs « Montant min (€) » / « Montant max (€) » dans la barre de filtres. Le filtre s'applique sur la valeur absolue du montant (un filtre Montant min = 1000 isole toutes les opérations supérieures à 1 000 €, qu'il s'agisse d'encaissements ou de décaissements).",
      "Pour catégoriser plusieurs opérations en masse : 1. Cochez les lignes concernées (ou la case d'en-tête pour toute la page). Le panneau latéral droit s'ouvre automatiquement. 2. Choisissez une catégorie dans la combobox du panneau. 3. Cliquez sur Catégoriser. Les opérations sont mises à jour, la sélection vidée et le panneau se referme.",
      "Pour catégoriser toutes les transactions d'un filtre en une seule action (sans limites de page) : sélectionnez toutes les transactions de la page courante avec la case d'en-tête, puis cliquez sur le lien « Sélectionner les X résultats correspondant aux filtres actuels » qui apparaît dans le mini-bandeau vert. Le drawer de catégorisation s'applique alors à l'ensemble du résultat filtré via un appel unique au serveur.",
      "Pour transformer la sélection en règle automatique : dans le même panneau, cliquez sur Suggérer une règle. Horizon analyse les libellés communs et ouvre le formulaire de création de règle pré-rempli (opérateur de libellé, valeur, sens, compte, catégorie).",
      "Pour vider la sélection sans agir : cliquez sur Désélectionner (visible dans le mini-bandeau vert ou dans le panneau).",
      "Si vous fermez le panneau de catégorisation avec une sélection encore active, un bouton Rouvrir le panneau apparaît dans le mini-bandeau vert pour le ré-afficher.",
      "Pour ne voir que les opérations à traiter : activez le toggle « Non catégorisées uniquement ». Toggle désactivé = liste complète.",
      "Pour afficher les sous-transactions SEPA : cochez le toggle « Afficher les virements SEPA détaillés » dans la barre de filtres. Par défaut, seules les lignes agrégées sont affichées. Quand le toggle est activé, les lignes enfants (sous-virements d'un virement SEPA de masse) apparaissent également.",
      "Pour isoler une catégorie : choisissez-la dans le filtre catégorie de la barre. Cliquez sur la croix à droite pour retirer le filtre. Pratique pour vérifier d'un coup toutes les opérations d'une catégorie (ex. : toutes les TVA, toute la masse salariale).",
      "Pour créer une règle depuis la suggestion automatique : si un bandeau ambre apparaît en haut de la page, cliquez sur « Créer une règle ». Le formulaire de règle s'ouvre pré-rempli avec le libellé et la catégorie détectés. Cliquez sur « Plus tard » pour ignorer la suggestion jusqu'au prochain rechargement de page.",
      "Pour naviguer rapidement dans la liste : la barre de pagination en bas du tableau propose plusieurs raccourcis. Cliquez directement sur un numéro de page, ou utilisez « (début), ‹ (précédente), › (suivante), » (fin). Au-delà de 5 pages, le champ Aller à : permet de sauter à une page précise (validez avec Entrée).",
      "Pour afficher plus de transactions par écran : changez le sélecteur Lignes : (25 / 50 / 100 / 200) dans la barre de pagination. À 200, vous parcourez plus vite un gros volume sans recharger.",
      "Pour exporter la liste des transactions filtrées : cliquez sur le bouton 'Exporter CSV' en haut à droite. Toutes les lignes correspondant aux filtres actifs (société, période, catégorie, montant, etc.) sont exportées, quelle que soit la page affichée. Le fichier CSV est encodé UTF-8 avec BOM pour Excel et utilise le point-virgule comme séparateur.",
    ],
    tips: [
      "Les filtres actifs sont mémorisés dans l'URL de la page. Vous pouvez copier-coller l'URL pour partager une vue filtrée avec un collègue, ou retrouver votre contexte après un rechargement de page.",
      "Les filtres Montant min et Montant max s'appliquent sur la valeur absolue du montant. Un filtre Montant min = 1000 isole toutes les opérations de plus de 1 000 €, quel que soit le sens (encaissement ou décaissement).",
      "Par défaut, les virements SEPA agrégés et leurs sous-transactions ne s'affichent pas simultanément. Activez le toggle « Afficher les virements SEPA détaillés » uniquement si vous souhaitez explorer la décomposition d'un virement de masse.",
      "Les opérations agrégées (lignes parents qui regroupent plusieurs sous-écritures) apparaissent sur fond gris plus dense pour les distinguer des lignes unitaires.",
      "Une opération sans catégorie porte un badge ambre « Non catégorisée » très visible : c'est ce qui alimente le KPI du Tableau de bord.",
      "Le panneau latéral de catégorisation ne s'affiche que s'il y a au moins une sélection. Le bouton Appliquer y reste désactivé tant qu'aucune catégorie n'a été choisie.",
      "La combobox catégorie du panneau s'adapte automatiquement au sens des opérations sélectionnées : si toutes ont un montant positif (encaissements), seules les sous-catégories d'« Encaissements » et les racines neutres (Flux financiers, Autres, Non catégorisées) sont proposées. Si toutes sont négatives (décaissements), la racine « Encaissements » est masquée. En cas de sélection mixte, toutes les catégories restent disponibles. Un badge en haut du panneau (Encaissements uniquement / Décaissements uniquement / Sélection mixte) rappelle ce filtrage.",
      "Si Suggérer une règle échoue (ex. : libellés trop hétérogènes), un message rouge s'affiche dans le panneau : ajustez la sélection puis recommencez.",
      "Les filtres et la pagination se réinitialisent à la page 1 dès que vous changez un filtre, pour éviter d'afficher une page vide.",
      "Voir aussi la section Règles de catégorisation pour automatiser durablement le travail de catégorisation, et la section Imports pour comprendre d'où viennent ces opérations.",
    ],
    panel: {
      summary:
        "Liste paginée des opérations bancaires. Filtres (montant, SEPA, catégorie, période), recherche, sélection multiple, catégorisation en masse, suggestion de règle. Filtres persistés dans l'URL.",
      does: [
        "Recherchez par libellé, tiers ou montant dans la barre de filtres.",
        "Filtrez par Montant min / Montant max (valeur absolue) pour isoler les grosses ou petites opérations.",
        "Cochez les lignes : un panneau s'ouvre à droite avec la combobox catégorie + bouton Catégoriser.",
        "Pour catégoriser tous les résultats d'un filtre : sélectionnez toute la page, puis cliquez sur le lien « Sélectionner les X résultats ».",
        "Cliquez sur Suggérer une règle (dans le panneau) pour automatiser une catégorisation récurrente.",
        "Activez « Non catégorisées uniquement » pour vous concentrer sur les lignes à traiter.",
        "Activez « Afficher les virements SEPA détaillés » pour voir les sous-transactions d'un virement de masse.",
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
    title: "À encaisser / À payer",
    subtitle:
      "Saisis ici les factures que tu attends ou que tu dois payer. Elles alimentent ton prévisionnel de trésorerie et tes indicateurs DSO/DPO.",
    sees: [
      "Un bandeau d'introduction permanent qui rappelle l'objet de la page : tu saisis ici les factures attendues ou à payer, elles alimentent le prévisionnel et les indicateurs BFR/DSO/DPO, et l'appariement avec une transaction réelle bascule automatiquement l'engagement en Payé.",
      "Trois onglets en haut : À encaisser (factures que tu attends de tes clients, direction in), À payer (factures que tu dois à tes fournisseurs, direction out), Tout (vue mixte des deux).",
      "Sous les onglets, des cards KPI : Sous 30 jours (montant cumulé des engagements pending dont la date prévue tombe dans les 30 prochains jours), En retard (montant) (somme des engagements pending dont la date prévue est passée), En retard (nombre) (combien de lignes en retard). Sur l'onglet Tout, ces cards sont dupliquées en deux blocs (À encaisser puis À payer) pour comparer les deux côtés d'un coup d'œil.",
      "Un bandeau jaune d'alerte fantômes apparaît au-dessus du tableau quand au moins une ligne est en retard de plus de 7 jours sans transaction associée. Deux actions : Voir la liste (filtre la table aux fantômes seulement) et Tout clôturer (action en masse, demande confirmation puis bascule toutes les lignes fantômes en Annulé).",
      "Un tableau avec : Statut (badge En attente / Payé / Annulé, complété d'un badge En retard rouge quand la date prévue est passée et que l'engagement est encore pending), Tiers, Catégorie, Date prévue, Montant, Référence, Tx matchée (cliquable quand l'engagement est apparié), Actions. Sur l'onglet Tout, une colonne supplémentaire Sens distingue les pastilles À encaisser (verte) et À payer (rose).",
      "Sur chaque ligne pending : trois boutons Matcher, Modifier, Clôturer. Sur une ligne Annulée : un bouton Réactiver. Sur une ligne Payée : la référence de la transaction appariée (Tx #...).",
      "Le tableau est trié par défaut avec les lignes En retard en haut (badges rouges immédiatement visibles), puis par date prévue croissante.",
      "Le dialog de matching manuel (clic sur Matcher) liste les transactions candidates avec, pour chacune, un Score 0-100 et la décomposition (écart de montant en €, écart de date en jours, bonus +20 si le tiers correspond). Les candidats de score ≥ 80 sont mis en évidence par une bordure verte à gauche : c'est le seuil au-delà duquel le matching est automatique à l'import.",
    ],
    does: [
      "Pour créer un engagement : clique sur Nouvel engagement en haut à droite. Le formulaire demande la société (en création uniquement), le sens (À encaisser ou À payer), le montant, la référence, la date d'émission, la date prévue, le tiers, la catégorie et une description libre.",
      "Pour modifier un engagement : clique sur Modifier sur la ligne ; le même formulaire s'ouvre pré-rempli (la société n'est pas modifiable a posteriori).",
      "Pour apparier manuellement un engagement à une transaction réelle : clique sur Matcher. Le dialog liste les transactions candidates classées par score décroissant. Clique sur Lier en face de la bonne ; l'engagement passe en Payé et sort du prévisionnel.",
      "Pour clôturer un engagement (anciennement Annuler) : clique sur Clôturer sur la ligne. Une confirmation est demandée. L'engagement bascule en Annulé, il sort du prévisionnel et des indicateurs DSO/DPO. C'est le geste à utiliser pour les fantômes ou les factures finalement non émises.",
      "Pour clôturer plusieurs fantômes en une fois : quand le bandeau jaune est présent, clique sur Tout clôturer. Une confirmation rappelle l'effet exact ; à validation, toutes les lignes fantômes du périmètre courant (entité + onglet) basculent en Annulé en une seule opération.",
      "Pour ne voir que les fantômes : depuis le bandeau jaune, clique sur Voir la liste. Le tableau se restreint aux lignes fantômes ; un bouton Voir tout permet de revenir à la liste complète.",
      "Pour réactiver un engagement clôturé : depuis l'onglet Tout, repère la ligne en statut Annulé et clique sur Réactiver pour la repasser en pending.",
      "Pour basculer entre direction : utilise les onglets À encaisser / À payer / Tout. Les KPI et le tableau se mettent à jour ensemble.",
    ],
    tips: [
      "L'appariement automatique tourne à chaque import bancaire. Une transaction est liée à un engagement quand un seul candidat dépasse le score 80 et qu'il est strictement le meilleur. En dessous de ce seuil, ou en cas d'ex-aequo, l'engagement reste pending et tu choisis manuellement via Matcher.",
      "Le score combine l'écart de montant (en €), l'écart de date (en jours) et un bonus +20 si le tiers de l'engagement correspond à celui de la transaction. La décomposition est visible dans le dialog de matching pour comprendre pourquoi un candidat est en tête.",
      "Un engagement pending dont la date prévue est passée de plus de 7 jours sans transaction associée est qualifié de fantôme. Soit la facture a été payée mais la transaction n'a pas été correctement appariée (utilise Matcher), soit la facture ne sera jamais émise/payée (utilise Clôturer ou Tout clôturer pour la sortir du prévisionnel).",
      "Clôturer est réversible : un engagement Annulé peut être réactivé à tout moment depuis l'onglet Tout, ligne par ligne. La suppression définitive n'existe pas — l'historique audit est préservé.",
      "Le badge En retard rouge n'est affiché que pour les lignes pending dont la date prévue est strictement antérieure à aujourd'hui. Une ligne payée ou clôturée ne porte jamais ce badge, même si elle a été réglée tardivement.",
      "Voir aussi la section Clients & fournisseurs pour valider les tiers utilisés ici, et la section Prévisionnel qui agrège ces engagements dans le pivot mensuel.",
    ],
    panel: {
      summary:
        "Factures attendues (À encaisser) ou à payer (À payer). Trois onglets, KPI 30 jours / retards / fantômes, badge En retard rouge, bandeau d'alerte fantômes avec action Tout clôturer en masse, dialog de matching avec score visible.",
      does: [
        "Crée un engagement via Nouvel engagement (sens, montant, dates, tiers, catégorie).",
        "Apparie manuellement via Matcher : le dialog affiche le score (0-100) et sa décomposition.",
        "Clôture un engagement (Clôturer) ou tous les fantômes d'un coup (Tout clôturer dans le bandeau jaune).",
        "Réactive un engagement clôturé via Réactiver depuis l'onglet Tout.",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "tiers",
    title: "Clients & fournisseurs",
    subtitle:
      "Annuaire des tiers (clients, fournisseurs, salariés, organismes) détectés à partir de tes imports bancaires. Renommage, fusion de doublons, filtrage des bruits.",
    sees: [
      "Un bandeau bleuté qui rappelle l'objet de la page : « Cette page liste tous les tiers détectés à partir de tes imports bancaires. ».",
      "En haut à droite : le sélecteur de société (EntitySelector) et un bouton Nouveau tiers.",
      "Une barre de recherche libre et une case à cocher Inclure les tiers ignorés.",
      "Un tableau avec sept colonnes : Nom (cliquable, ouvre la liste des transactions du tiers), Volume cumulé (somme des |montants| en EUR), # Tx (nombre de transactions), Dernière opé (date la plus récente), Engagts en cours (nombre d'engagements pending), Statut (badge Actif vert ou Ignoré ambré), Actions.",
      "Sur chaque ligne, dans Actions : Renommer (édition inline), Fusionner… (ouvre le dialog), Ignorer ou Réactiver selon le statut courant.",
      "Le tableau est trié par défaut par volume décroissant : les tiers à plus fort enjeu remontent en haut.",
    ],
    does: [
      "Pour rechercher un tiers : tapez une fraction de nom dans la barre, le filtrage est immédiat (côté serveur, ILIKE).",
      "Pour inclure les tiers ignorés dans la liste : cochez Inclure les tiers ignorés (par défaut décochée).",
      "Pour ouvrir la liste des transactions d'un tiers : cliquez sur son nom (lien vers la page Transactions filtrée).",
      "Pour renommer un tiers : cliquez sur Renommer, modifiez le nom, validez par Entrée ou cliquez ailleurs (Échap pour annuler). Le nouveau nom s'applique partout (transactions liées, engagements, règles).",
      "Pour fusionner deux tiers : cliquez sur Fusionner… sur la ligne du tiers source. Choisissez le tiers cible dans la liste déroulante (les candidats sont les autres tiers de la même société). Une preview détaille les éléments réattachés (transactions, engagements, règles, lignes de prévisionnel). Cliquez sur Confirmer la fusion. Le tiers source est supprimé.",
      "Pour ignorer un tiers : cliquez sur Ignorer. Une confirmation rappelle l'effet exact. Le tiers reste en base mais disparaît des sélecteurs et des prédictions de récurrence.",
      "Pour réactiver un tiers ignoré : cochez Inclure les tiers ignorés, puis cliquez sur Réactiver sur la ligne.",
      "Pour créer un tiers manuellement : cliquez sur Nouveau tiers, saisissez un nom, validez. Utile pour préparer un client/fournisseur avant le premier import.",
    ],
    tips: [
      "Les tiers sont créés automatiquement à chaque import bancaire. Le matching utilise un fuzzy (token_set_ratio ≥ 90 %) sur le nom normalisé : un tiers existant est réutilisé même s'il était Ignoré (statut préservé), ce qui évite les doublons silencieux.",
      "Fusionner est irréversible : tout est réattaché atomiquement vers la cible (47 transactions + 3 engagements + 2 règles passent en une opération), puis le tiers source est supprimé. Une entrée audit dédiée action=merge est posée dans le journal.",
      "Ignorer ne supprime PAS les transactions liées. Elles restent visibles dans la page Transactions et comptent toujours dans le dashboard, l'analyse, les indicateurs financiers.",
      "Le statut Actif/Ignoré n'influence ni la catégorisation par règles, ni le matching d'engagement.",
      "Un libellé bancaire pourri non récurrent qui pollue les sélecteurs est typiquement un candidat à Ignorer. Pour un fournisseur récurrent mal nommé, préfère Renommer.",
    ],
    panel: {
      summary:
        "Annuaire des tiers détectés. Renomme, fusionne les doublons, ignore les bruits. Volume / nb tx / dernière opé / engagts en cours visibles dans le tableau.",
      does: [
        "Renommer un tiers (inline, propage partout).",
        "Fusionner deux tiers (réattache transactions, engagements, règles, prévisionnel — irréversible).",
        "Ignorer / Réactiver (le tiers reste en base, sort/entre dans les sélecteurs).",
        "Créer un tiers manuellement via Nouveau tiers (utile avant un premier import).",
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
      "Pour créer une règle : cliquez sur Nouvelle règle. Un tiroir s'ouvre avec : Nom, Priorité (par défaut 5000), Scope (Globale ou société précise), Sens (Tous / Crédits uniquement / Débits uniquement), Filtre libellé (opérateur contient / commence par / finit par / égal à + valeur), Filtre montant en € (égal / différent / supérieur / inférieur / entre — montant comparé en valeur absolue, signe ignoré), Tiers (counterparty cible — facultatif), Compte bancaire (facultatif, restreint aux comptes de la société sélectionnée), Catégorie cible. Au moins un filtre (libellé, montant, sens, tiers ou compte) est requis.",
      "Pour tester une règle avant de la créer : l'aperçu se met à jour automatiquement (délai de 0,5 secondes) dès que vous modifiez un filtre. Vous pouvez aussi cliquer sur le bouton Aperçu pour forcer un rafraîchissement immédiat. Un tableau s'affiche avec les transactions concrètes qui seraient capturées (date, libellé complet, montant signé en couleur), trié par date décroissante, limité aux 20 plus récentes si la règle matche plus.",
      "Pour cibler plusieurs libellés différents avec une seule règle : séparez-les par une virgule dans le champ valeur du filtre libellé. Exemple : « DGFIP, TVA » avec l'opérateur contient → la règle matche si le libellé contient l'un OU l'autre. Pratique pour regrouper les variantes d'un même flux (ex. : « URSSAF, RECOUV URSSAF »).",
      "Pour appliquer immédiatement une règle nouvellement créée à l'historique : cliquez sur Créer et appliquer (au lieu de Créer simple). Sinon la règle ne joue qu'à partir des prochains imports et des prochaines actions.",
      "Pour réordonner les règles : glissez-déposez une ligne. Les règles sont évaluées de haut en bas, la première qui matche gagne.",
      "Pour modifier une règle existante : cliquez sur Modifier sur la ligne. Le même tiroir s'ouvre, pré-rempli.",
      "Pour supprimer une règle personnalisée (admin uniquement) : cliquez sur Supprimer ; une confirmation est demandée (« Supprimer la règle \"...\" ? »).",
    ],
    tips: [
      "Depuis la page Transactions, sélectionnez plusieurs opérations puis Suggérer une règle : Horizon vous pré-remplit le formulaire (libellé commun, sens, compte, catégorie déjà choisie le cas échéant).",
      "Les règles système ne sont ni modifiables ni supprimables. Elles assurent les catégorisations de base (frais bancaires, cotisations, virements internes) et garantissent une couverture minimale même sans configuration.",
      "Les opérateurs de libellé disponibles sont contient, commence par, finit par, égal à. Il n'y a pas d'opérateur regex (expression régulière) : pour des cas complexes, séparez plusieurs valeurs par une virgule dans le champ (matching en OU) ou créez plusieurs règles plus simples.",
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
    id: "administration-categories",
    title: "Catégories (administration)",
    subtitle:
      "Gestion des sous-catégories utilisateur (réservée aux administrateurs).",
    sees: [
      "Une page (/administration/categories) qui liste toutes les racines (Encaissements, Personnel, Charges externes, etc.) et leurs sous-catégories. Chaque section racine a un bouton « Ajouter une sous-catégorie » à droite.",
      "Pour chaque sous-catégorie : son nom, un badge « Système » si elle a été seedée par les migrations Horizon (lecture seule), ou des boutons Renommer / Supprimer si c'est une catégorie utilisateur.",
    ],
    does: [
      "Pour ajouter une sous-catégorie sous une racine (ex : « SolarFacility » sous Charges externes) : cliquez sur Ajouter une sous-catégorie dans la section voulue, saisissez le nom, validez. La sous-catégorie est immédiatement disponible dans toutes les comboboxes catégorie de l'app (Transactions, Règles, Prévisionnel).",
      "Pour renommer une sous-catégorie utilisateur : cliquez sur Renommer, modifiez le nom, validez. Les transactions et règles déjà rattachées suivent automatiquement.",
      "Pour supprimer une sous-catégorie utilisateur : cliquez sur Supprimer. Une première confirmation est demandée. Si la catégorie est encore référencée par des transactions ou des règles, une seconde confirmation propose de les déplacer automatiquement vers la catégorie parente puis de supprimer (ex : supprimer « SolarFacility » sous « Charges externes » reclasse les transactions concernées en « Charges externes »). La suppression reste refusée tant que la catégorie a elle-même des sous-catégories : supprimez d'abord celles-ci.",
    ],
    tips: [
      "Les catégories système (badge « Système ») ne peuvent ni être renommées ni supprimées : elles servent de socle stable et sont liées à des règles seed. En revanche, vous pouvez créer autant de sous-catégories utilisateur que nécessaire sous une racine système.",
      "On ne crée que des sous-catégories : les racines sont figées par les seeds. Si vous avez besoin d'une nouvelle racine, c'est une demande au support technique.",
      "Quand vous supprimez une sous-catégorie utilisée, le déplacement vers le parent se fait en une seule transaction SQL : aucun état intermédiaire ne laisse une transaction « orpheline ». Les sous-catégories enfants restent bloquantes (refus de suppression) pour vous forcer à supprimer l'arborescence du bas vers le haut, ce qui évite d'aplatir silencieusement la hiérarchie.",
    ],
    panel: {
      summary:
        "Création / renommage / suppression des sous-catégories utilisateur (admins uniquement). Les catégories système sont en lecture seule.",
      does: [
        "Cliquez Ajouter une sous-catégorie dans la racine voulue, saisissez le nom, validez.",
        "Cliquez Renommer ou Supprimer sur une sous-catégorie utilisateur.",
      ],
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
      "Les événements d'authentification : chaque connexion réussie (action login), chaque tentative de connexion échouée (action login_failed) et chaque déconnexion (action logout) sont tracés dans le journal avec l'adresse IP source et l'horodatage. Pour les retrouver, filtrez par action dans la barre de filtres en haut de page.",
      "Pour chaque événement : horodatage précis (date + heure + secondes), utilisateur auteur, IP source, action (badge create / update / delete / login / login_failed / logout avec un code couleur), type d'entité, identifiant interne, et un résumé des champs modifiés (« champ : avant → après »).",
      "Des filtres en haut de page : type d'entité, action (create/update/delete/login/login_failed/logout), utilisateur, période.",
      "Au clic sur une ligne : un panneau de détail (drawer) qui expose les JSON complets — état avant, état après, et diff champ par champ, en mono-espacé pour la lisibilité.",
    ],
    does: [
      "Pour ouvrir le journal : groupe Administration de la sidebar, lien Journal d'audit. La page est accessible via /administration/audit.",
      "Pour cibler une catégorie d'événements : utilisez le filtre Type d'entité (par ex. Transaction, Commitment, User) puis le filtre Action.",
      "Pour identifier qui a fait une modification donnée : filtrez par utilisateur, ou trouvez la ligne dans la table puis lisez la colonne Auteur.",
      "Pour reconstituer un changement problématique : ouvrez la ligne, lisez le diff champ par champ ou comparez les JSON avant / après.",
      "Pour exporter le journal (avec les filtres actifs) : cliquez sur le bouton 'Exporter CSV' en haut à droite. Le fichier CSV contient les colonnes Date/heure, Utilisateur, Action, Type entité, ID entité, Adresse IP. Il est encodé UTF-8 avec BOM pour Excel.",
    ],
    tips: [
      "Les mots de passe et secrets sont toujours masqués (« <redacted> ») dans les snapshots : aucune donnée sensible n'est exposée dans le journal, même pour un administrateur.",
      "Les lectures (consultations, GET) ne sont pas tracées, seulement les mutations (create/update/delete). Impossible donc de savoir qui a simplement consulté une donnée — c'est volontaire (volume et bruit).",
      "Les imports massifs (par exemple 500 transactions créées d'un coup) ne génèrent qu'une seule entrée d'audit résumée, pas une par transaction. Vous gardez la traçabilité globale sans noyer le journal.",
      "La rétention par défaut est de 365 jours. Si une purge des événements anciens est nécessaire, elle se fait via une intervention SQL directe sur le serveur (opération technique réservée à l'administrateur système, hors de l'interface de l'application).",
      "Voir aussi la section Sécurité et sauvegardes pour la stratégie globale de protection des données.",
    ],
    panel: {
      summary:
        "Trace de toutes les mutations finance-sensibles et des événements d'authentification (login, login_failed, logout). Filtres par entité, action, utilisateur et période ; diff complet sur clic.",
      does: [
        "Filtrez par type d'entité, action (create/update/delete/login/login_failed/logout), utilisateur, période.",
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
      "Un mécanisme de révocation de session par version de token : chaque utilisateur possède un compteur de version interne. Quand un administrateur réinitialise le mot de passe d'un utilisateur, ce compteur est incrémenté. Tous les cookies de session émis avant cette incrémentation deviennent immédiatement invalides, quelle que soit leur date d'expiration nominale.",
      "Un journal d'audit des événements d'authentification : chaque connexion réussie, chaque tentative échouée et chaque déconnexion est enregistrée dans le journal d'audit avec l'adresse IP source et l'horodatage. Consultable depuis Administration > Journal d'audit en filtrant sur l'action login, login_failed ou logout.",
      "Un mécanisme de verrouillage automatique : après 5 tentatives de connexion échouées consécutives, le compte est automatiquement verrouillé pendant 15 minutes. Pendant cette période, même le bon mot de passe est refusé. Le compteur se remet à zéro à chaque connexion réussie.",
    ],
    does: [
      "Pour vérifier la santé des sauvegardes : un administrateur ouvre la page Sauvegardes (groupe Administration) et lit les 4 cartes en haut. Si la dernière sauvegarde réussie a plus de 26h ou que le dernier test de restauration a plus de 8 jours, un bandeau rouge s'affiche.",
      "Pour déclencher une restauration en cas d'incident : demandez à l'administrateur technique. La restauration se fait à partir du dump le plus récent (perte maximale = activité depuis le dernier snapshot nocturne).",
      "Pour réagir à une compromission soupçonnée d'un compte utilisateur : un administrateur réinitialise immédiatement le mot de passe de l'utilisateur concerné depuis la page Administration > Utilisateurs (action Réinitialiser le mot de passe). Cette action change le mot de passe ET invalide instantanément toutes les sessions actives de cet utilisateur. L'utilisateur sera automatiquement déconnecté lors de sa prochaine requête et devra se reconnecter avec le nouveau mot de passe.",
      "Pour réagir à une compromission soupçonnée de votre propre compte : changez immédiatement votre mot de passe depuis la page Profil. Cette action invalide également vos autres sessions actives. Prévenez ensuite un administrateur.",
      "Pour surveiller les connexions suspectes : ouvrez Administration > Journal d'audit, filtrez par action login_failed et vérifiez si un compte accumule des tentatives répétées depuis des IP inconnues.",
      "Si vous recevez un message indiquant que votre compte est temporairement verrouillé : attendez les 15 minutes indiquées dans le message, puis réessayez. Si vous suspectez que quelqu'un tente de prendre le contrôle de votre compte, prévenez un administrateur immédiatement pour qu'il réinitialise votre mot de passe.",
    ],
    tips: [
      "Les sessions reposent sur un cookie HTTP-only : il ne peut pas être lu depuis du JavaScript exécuté dans le navigateur, ce qui bloque les attaques XSS classiques.",
      "La révocation de session fonctionne même si l'utilisateur n'a pas encore fermé son navigateur ou que son cookie n'est pas encore expiré : la version embarquée dans le token est vérifiée à chaque requête authentifiée.",
      "Les PDF importés sont stockés à part pour permettre la prévisualisation, et ne sont jamais accessibles en dehors d'une session authentifiée.",
      "Une restauration de la base écrase l'état actuel : c'est une opération irréversible côté production. Toute modification faite depuis le dernier snapshot est perdue.",
      "L'audit (voir section Journal d'audit) couvre les mutations métier ; les sauvegardes couvrent l'intégralité des données. Les deux sont complémentaires.",
      "Le verrouillage automatique après 5 échecs s'applique même si le bon mot de passe est saisi pendant la période de gel. Ce comportement est intentionnel : il protège contre les attaques par force brute. En cas de gel accidentel, un administrateur peut déverrouiller le compte en réinitialisant le mot de passe depuis Administration > Utilisateurs.",
      "Voir aussi la section Profil pour le changement de mot de passe, et Journal d'audit pour la traçabilité.",
    ],
    panel: {
      summary:
        "Sauvegarde nocturne automatique de la base, en-têtes HTTP de sécurité renforcés, sessions par cookie HTTP-only avec révocation instantanée au reset de mot de passe.",
      does: [
        "Vérifiez régulièrement la page Sauvegardes (groupe Administration) pour la santé des snapshots.",
        "Lancez un test de restore régulièrement depuis la page Sauvegardes pour vous assurer qu'un backup est exploitable.",
        "En cas de compte compromis, réinitialisez le mot de passe depuis Administration > Utilisateurs : le compte et toutes ses sessions actives sont immédiatement bloqués.",
        "Changez votre mot de passe depuis Profil au moindre doute sur votre propre compte.",
      ],
      hide: ["tips"],
    },
  },
  {
    id: "administration-erreurs-client",
    title: "Erreurs client (administration)",
    subtitle:
      "Liste des erreurs JavaScript remontées automatiquement par les navigateurs des utilisateurs (réservée aux administrateurs).",
    sees: [
      "Une page (/administration/erreurs-client) qui liste toutes les erreurs JavaScript survenues dans les navigateurs des utilisateurs. Chaque entrée correspond à une exception non interceptée, un appel API échoué ou une erreur remontée manuellement.",
      "Un tableau avec : identifiant, date et heure de survenance, email de l'utilisateur concerné (ou « Anonyme » si non connecté), niveau de gravité (error, warning, fatal) avec un badge coloré, message d'erreur (tronqué à 80 caractères, texte complet au survol), URL de la page où l'erreur a eu lieu, statut (badge « A traiter » en orange si non acquittée, badge « Acquitte » en vert si acquittée).",
      "Des filtres en haut de page : niveau de gravité (toutes / error / warning / fatal), statut (toutes / non acquittées uniquement / acquittées uniquement), dates Depuis et Jusqu'au.",
      "Un bouton « Marquer acquitte » sur chaque erreur non encore acquittée. Un tooltip explique l'action.",
      "Une pagination (Précédent / Suivant, 50 entrées par page).",
    ],
    does: [
      "Pour consulter les erreurs : ouvrez Administration > Erreurs client dans la sidebar (visible uniquement pour les administrateurs). La liste charge les 50 erreurs les plus récentes.",
      "Pour filtrer par gravité : sélectionnez le niveau dans le menu déroulant Gravité (toutes / error / warning / fatal).",
      "Pour ne voir que les erreurs à traiter : sélectionnez « Non acquittées uniquement » dans le filtre Statut.",
      "Pour acquitter une erreur : cliquez sur Marquer acquitte sur la ligne correspondante. L'erreur passe en statut Acquitte et ne réapparaît pas dans le filtre « Non acquittées uniquement ».",
      "Pour voir le message d'erreur complet : survolez la cellule Message avec la souris (tooltip).",
    ],
    tips: [
      "Acquitter une erreur ne la supprime pas. Elle reste visible dans la liste et dans les filtres. L'acquittement signifie uniquement que l'erreur a été examinée.",
      "Les erreurs sans utilisateur connecté portent la mention « Anonyme » dans la colonne email : elles peuvent indiquer des problèmes sur les pages publiques (connexion, assets).",
      "Un volume élevé d'erreurs d'un même type sur une courte période peut signaler une régression récente. Triez par date décroissante et observez les répétitions.",
    ],
    panel: {
      summary:
        "Erreurs JavaScript remontées par les navigateurs des utilisateurs. Filtre par gravité et statut. Acquittement ligne par ligne.",
      does: [
        "Filtrez par gravité (error / warning / fatal) et par statut (à traiter / acquittées).",
        "Cliquez sur Marquer acquitte pour indiquer qu'une erreur a été examinée.",
        "Survolez le message pour lire le texte complet.",
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
      "Termes financiers — Runway (autonomie de trésorerie) : nombre de mois pendant lesquels la société peut tenir à son rythme actuel de consommation de cash. Burn rate (consommation mensuelle) : différence moyenne entre les sorties et les entrées de cash sur la période récente. MoM (Month over Month, mois sur mois) : comparaison d'un indicateur entre un mois et le mois précédent — permet de suivre les tendances court terme sans avoir besoin d'un historique annuel. KPI (Key Performance Indicator, indicateur clé de performance) : chiffre synthétique mesurant la santé d'un aspect de l'activité.",
      "Concentration et risque — HHI (Herfindahl-Hirschman Index, indice de concentration de Herfindahl-Hirschman) : somme des carrés des parts de marché. Varie de 0 (parfaitement diversifié) à 10 000 (un seul acteur). Repères : moins de 1500 = concentration faible, 1500 à 2500 = modérée, plus de 2500 = forte (seuil d'alerte antitrust américain).",
      "Identifiants bancaires — IBAN (International Bank Account Number, numéro de compte bancaire international) : identifiant standardisé d'un compte bancaire. BIC (Bank Identifier Code, code identifiant bancaire) : identifie l'établissement bancaire à l'échelle internationale. SIREN (Système d'Identification du Répertoire des Entreprises) : identifiant à 9 chiffres d'une entreprise française. SIRET (Système d'Identification du Répertoire des Établissements) : identifiant à 14 chiffres d'un établissement (SIREN + 5 chiffres NIC).",
      "Fiscal et social — DGFIP (Direction Générale des Finances Publiques) : administration fiscale française qui collecte les impôts (TVA, IS, taxes) et le prélèvement à la source. URSSAF (Union de Recouvrement des cotisations de Sécurité Sociale et d'Allocations Familiales) : collecte les cotisations sociales sur les salaires. PAS (Prélèvement À la Source) : retenue d'impôt sur le revenu opérée par l'employeur sur les salaires des employés et reversée à la DGFIP — apparaît dans les libellés bancaires sous la forme PAS-DSN ou IMPOT-PAS-DSN. DSN (Déclaration Sociale Nominative) : déclaration mensuelle unifiée des cotisations sociales et fiscales. IS (Impôt sur les Sociétés) : impôt sur les bénéfices des entreprises. TVA (Taxe sur la Valeur Ajoutée) : taxe sur la consommation collectée puis reversée à la DGFIP. CFE/CVAE (Cotisation Foncière des Entreprises / Cotisation sur la Valeur Ajoutée des Entreprises) : composantes de la contribution économique territoriale.",
      "Technique — SHA256 : empreinte cryptographique de 64 caractères qui prouve qu'un fichier n'a pas été modifié. RGPD (Règlement Général sur la Protection des Données) : réglementation européenne sur la confidentialité des données personnelles. HTTP (HyperText Transfer Protocol) / HTTPS (HTTP Secure) : protocoles de communication web, le second chiffré.",
    ],
    tips: [
      "Si vous croisez un terme non listé ici, signalez-le à un administrateur — il sera ajouté au lexique pour les autres utilisateurs.",
      "Les acronymes anglais conservés (Runway, Burn rate, MoM, HHI) sont des standards de la finance d'entreprise : les rapports d'audit, les analystes financiers et les outils tiers (Agicap, Pennylane, etc.) utilisent les mêmes termes. Connaître la version anglaise vous évite d'être perdu dans ces contextes.",
    ],
    panel: {
      summary:
        "Glossaire des sigles utilisés dans l'application (financiers, bancaires, techniques).",
      hide: ["tips"],
    },
  },
];

/**
 * Documentation d'impact des actions UI à effet (E3, E5, E9).
 * Voir CLAUDE.md -> section "Documentation d'impact obligatoire".
 */
export const FEATURE_DOCS: FeatureDoc[] = [
  {
    id: "apercu-live-regles",
    title: "Aperçu automatique dans le formulaire de règle",
    whatItDoes:
      "Affiche en temps réel les transactions qui seraient capturées par la règle en cours de configuration, sans nécessiter un clic sur le bouton Aperçu.",
    whatItChanges: [
      "Déclenche automatiquement un appel GET /api/rules/preview 450 ms après la dernière modification d'un filtre (libellé, sens, montant, tiers, compte, société).",
      "Met à jour la liste d'aperçu dans le tiroir sans action manuelle.",
    ],
    whatItDoesNotChange: [
      "Ne crée aucune règle, ne catégorise aucune transaction.",
      "Le bouton Aperçu reste disponible pour un rafraîchissement forcé immédiat.",
      "L'aperçu ne se déclenche pas si aucun filtre n'est défini (champ libellé vide, sens Toutes, pas de tiers ni de compte).",
    ],
    whenToUse: [
      "Quand vous ajustez un libellé et souhaitez voir immédiatement l'impact sans cliquer.",
      "Quand vous comparez plusieurs variantes d'un filtre pour trouver la formulation la plus précise.",
    ],
  },
  {
    id: "marquer-acquitte-erreur-client",
    title: "Marquer une erreur client comme acquittée",
    whatItDoes:
      "Indique qu'une erreur JavaScript remontée par un navigateur a été examinée et traitée par un administrateur.",
    whatItChanges: [
      "Appelle PATCH /api/admin/client-errors/{id}/acknowledge côté backend.",
      "Enregistre la date et l'heure d'acquittement (champ acknowledged_at) dans la base de données.",
      "Le badge statut de la ligne passe de « A traiter » (orange) à « Acquitte » (vert).",
    ],
    whatItDoesNotChange: [
      "Ne supprime pas l'entrée. L'erreur reste visible dans la liste.",
      "Ne corrige pas le bug sous-jacent. L'acquittement est un marqueur organisationnel, pas une résolution technique.",
    ],
    whenToUse: [
      "Après avoir examiné une erreur, identifié sa cause et confirmé qu'elle est résolue ou sans impact.",
      "Pour filtrer la liste et ne voir que les erreurs restant à traiter.",
    ],
  },
  {
    id: "rules-hit-count",
    title: "Colonne Hits dans la liste des règles",
    whatItDoes:
      "Affiche le nombre de transactions que chaque règle a catégorisées jusqu'à présent. Permet de distinguer les règles actives des règles jamais déclenchées.",
    whatItChanges: [
      "L'API GET /api/rules retourne désormais un champ hit_count par règle, calculé en direct via COUNT(transactions.categorization_rule_id).",
      "Une colonne Hits apparaît entre les colonnes Condition et Catégorie dans le tableau. Un clic sur l'en-tête Hits trie les règles du plus au moins utilisé.",
    ],
    whatItDoesNotChange: [
      "Ne modifie aucune règle ni aucune transaction.",
      "Le tri par Hits est temporaire (en mémoire) et n'affecte pas l'ordre d'évaluation des règles au moment de la catégorisation. L'ordre d'évaluation reste déterminé par la priorité numérique.",
    ],
    whenToUse: [
      "Pour identifier les règles jamais déclenchées (hit_count = 0) et envisager de les supprimer ou de les ajuster.",
      "Pour vérifier qu'une règle nouvellement créée commence bien à capturer des transactions après un import.",
    ],
  },
  {
    id: "filtres-montant",
    title: "Filtres Montant min / Montant max sur la page Transactions",
    whatItDoes:
      "Permet de restreindre la liste des transactions a celles dont la valeur absolue du montant est comprise dans une fourchette donnee.",
    whatItChanges: [
      "Passe les parametres amount_min et amount_max (en euros) a l'API GET /api/transactions.",
      "Le backend filtre les transactions dont func.abs(amount) est superieur ou egal a amount_min et inferieur ou egal a amount_max.",
      "La liste se rechargeen page 1 des que vous modifiez un des deux champs.",
    ],
    whatItDoesNotChange: [
      "Ne modifie aucune transaction.",
      "Le filtre montant ne remplace pas les autres filtres (periode, categorie, recherche) : ils s'appliquent tous ensemble.",
      "Le filtre s'applique sur la valeur absolue : un filtre Montant min = 1000 capture aussi bien les encaissements de 1 000 EUR que les decaissements de 1 000 EUR.",
    ],
    whenToUse: [
      "Pour isoler les operations importantes au-dela d'un seuil (ex. : toutes les depenses superieures a 5 000 EUR).",
      "Pour identifier les micro-transactions sous un certain montant (ex. : tout ce qui est inferieur a 10 EUR).",
    ],
  },
  {
    id: "url-persistence-transactions",
    title: "Persistance des filtres dans l'URL sur la page Transactions",
    whatItDoes:
      "Enregistre l'etat de tous les filtres actifs dans l'URL de la page, de sorte qu'un rechargement ou un partage de lien restaure exactement la meme vue filtree.",
    whatItChanges: [
      "Chaque modification de filtre (recherche, periode, categorie, montant, SEPA, non categorisees, compte, contrepartie, pagination) met a jour l'URL via useSearchParams sans provoquer de rechargement complet.",
      "L'URL reste propre (aucun parametre) quand tous les filtres sont a leur valeur par defaut.",
    ],
    whatItDoesNotChange: [
      "La selection de transactions (cases cochees) n'est pas persistee dans l'URL : elle se vide au changement de page ou de filtre.",
      "Le filtre entite (societe) n'est pas dans l'URL : il est global a l'application via l'EntitySelector.",
    ],
    whenToUse: [
      "Pour partager une vue filtree avec un collegue (copier-coller l'URL du navigateur).",
      "Pour retrouver un contexte de travail apres un rechargement accidentel de la page.",
    ],
  },
  {
    id: "toggle-sepa",
    title: "Toggle Afficher les virements SEPA detailles sur la page Transactions",
    whatItDoes:
      "Permet d'afficher les sous-transactions d'un virement SEPA de masse (lignes enfants dont parent_transaction_id est non null), masquees par defaut.",
    whatItChanges: [
      "Active ou desactive le parametre include_sepa_children dans la requete GET /api/transactions.",
      "Quand desactive (comportement par defaut) : seules les lignes sans parent (parent_transaction_id = null) sont retournees, ce qui evite de voir la meme operation deux fois.",
      "Quand active : les sous-transactions apparaissent egalement, permettant de voir le detail de chaque sous-virement.",
      "L'etat du toggle est persist dans l'URL (parametre sepa=true).",
    ],
    whatItDoesNotChange: [
      "Ne modifie aucune transaction.",
      "L'activation du toggle n'affecte pas les autres filtres.",
    ],
    whenToUse: [
      "Quand vous voulez comprendre la decomposition d'un virement SEPA de masse et verifier que chaque ligne enfant est correctement categorisee.",
    ],
  },
  {
    id: "filtre-tiers-transactions",
    title: "Filtre par tiers sur la page Transactions",
    whatItDoes:
      "Permet de restreindre la liste des transactions a celles rattachees a un tiers (client ou fournisseur) donne. Le selecteur propose tous les tiers actifs de la societe selectionnee, avec recherche par nom.",
    whatItChanges: [
      "Passe le parametre counterparty_id a l'API GET /api/transactions.",
      "Le backend filtre les transactions dont counterparty_id correspond.",
      "Quand le filtre est actif, les sous-transactions SEPA enfants sont incluses automatiquement, meme si le toggle Afficher les virements SEPA detailles est desactive — sans cela, un tiers paye exclusivement par virement SEPA de masse ne renverrait aucune ligne, car les batch parents SEPA n'ont pas de tier rattache.",
      "Le filtre est persiste dans l'URL via le parametre counterparty et est restaure au rechargement de la page.",
    ],
    whatItDoesNotChange: [
      "Ne modifie aucune transaction.",
      "Le filtre tiers s'applique en supplement des autres filtres (periode, categorie, montant, recherche, non categorisees) — ils sont tous combines avec un ET logique.",
      "Le selecteur masque les tiers en statut ignore : pour les retrouver, passer par la page Clients et fournisseurs avec l'option Inclure les tiers ignores.",
    ],
    whenToUse: [
      "Pour verifier les paiements recus d'un client ou envoyes a un fournisseur sur une periode donnee.",
      "Pour rapprocher un releve fournisseur avec les transactions effectivement passees en banque.",
      "Pour preparer une categorisation en masse de toutes les transactions d'un tiers (par exemple, requalifier les paiements de salaire d'un employe).",
    ],
  },
  {
    id: "bulk-categorize-filtre",
    title: "Categoriser tous les resultats d'un filtre (sans limite de page)",
    whatItDoes:
      "Permet de catégoriser en une seule action toutes les transactions correspondant aux filtres actifs, sans etre limite a la page courante.",
    whatItChanges: [
      "Appelle POST /api/transactions/bulk-categorize-filtered avec les criteres de filtre courants (periode, recherche, categorie, montant, SEPA, non categorisees, compte, contrepartie) et la categorie choisie.",
      "Le backend reconstruit la meme requete SQL que GET /api/transactions, sans limite de pagination, et met a jour toutes les transactions trouvees.",
      "Le nombre total d'operations categorisees est affiche dans le panneau apres l'action.",
    ],
    whatItDoesNotChange: [
      "Ne touche pas aux transactions qui ne correspondent pas aux filtres actifs.",
      "L'endpoint existant de categorisation par identifiants (bulk-categorize avec transaction_ids) reste disponible pour la categorisation de la page courante uniquement.",
    ],
    whenToUse: [
      "Quand vous avez filtre « Non categorisees uniquement » et souhaitez tout catégoriser d'un coup dans la meme categorie.",
      "Quand vous avez un grand volume de transactions a traiter (plus de 50, donc plusieurs pages) et qu'une seule categorie convient pour tout le resultat filtre.",
    ],
  },
  {
    id: "auto-suggest-regle",
    title: "Suggestion automatique de regle apres catégorisations manuelles repetees",
    whatItDoes:
      "Detecte lorsque vous avez catégorise manuellement le meme libellé au moins 3 fois dans la meme categorie au cours des 30 derniers jours, et vous propose de créer une regle automatique.",
    whatItChanges: [
      "Appelle GET /api/rules/auto-suggest au chargement de la page Transactions.",
      "Si des suggestions sont disponibles, un bandeau ambre apparait en haut de la page avec un bouton « Créer une regle » par suggestion.",
      "Cliquer sur « Créer une regle » ouvre le formulaire de regle prefilled (operateur CONTAINS, valeur = libelle normalise, categorie = categorie detectee).",
      "Cliquer sur « Plus tard » masque la suggestion pour la session en cours (sessionStorage), sans la supprimer cote serveur.",
    ],
    whatItDoesNotChange: [
      "Ne crée aucune regle automatiquement : c'est toujours vous qui validez le formulaire.",
      "Ne supprime pas les transactions ni les catégorisations manuelles existantes.",
      "Les catégorisations effectuees par une regle ne sont pas comptees : seules les catégorisations de type MANUAL sont analysees.",
    ],
    whenToUse: [
      "Quand le meme tiers ou libelle revient chaque mois et que vous le catégorisez manuellement a chaque fois : acceptez la suggestion pour automatiser la prochaine fois.",
    ],
  },
  {
    id: "daily-balance-chart",
    title: "Graphe de solde de tresorerie quotidien (90 jours)",
    whatItDoes:
      "Affiche l'evolution du solde de tresorerie jour par jour sur les 90 derniers jours, reconstruit a partir du dernier releve importe. Permet de visualiser en un coup d'oeil la tendance et les creux de liquidites.",
    whatItChanges: [
      "Aucun effet : c'est une lecture seule. Survoler le graphe avec la souris fait apparaitre un tooltip avec la date et le solde exact de ce jour.",
      "La couleur de l'aire change selon le signe du dernier solde connu : verte si positif, rouge si negatif.",
    ],
    whatItDoesNotChange: [
      "Les transactions ne sont pas modifiees.",
      "Les imports ne sont pas modifies.",
      "Le graphe ne modifie aucune donnee en base.",
    ],
    whenToUse: [
      "Pour detecter des creux de tresorerie a venir ou passes.",
      "Pour reperer la saisonnalite des flux (pic de depenses en fin de mois, renforcement en debut de trimestre).",
      "Pour preparer un rendez-vous banquier avec une vision claire de l'evolution du solde.",
    ],
  },
  {
    id: "per-account-balance",
    title: "Position de tresorerie par compte bancaire",
    whatItDoes:
      "Affiche une grille de cartes, une par compte bancaire accessible, avec le solde courant, la variation sur 30 jours (en euros et en pourcentage) et une mini-courbe (sparkline) sur 30 points quotidiens. Permet de voir d'un coup d'oeil quelle entite ou quel compte est en tension.",
    whatItChanges: [
      "Aucun effet : c'est une lecture seule.",
      "Les cartes se mettent a jour automatiquement lors du rechargement de la page ou apres un nouvel import.",
    ],
    whatItDoesNotChange: [
      "Les soldes en base ne sont pas modifies.",
      "La variation affichee est calculee entre le dernier import disponible et le dernier import dont la date de fin de periode est anterieure de 30 jours.",
      "Un compte sans import n'apparait pas dans la grille.",
    ],
    whenToUse: [
      "Pour surveiller la position de chaque compte separement quand plusieurs comptes bancaires sont enregistres.",
      "Pour verifier rapidement si la variation 30 jours est coherente avec les flux attendus.",
      "Pour identifier quel compte est le plus actif ou le plus en tension avant un arbitrage de tresorerie.",
    ],
  },
  // ---------------------------------------------------------------------------
  // G3 — Bandeau DSO/DPO/BFR sur ForecastV2Page
  // ---------------------------------------------------------------------------
  {
    id: "working-capital-banner-forecast",
    title: "Bandeau DSO/DPO/BFR sur la page Previsionnel",
    whatItDoes:
      "Affiche en tete de la page Previsionnel trois indicateurs de besoin en fonds de roulement : DSO (delai client moyen), DPO (delai fournisseur moyen) et BFR (besoin en fonds de roulement en euros). Ces chiffres ancrent le previsionnel dans la realite des creances et dettes courantes.",
    whatItChanges: [
      "Appelle GET /api/analysis/working-capital au chargement de la page Previsionnel, pour l'entite selectionnee.",
      "Affiche trois cartes KPI entre le selecteur d'entite/scenario et le graphique de barres.",
      "Si has_data=false (aucun engagement matche a une transaction), affiche un encadre ambre invitant a creer des engagements.",
      "Si DSO ou DPO est null (donnees insuffisantes), affiche le tiret — avec un tooltip explicatif.",
    ],
    whatItDoesNotChange: [
      "Les engagements, les transactions, le scenario de prevision.",
      "Le pivot et le graphique de barres ne sont pas modifies.",
      "C'est une lecture seule : aucune ecriture en base.",
    ],
    whenToUse: [
      "Avant de valider un previsionnel mensuel, pour verifier que le BFR est coherent avec les encaissements attendus.",
      "Pour surveiller un DSO eleve signalant des clients qui paient lentement et pouvant creer un creux de tresorerie.",
    ],
  },
  // ---------------------------------------------------------------------------
  // G2 — Rolling 13-week
  // ---------------------------------------------------------------------------
  {
    id: "rolling-13w",
    title: "Vue hebdomadaire 13 semaines glissantes",
    whatItDoes:
      "Affiche un graphique en barres representant les flux nets realises (semaines passees) et prevus par le scenario actif (semaines futures) sur une fenetre de 13 semaines : W-1 (semaine precedente) a W+11. Permet de detecter d'un coup d'oeil si une semaine prochaine est financierement tendue.",
    whatItChanges: [
      "Appelle GET /api/forecast/rolling-13w au chargement, pour l'entite et le scenario selectionnes.",
      "Affiche une section Tresorerie hebdomadaire en bas de la page Previsionnel, apres le tableau pivot.",
      "Les semaines passees ont des barres pleines, les semaines futures ont des barres semi-transparentes.",
    ],
    whatItDoesNotChange: [
      "Les transactions, les forecast_lines, le scenario.",
      "La vue mensuelle du pivot n'est pas affectee.",
      "Lecture seule : aucune ecriture en base.",
    ],
    whenToUse: [
      "En gestion de tresorerie operationnelle jour-a-jour, pour anticiper une semaine tendue a venir.",
      "Pour valider que les previsions hebdomadaires du scenario actif sont coherentes avec les transactions realisees des semaines precedentes.",
    ],
  },
  // ---------------------------------------------------------------------------
  // G7 — Overlay multi-scenarios
  // ---------------------------------------------------------------------------
  {
    id: "scenario-overlay",
    title: "Comparaison de scenarios en overlay",
    whatItDoes:
      "Permet de superposer le solde projete d'un second scenario sur le graphique Encaissements vs. decaissements, sous la forme d'une ligne pointillee jaune. Facilite la comparaison visuelle entre deux hypotheses (par exemple Optimiste vs Pessimiste) sans quitter la page.",
    whatItChanges: [
      "Active un bouton Comparer dans la barre d'outils de la page Previsionnel.",
      "Quand active, affiche un selecteur de scenario de comparaison.",
      "Quand un second scenario est selectionne, appelle GET /api/forecast/pivot pour ce scenario et ajoute une ligne pointillee jaune sur le graphique de barres.",
    ],
    whatItDoesNotChange: [
      "Aucun scenario n'est modifie : c'est une visualisation en lecture seule.",
      "Le tableau pivot et le scenario actif restent inchanges.",
      "Fermer ou desactiver le bouton Comparer retire l'overlay sans aucun effet de bord.",
    ],
    whenToUse: [
      "Pour comparer visuellement un scenario optimiste et un scenario pessimiste sur la meme periode.",
      "Pour preparer une presentation a un investisseur ou un banquier en montrant l'amplitude des incertitudes.",
    ],
  },
  // ---------------------------------------------------------------------------
  // G11 — Export CSV generalisé
  // ---------------------------------------------------------------------------
  {
    id: "export-csv",
    title: "Export CSV des données",
    whatItDoes:
      "Permet de télécharger les données affichées sur les pages clés (Transactions, Journal d'audit, Analyse — dérives, top movers, MoM 6 mois — et Prévisionnel pivot) sous forme de fichier CSV. Le fichier est encodé en UTF-8 avec BOM pour une ouverture correcte dans Excel sur Windows, et utilise le point-virgule comme séparateur (standard FR).",
    whatItChanges: [
      "Déclenche un appel GET vers l'endpoint d'export correspondant avec les filtres actifs au moment du clic.",
      "Génère un fichier .csv dans le dossier Téléchargements du navigateur.",
      "Le nom du fichier inclut la date du jour (ex : transactions_2026-05-07.csv).",
    ],
    whatItDoesNotChange: [
      "Aucune donnée en base n'est modifiée : l'export est une lecture seule.",
      "Les filtres actifs sur la page sont respectés : seules les données visibles sont exportées.",
      "Les permissions multi-tenant sont appliquées : un utilisateur n'exporte que les données auxquelles il a accès.",
    ],
    whenToUse: [
      "Pour réaliser une clôture mensuelle ou préparer un reporting comptable.",
      "Pour fournir un extract de données à un expert-comptable ou un auditeur.",
      "Pour analyser les transactions dans un tableur (Excel, Calc) avec des formules personnalisées.",
      "Pour archiver l'état du journal d'audit à une date donnée.",
    ],
  },
  // ---------------------------------------------------------------------------
  // G8 — What-if sans persistence
  // ---------------------------------------------------------------------------
  {
    id: "what-if-simulation",
    title: "Simulation what-if sur le tableau pivot",
    whatItDoes:
      "Permet de modifier temporairement n'importe quelle cellule de prevision (mois courant ou futur) en double-cliquant dessus, sans enregistrer la valeur en base. Les totaux de colonnes et le solde de fin de mois sont recalcules automatiquement cote navigateur. Un bouton Reinitialiser les simulations remet toutes les cellules a leurs valeurs reelles.",
    whatItChanges: [
      "Double-clic sur une cellule future ou courante : affiche un champ de saisie (fond orange) a la place de la valeur.",
      "Apres validation (Entree ou clic ailleurs), la cellule s'affiche en orange avec la valeur saisie.",
      "Les lignes Total encaissements, Total decaissements, Variation nette de cash et Tresorerie en fin de mois (simulation) sont recalculees avec les valeurs overridees.",
      "Un bandeau ambre en haut du tableau indique que le mode simulation est actif.",
    ],
    whatItDoesNotChange: [
      "Le scenario, les forecast_lines et aucune donnee persistee en base.",
      "Les overrides disparaissent lors d'un rechargement de page ou en cliquant sur Reinitialiser.",
      "Les mois passes (anterieurs au mois courant) ne sont pas editables.",
    ],
    whenToUse: [
      "Pour explorer rapidement l'impact d'une depense exceptionnelle sur la tresorerie projetee, sans creer un nouveau scenario.",
      "Pour preparer un chiffre a communiquer (si on depense X ce mois, quel est le solde fin de mois ?) avant une reunion.",
    ],
  },
  // ---------------------------------------------------------------------------
  // G9 — Saisonnalité par catégorie
  // ---------------------------------------------------------------------------
  {
    id: "seasonality-chart",
    title: "Saisonnalité par catégorie (N vs N-1)",
    whatItDoes:
      "Affiche un graphique comparant les flux mensuels d'une catégorie entre l'année en cours (N) et l'année précédente (N-1) sur 24 mois glissants. Permet de détecter les patterns récurrents (loyer, abonnements, primes) et d'anticiper les mois à flux élevés.",
    whatItChanges: [
      "Affiche une carte Saisonnalité par catégorie en bas de la page Analyse.",
      "Un menu déroulant permet de choisir la catégorie à analyser.",
      "Si la catégorie sélectionnée a moins de 13 mois de données, un encadré informatif indique la date estimée à laquelle le graphique deviendra disponible.",
      "Si 13+ mois de données sont disponibles, un graphique en courbes (bleu = N, gris tirets = N-1) s'affiche avec les totaux mensuels en euros.",
    ],
    whatItDoesNotChange: [
      "Les transactions, catégories ou imports ne sont pas modifiés.",
      "C'est une visualisation en lecture seule.",
      "Les données d'autres catégories ou entités ne sont pas affectées.",
    ],
    whenToUse: [
      "Pour valider que les dépenses d'une catégorie suivent le même rythme que l'année précédente (vérification de conformité).",
      "Pour anticiper un pic de dépenses saisonnier (ex. : assurances en janvier, primes en décembre) avant qu'il n'impacte la trésorerie.",
      "Pour expliquer à un partenaire bancaire ou un investisseur la normalité d'un pic mensuel.",
      "Note : avec moins de 13 mois de données importées, ce graphique affiche un placeholder et deviendra utile progressivement.",
    ],
  },
  // ---------------------------------------------------------------------------
  // G4 — Anomalies p95 par catégorie
  // ---------------------------------------------------------------------------
  {
    id: "anomaly-detection",
    title: "Détection des transactions inhabituelles (p95)",
    whatItDoes:
      "Identifie automatiquement les transactions dont le montant absolu dépasse le 95e percentile historique de leur catégorie sur les 180 derniers jours. Le résultat est une liste des transactions des 30 derniers jours qui sont statistiquement inhabituelles, triées par ratio décroissant (les plus inhabituelles en premier).",
    whatItChanges: [
      "Affiche une carte Transactions inhabituelles sur la page Analyse, avec la liste des transactions anormales : date, libellé, catégorie, montant, et le ratio (ex : x 2.3 signifie 2.3 fois le p95 de la catégorie).",
      "Un compteur de badge indique le nombre total d'anomalies détectées.",
    ],
    whatItDoesNotChange: [
      "Les transactions elles-mêmes ne sont pas modifiées, recatégorisées ou marquées en base.",
      "Le calcul est en lecture seule : aucun enregistrement n'est créé lors de l'affichage.",
      "Les catégories ayant moins de 5 transactions sur la fenêtre d'analyse sont exclues du calcul (p95 non fiable sur un petit échantillon).",
    ],
    whenToUse: [
      "Pour repérer rapidement une dépense exceptionnelle oubliée (facture mal imputée, paiement en double, erreur de virement).",
      "Pour préparer une revue mensuelle des dépenses inhabituelles sans trier manuellement les transactions.",
      "Pour détecter des frais récurrents qui auraient subi une hausse silencieuse (abonnement, loyer, prestataire).",
    ],
  },
  // ---------------------------------------------------------------------------
  // G12 — Snooze/acquittement de dérive
  // ---------------------------------------------------------------------------
  {
    id: "drift-snooze",
    title: "Snooze d'une alerte de dérive (30 jours)",
    whatItDoes:
      "Permet de mettre en veille une alerte de dérive de catégorie pour 30 jours en cliquant sur le bouton \"Snooze 30 j\" visible sur chaque ligne en statut Dérive dans le tableau Dérives par catégorie. Un acquittement est enregistré en base avec la date d'expiration, le nom de l'utilisateur et une note optionnelle. L'alerte reste visible dans le tableau sous la forme d'un badge gris \"En veille\" jusqu'à expiration, ce qui garantit la traçabilité.",
    whatItChanges: [
      "Crée un enregistrement dans la table drift_acks en base avec entity_id, category_id, snoozed_until (aujourd'hui + 30 jours) et l'identifiant de l'utilisateur connecté.",
      "La catégorie passe du statut Dérive (fond rose) au statut En veille (fond gris) dans le tableau Dérives par catégorie.",
      "L'alerte ne compte plus dans le compteur de dérives affiché en haut du tableau.",
      "Après expiration (J+30), la catégorie peut à nouveau apparaître en statut Dérive si la dérive persiste.",
    ],
    whatItDoesNotChange: [
      "Les transactions de la catégorie ne sont pas modifiées.",
      "Le calcul de dérive continue de s'exécuter en arrière-plan : la donnée est toujours calculée, seul l'affichage change.",
      "Les autres catégories du tableau ne sont pas affectées.",
      "L'historique de l'acquittement est conservé en base et auditable.",
    ],
    whenToUse: [
      "Lorsqu'une dépense exceptionnelle connue (achat de matériel, prime de fin d'année, sinistre, campagne marketing ponctuelle) déclenche une alerte qui n'a pas lieu d'être surveillée ce mois-ci.",
      "Pour nettoyer le tableau de bord avant une réunion de revue financière, en distinguant les alertes réelles des alertes contextuelles.",
      "Lorsqu'une catégorie est en cours de restructuration et que les chiffres du mois sont transitoires.",
    ],
  },
  {
    id: "acces-entites-reader",
    title: "Accorder ou révoquer l'accès d'un reader à une entité",
    whatItDoes:
      "Détermine quelles entités (sociétés) un utilisateur de rôle Lecture (reader) peut consulter. Sans entrée dans cette liste, un reader ne voit aucune donnée — ni transactions, ni comptes, ni dashboard. Les administrateurs voient toutes les entités quelle que soit cette configuration.",
    whatItChanges: [
      "Accorder appelle POST /api/users/{id}/entity-access et crée une ligne dans la table user_entity_access. À partir de cet instant, le reader voit l'entité dans le sélecteur EntitySelector et dans tous les écrans filtrés par entité (Dashboard, Transactions, Forecast, Analyse, Engagements).",
      "Révoquer appelle DELETE /api/users/{id}/entity-access/{entity_id} et supprime cette ligne. Le reader perd immédiatement l'accès aux données de cette entité ; les pages qui n'ont plus aucune entité accessible affichent une liste vide.",
      "Chaque action est tracée dans le journal d'audit (action create ou delete sur l'objet UserEntityAccess).",
    ],
    whatItDoesNotChange: [
      "Ne modifie ni ne supprime aucune transaction, aucune catégorie, aucun engagement. C'est uniquement un droit de consultation.",
      "N'a aucun effet sur les administrateurs : un admin voit toujours toutes les entités, indépendamment de cette liste.",
      "Ne déclenche aucun email ni notification : le reader doit se reconnecter ou rafraîchir la page pour voir le changement.",
      "Ne modifie pas le rôle de l'utilisateur. Pour passer un reader en admin, utiliser le formulaire d'édition de l'utilisateur.",
    ],
    whenToUse: [
      "À la création d'un nouveau reader : attribuer immédiatement les entités auxquelles il doit accéder, sinon il voit une application vide.",
      "Lors d'un changement d'organisation (nouveau collaborateur sur une filiale, départ d'un comptable, séparation de périmètres).",
      "Pour restreindre temporairement un reader à un sous-ensemble d'entités sans changer son rôle.",
    ],
  },
];
