# ❄️ Emilia Frost v100

Base Python `discord.py` 2.x en français, identité bleu glacier et violet pastel. Cette branche constitue une fondation exécutable et documente les limites : elle **n’implémente pas encore tout le cahier maître**.

## Fonctions actuellement présentes dans le code

- Commandes hybrides slash et préfixe pour aide, solde, daily, work, transfert local, banque, dépôt/retrait et classement.
- Préfixes publics `!`, staff `+`, et propriétaire `w.` reconnus par le bot ; chaque commande reste soumise à ses contrôles. Les commandes `w.` ne sont pas encore développées.
- Comptes SQLite isolés par serveur (`guild_id`), mode WAL, contraintes de soldes non négatifs et journal des mouvements.
- Récompenses quotidiennes/travail, transferts et mouvements bancaires protégés contre le double clic/la concurrence par transactions SQLite.
- Modération avec hiérarchie du membre et du bot vérifiée, avertissements historisés, timeout, kick, purge, configuration des logs, role-ban interne `+ban` et ban Discord natif séparé `+discordban`.

## Éléments du cahier maître encore absents

Familles, tickets, prison de jeu, COFFRESMUSK, WINNERMUSK, véhicules, animaux, gouvernement, élections, missions, événements, taxes/intérêts, transferts interserveurs, dashboard, sauvegardes externes et autres modules ne sont **pas** encore implémentés. Les commandes non présentes ne doivent pas être présentées aux membres comme disponibles. Le classement actuel est fondé sur les fonds liquides, pas sur les biens.

## Déploiement Railway

1. Crée un service Railway depuis la branche `copilot/emilia-frost-v100-foundation`.
2. Ajoute les variables Railway `DISCORD_TOKEN` (secret), `OWNER_IDS` (ID Discord numérique du propriétaire) et `DATABASE_PATH=/data/emilia_frost.db`.
3. Ajoute un volume persistant monté sur `/data` afin de conserver la base au redémarrage.
4. Dans Discord Developer Portal, active **Message Content Intent** et **Server Members Intent**. Invite le bot avec `applications.commands`, `Send Messages`, `Embed Links`, `Read Message History`; pour la modération, accorde seulement les permissions nécessaires. Place le rôle du bot au-dessus des rôles à gérer.
5. Railway installe `requirements.txt` et lance `python main.py`. Vérifie les logs, puis teste `/aide`, `!daily`, `/balance` et les commandes staff sur un serveur privé.
6. Configure `+setlog #salon` et `+setbanrole @rôle` avant d’utiliser les journaux ou `+ban`.

Ne partage jamais le token du bot. Si exposé, régénère-le dans le Developer Portal. Une base sans volume persistant peut être perdue lors d’un redéploiement.

## Lancement local

```bash
python -m venv .venv
source .venv/bin/activate  # Windows : .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# Renseigner les variables puis :
python main.py
```

L’archive finale ne devra être préparée qu’après audit, tests et demande explicite « Fais le ZIP ».
