# ❄️ Emilia Frost — Bot-Hosting

Bot Discord Python 3.11+ (`discord.py` 2.4+), SQLite, réponses aux couleurs d’Emilia Frost et commandes en français. Les commandes principales sont organisées en groupes utilisables avec `+` et `/`.

## Installation

1. Décompresse le ZIP et ouvre le dossier du bot.
2. Installe Python 3.11 ou plus récent, puis lance `pip install -r requirements.txt`.
3. Copie `.env.example` vers `.env` en local, puis configure les variables ci-dessous. Sur un hébergeur, utilise plutôt son panneau de variables secrètes.
4. Active **Message Content Intent** et **Server Members Intent** dans le portail Discord Developer, et autorise l’installation des commandes d’application pour le bot.
5. Lance `python main.py`.
6. Garde le dossier `database/` sur un stockage persistant.
7. Sur Bot-Hosting, règle `DISCORD_TOKEN` dans le panneau des variables secrètes. N’ajoute jamais le vrai token au ZIP.

### Variables indispensables

- `DISCORD_TOKEN` : token du bot, à garder secret.
- `DATABASE_PATH=database/bot.db` : base persistante.
- `XP_COOLDOWN_SECONDS=60` : délai entre deux gains d’XP de chat (10 à 3600 secondes, séparé pour chaque serveur).
- `WINNER_ID` : **identifiant numérique Discord exact du propriétaire WINNERMUSK**. Les commandes privées WINNERMUSK sont bloquées tant que cet identifiant n’est pas configuré. Le nom d’utilisateur seul ne suffit pas.

## Préfixes

- Les commandes texte utilisent `+` pour les membres, le staff et les administrateurs; les permissions sensibles restent vérifiées commande par commande.
- Chaque commande texte dispose aussi d’une route slash : directement ou dans son groupe de fonction (par exemple `+balance` et `/eco balance`).
- `+help [catégorie]` et `/help` affichent d’abord les catégories; donne une catégorie pour voir les commandes correspondantes.
- En cas d’argument manquant ou mal formé, le bot affiche le format attendu, les arguments et un exemple.
- Les réponses du bot et des boutons utilisent des embeds; les refus d’interaction restent privés.
- Configure le rôle staff avec `+setup staff @rôle` ou `/setup staff`.
- Discord affiche son indicateur d’écriture/chargement pendant l’exécution des commandes.

## Commandes principales

### Économie et progression
`+eco balance`, `+eco daily`, `+eco work`, `+eco pay`, `+eco deposit`, `+eco withdraw`, `+eco mine`, `+eco top`, `+eco profile`, `+eco shop`, `+eco buy`, `+eco inventory`, `+eco loan`, `+social quests`, `+social pets`. Les variantes slash correspondantes apparaissent dans l’autocomplétion Discord.

### Boutiques, équipement et objets
- `+eco markets [all|regular|rare|black|equipment]`
- `+eco marketbuy ID`, `+social inventoryplus`
- Administrateur : `+admin marketadd boutique prix coins|mf stock Nom|description`, `+admin marketpromo ID pourcentage`, `+admin marketrotate [all|regular|rare|black|equipment]`
- Coffres à 5 raretés : Commun, Rare, Épique, Légendaire, Mythique.

### Raids, courses et biens
- Raid : `+games raid create nom_du_boss PV récompense`, `+games raid join`, `+games raid attack`
- Salon d’annonces : `+admin raidchannel #salon`
- Courses : `+games race create`, `+games race join nom_véhicule`, `+games race finish`
- Enchères : `+games auction-list`, `+games auction-create prix nom`, `+games auction-bid ID montant`, `+games auction-finish ID`
- Patrimoine : `+social assets`, `+admin assetvalue @membre type nom valeur`
- WINNERMUSK : `+winner store`, `+winner buy ID`, `+winner assets`, `+winner sell type Nom exact`, `+winner repair type Nom exact`.

### WINNERMUSK — propriétaire uniquement
Une fois `WINNER_ID` configuré :
- `+winner add voiture|moto|maison prix stock Nom|description`
- `+winner gift @membre voiture|moto|maison Nom exact`
- `+winner remove ID`, `+winner stock ID stock`, `+winner media ID URL`
- `+winner ledger`, `+winner invest @membre montant part`, `+winner payout montant`

Les joueurs peuvent acheter les articles publiés dans le catalogue. Les commandes de gestion et de cadeau sont contrôlées par identifiant numérique, pas par nom d’utilisateur ni par simple permission administrateur.

### Gouvernement et économie avancée
- `+events government show`
- `+events government nominate president @membre`
- `+events government election president|premierministre|mafia`
- `+events government vote ID @candidat`, `+events vote`, `+events limits president|premierministre richesse popularité niveau`
- Seuils par défaut : Président Top 5 richesse, Top 7 popularité et Top 10 niveaux. Pour Premier ministre et Chef de la Mafia, les seuils proposés par défaut sont Top 10 richesse, Top 15 popularité, Top 20 niveaux; ils sont modifiables avec `+govlimits premierministre richesse popularité niveau`.
- `+social tradeoffer @membre montant [type:nom,type:nom]`, `+social tradeaccept ID`, `+social traderefuse ID`
- `+eco loan montant`, `+eco myloan`; prélèvement automatique à échéance, dette restante conservée.
- `+admin journalchannel #salon`, `+admin journal`

### Invitations, accueil, événements
- `+social invites [@membre]`, `+admin invite-reward montant`, `+admin invite-role seuil @rôle`
- `+admin welcome #salon`
- `+events active`, `+events claim halloween|winterfest|spring|anniversary`
- `+events start halloween|winterfest|spring|anniversary jours`
- Le code des événements saisonniers est isolé dans `cogs/seasonal_events.py`; retirer ce module n’efface pas les Crédits déjà gagnés.

### Modération, tickets et aide
- `+admin automod spam|links|invites|mentions|caps|flood on|off`
- Modération : `+moderation warn`, `+moderation warnings`, `+moderation purge`, `+moderation lock`, `+moderation unlock`.
- Tickets : `+tickets open help|signalement|partenariat|staff`, `+tickets claim`, `+tickets transfer @staff`, `+tickets close`. La fermeture envoie une demande de note en DM si le membre accepte les messages privés.
- Giveaways : `+giveaways create durée_secondes nombre_gagnants prix`, `+giveaways end ID_message`, `+giveaways reroll ID_message`, `+giveaways claim ID_message`.

## Configuration Discord nécessaire

- Pour les tickets : Gérer les salons; configure la catégorie avec `+ticketsetup`.
- Pour rôles et progression staff : Gérer les rôles, et le rôle du bot au-dessus des rôles qu’il attribue.
- Pour le suivi des invitations : permission **Gérer le serveur** afin de lire les utilisations des invitations.
- Pour le journal : configure le salon de logs dans la base via `+setlog #salon`.

## Économie par serveur et migration de l’ancienne base

- Les comptes, achats, soldes, XP, maisons, véhicules, catalogues WINNERMUSK, boutique classique et cooldowns utilisent le serveur courant.
- Une ancienne base partagée ne peut pas attribuer correctement ses soldes à plusieurs serveurs sans inventer l’origine. Le programme en crée donc d’abord une sauvegarde, puis conserve les anciennes tables globales sous des noms `legacy_*_global`; les nouveaux comptes par serveur démarrent à zéro.
- La migration n’est pas lancée silencieusement. Si une ancienne base est détectée, le bot s’arrête sans rien changer tant que `CONFIRM_LEGACY_ECONOMY_MIGRATION=YES` n’a pas été défini après sauvegarde et lecture de `BOT_HOSTING_SETUP.md`. Tickets, rôles, paramètres de serveur et journaux ne sont pas réinitialisés.
- La vidéo ne peut pas être garantie en lecture intégrée dans un embed Discord. `+winnermedia` permet de lier une animation ou une vidéo; les images/GIF directs peuvent être affichés dans l’embed.
- Les enchères et certains transferts de biens avancés ont besoin de tests réels supplémentaires.
- Les raids ont un boss à PV, attaques, contre-attaques et récompenses proportionnelles; il n’y a pas encore d’arbres de compétences complets ni d’animations dédiées.
- L’auto-mod propose des règles de base, mais n’est pas un filtre linguistique complet et n’applique pas encore une échelle automatique de sanctions graduées.
- Les invitations dépendent des permissions Discord et du cache des invitations; certaines entrées non attribuables ne peuvent pas être créditées avec certitude.
- Le bot n’a pas été connecté à Discord dans l’environnement de création. Les commandes slash, permissions, DM, boutons, intents et hébergement doivent encore être validés sur un serveur privé.
