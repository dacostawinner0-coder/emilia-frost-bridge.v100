# Cahier des charges — Emilia Frost v100

> Document de référence pour les prochaines IA et personnes qui contribueront au projet. Il décrit la vision et l’état connu du dépôt ; il ne signifie pas que toutes les fonctions sont déjà codées.
>
> **Important pour le déploiement : ce fichier est de la documentation seulement.** Il ne doit pas être importé par le bot, installé comme dépendance, exécuté par Railway, ni modifié pour changer le `Dockerfile`, `railway.toml`, les commandes de démarrage ou les variables de déploiement. L’ajout de ce document seul ne doit pas pouvoir faire échouer le build ou le démarrage Railway.

## 1. Vision du produit

Emilia Frost est un bot Discord communautaire, principalement en français, avec une identité douce, moderne et soignée : bleu glacier, blanc et violet pastel. L’interface doit être claire sur ordinateur et mobile. Le projet doit évoluer comme un produit modulaire, fiable et documenté, plutôt qu’un assemblage de commandes sans règles communes.

## 2. Principes non négociables

- **Multi-serveur :** toute donnée appartenant à une communauté doit être isolée par `guild_id`. Les comptes ou historiques d’un serveur ne doivent pas être visibles ni utilisables dans un autre, sauf fonctionnalité interserveur explicitement conçue et autorisée.
- **Autorisations :** un préfixe n’accorde jamais de permission. Chaque commande vérifie l’identité, les permissions Discord, les rôles configurés et, pour la modération, la hiérarchie du membre et du bot.
- **Propriétaire :** les commandes propriétaires sont réservées aux identifiants numériques configurés dans `OWNER_IDS`. Ne jamais se fier uniquement au préfixe.
- **Secrets :** ne jamais committer le token Discord, un fichier `.env` réel, une clé ou un secret. Les secrets résident dans les variables du fournisseur d’hébergement.
- **Économie :** soldes non négatifs ; récompenses, achats, transferts, dépôts/retraits, taxes et autres mouvements doivent être atomiques et produire un historique vérifiable.
- **Modération :** chaque action sensible doit produire une trace avec serveur, auteur, cible, action, motif et date. Expliquer clairement la différence entre un rôle de restriction interne et un ban Discord natif.
- **Documentation honnête :** une fonction « prévue » n’est pas une fonction disponible. L’aide et le registre des commandes doivent refléter le code réellement livré.
- **Évolution prudente :** les migrations de base doivent être versionnées, sauvegarder les données existantes et fournir des contrôles de rapprochement avant toute migration destructive.

## 3. Préfixes et commandes

La convention produit souhaitée est :

- `/` : commandes slash Discord.
- `!` : commandes générales et économiques.
- `+` : commandes de staff et de modération.
- `w.` : commandes réservées au propriétaire.

Les préfixes `!`, `+` et `w.` ne remplacent jamais les vérifications d’autorisation. Les commandes hybrides slash doivent appliquer les mêmes contrôles de permission que leurs équivalents préfixés.

Un registre de commandes maintenu dans `docs/command-registry.toml` doit préciser, pour chaque commande : nom, alias, catégorie, syntaxe, préfixe, permissions et état (`prévu`, `développé`, `testé localement`, `testé sur Discord`).

## 4. Architecture visée

Organiser progressivement le code autour de responsabilités distinctes :

- `core/` : configuration, politiques de permission, journalisation et bootstrap.
- `database/` : schéma, migrations versionnées et accès aux données.
- `services/` : logique métier réutilisable et indépendante des commandes Discord.
- `cogs/` : commandes Discord par domaine fonctionnel.
- `ui/` : embeds, vues et composants visuels cohérents.
- `tests/` : tests unitaires, d’intégration simulée et concurrence.
- `docs/` : cahier, registre de commandes, architecture de données et guides.

Éviter de dupliquer la logique économique ou les contrôles d’accès dans les cogs. Les commandes doivent appeler des services testables.

## 5. Modules prévus

La liste ci-dessous est une vision produit, pas une annonce de disponibilité. Chaque module devra avoir des règles détaillées, des permissions, un schéma guild-scoped, des tests et une entrée au registre avant d’être annoncé comme livré.

### Fondation et expérience

- Démarrage robuste, configuration par environnement, commandes d’aide et d’état.
- Interface Emilia Frost cohérente, réponses d’erreur compréhensibles et expérience mobile.
- Registre de commandes et documentation synchronisés avec les fonctionnalités réelles.

### Économie et progression

- Portefeuille, banque, récompenses quotidiennes, travail, transferts et classement.
- Taxes, intérêts, limites, historique/audit, équilibrage économique et règles anti-abus.
- MF et toute monnaie ou ressource additionnelle avec règles explicites.
- Toute opération de solde doit être atomique et ne jamais permettre un solde négatif.

### Communauté et jeu

- Familles et progression familiale.
- Prison de jeu et systèmes associés, distincts des sanctions Discord.
- Tickets de support et outils pour l’équipe.
- Coffres (COFFRESMUSK), WINNERMUSK, événements, giveaways et bump.
- Garage, véhicules, animalerie et animaux.
- Gouvernement, élections, missions et systèmes communautaires associés.

### Modération et administration

- Avertissements, historique, timeout, expulsion, ban natif Discord et rôle de restriction interne distinct.
- Journaux configurables, contrôles de hiérarchie, gestion sûre des rôles et audit.
- Paramètres configurables par serveur et commandes d’administration protégées.

### Exploitation et données

- Sauvegardes et restauration testées avant mise en production.
- Tableau de bord uniquement si son authentification, ses permissions et son modèle de menace sont spécifiés.
- Transferts interserveurs seulement après décision produit explicite, avec consentement et règles anti-abus ; le cloisonnement par serveur reste le défaut.

## 6. État de livraison connu dans cette branche

Les éléments suivants ont été repérés comme présents dans la fondation à la date de rédaction ; ils doivent encore être vérifiés avec les tests et le déploiement réel avant d’être qualifiés de validés sur Discord :

- Comptes SQLite isolés par serveur, réglages serveur, transactions économiques, dossiers de modération et role-bans internes.
- Commandes économiques de base : solde, daily, work, transfert, banque, dépôt/retrait et classement.
- Commandes de modération de base : avertissement, historique, timeout, kick, role-ban interne, levée du role-ban, ban natif Discord, configuration de rôle/log et purge.
- Commandes générales `help` et `ping`, ainsi que statut propriétaire protégé par `OWNER_IDS` dans les fichiers de la branche.
- Tests automatisés SQLite et test de chargement des extensions présents ou en cours d’ajout.

**À vérifier avant de considérer la fondation comme déployée :** que Railway suit la branche voulue ; que le commit de correction du bootstrap est inclus ; que le build de l’image réussit ; que les variables requises sont configurées ; que le bot se connecte et synchronise ses commandes dans un serveur de test. Ne pas déclarer une validation Discord réelle sur la seule base de la présence du code.

**Non implémenté dans cette fondation, sauf ajout ultérieur documenté :** familles, tickets, prison de jeu, COFFRESMUSK, WINNERMUSK, véhicules, animaux, gouvernement, élections, missions, événements avancés, taxes/intérêts, dashboard, sauvegardes externes et transferts interserveurs.

## 7. Déploiement Railway — règle de non-régression

- Le code applicatif se lance avec la commande configurée par le projet ; les dépendances Python doivent être listées dans `requirements.txt`.
- Le build et le démarrage doivent rester déterministes et être vérifiés avant de demander un redeploy.
- Le chemin de base de données doit pointer vers un volume persistant configuré côté Railway ; le chemin seul ne crée pas le volume.
- Variables sensibles attendues : `DISCORD_TOKEN`, `OWNER_IDS`. Les réglages non secrets peuvent inclure `DATABASE_PATH`, `LOG_LEVEL` et, en environnement de test, `SYNC_GUILD_ID`.
- Activer dans le portail Discord seulement les intents nécessaires au code et accorder au bot les permissions minimales nécessaires.
- Toute modification de documentation sous `docs/` doit rester passive : aucune dépendance nouvelle, aucun script de build, aucun changement de configuration Railway ni de code de démarrage requis par cette documentation.
- Avant chaque déploiement : installer les dépendances, compiler le code, exécuter les tests, construire l’image de déploiement si le projet utilise Docker, puis examiner les logs Railway.

## 8. Critères d’acceptation d’une fonctionnalité

Une fonctionnalité est prête à être annoncée comme disponible lorsque :

1. Ses règles fonctionnelles et permissions sont écrites.
2. Son isolation par `guild_id` est assurée et testée.
3. Les erreurs, limites, concurrence et abus raisonnables sont gérés.
4. Les opérations sensibles sont transactionnelles et auditées.
5. Les tests automatisés réussissent.
6. Le registre de commandes et l’aide reflètent le comportement réel.
7. Si la fonctionnalité dépend de Discord/Railway, elle a été testée dans un serveur/environnement dédié et son résultat est rapporté honnêtement.

## 9. Consignes aux futures IA et contributrices/contributeurs

- Commencer par lire ce cahier, `README.md`, `docs/command-registry.toml` et l’architecture actuelle.
- Inspecter le code réel avant d’affirmer qu’un module existe ou qu’un bug est corrigé.
- Garder les changements ciblés, ajouter ou mettre à jour des tests, et signaler les tests non exécutés.
- Ne jamais inclure de secret dans un commit ou dans une réponse.
- Ne pas réécrire les données existantes ni supprimer une base sans sauvegarde explicite.
- Ne pas promettre un redéploiement réussi sans preuve provenant des logs Railway.
- Préserver le cloisonnement multi-serveur, les contrôles d’accès et la compatibilité avec le démarrage Railway.
