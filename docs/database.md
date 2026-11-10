# Architecture de la base Emilia Frost

Le runtime conserve pour l’instant un point d’entrée historique `database.py` afin de limiter les ruptures, tandis que les prochaines évolutions sont organisées dans `database/migrations/`.

Schéma initial version 1 : `guild_settings`, `economy_accounts`, `transactions`, `moderation_cases` et `role_bans`. Toutes les tables contenant des données communautaires portent `guild_id`. Les comptes utilisent une clé composée `(guild_id, user_id)`.

Avant une migration de base existante : sauvegarder le fichier original, migrer une copie, comparer les comptages avant/après et conserver un rapport. Aucun script de migration destructive ne doit écraser `bot.db`.
