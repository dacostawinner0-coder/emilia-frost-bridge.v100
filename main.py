"""Point d'entrée (python main.py).

emilia_frost.py définit le bot et ses commandes de base.
emilia_extra.py ajoute les commandes manquantes, le routeur de préfixes,
l'aide, la vérification à l'arrivée, etc. Il doit être importé AVANT
de démarrer le bot pour que tout s'enregistre.
"""
import emilia_frost
import emilia_extra  # noqa: F401  (effets de bord : commandes, listeners, checks)

if __name__ == "__main__":
    emilia_extra.main()
