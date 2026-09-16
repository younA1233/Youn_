# CROUS Watcher — Alertes logement multi-villes (Telegram)

Surveille plusieurs villes en même temps sur trouverunlogement.lescrous.fr
et poste un message dans un canal Telegram dès qu'un nouveau logement
apparaît, en précisant la ville concernée.

## Étape 1 — Créer le bot Telegram
1. Ouvre Telegram, cherche **@BotFather**
2. Envoie `/newbot`, donne un nom puis un pseudo finissant par `bot`
3. Note le **token** fourni (ex. `123456789:ABC-DEF...`)

## Étape 2 — Créer le canal et y ajouter le bot
1. Telegram → **Nouveau canal**
2. Paramètres du canal → **Administrateurs** → ajoute ton bot avec droit
   de publication

## Étape 3 — Récupérer le chat_id
1. Poste un message test dans le canal
2. Va sur `https://api.telegram.org/bot<TON_TOKEN>/getUpdates` dans un
   navigateur
3. Repère `"chat":{"id":-100xxxxxxxxxx, ...}` → c'est ton `chat_id`

## Étape 4 — Préparer la liste des villes
Construis un JSON avec toutes tes villes, chacune avec son URL de
recherche CROUS (récupérée comme avant : recherche → zoom sur la zone →
« Rechercher dans cette zone » → copier l'URL) :

```json
[
  {"name": "Grenoble", "url": "https://trouverunlogement.lescrous.fr/tools/XX/search?bounds=..."},
  {"name": "Paris", "url": "https://trouverunlogement.lescrous.fr/tools/XX/search?bounds=..."},
  {"name": "Lyon", "url": "https://trouverunlogement.lescrous.fr/tools/XX/search?bounds=..."}
]
```

Garde ce JSON de côté (sur une seule ligne ou pas, peu importe) pour
l'étape 6.

## Étape 5 — Créer un nouveau dépôt GitHub (séparé de l'ancien)
1. **New repository** → nom différent (ex. `crous-watcher-telegram`) → **Public**
2. Uploade les 5 fichiers de ce dossier :
   - à la racine : `check_crous.py`, `requirements.txt`, `seen.json`, `README.md`
   - dans `.github/workflows/` : `check.yml`
3. **Settings → Actions → General → Workflow permissions** →
   **"Read and write permissions"** → Save

## Étape 6 — Ajouter les secrets
Dans **Settings → Secrets and variables → Actions**, ajoute 3 secrets :

| Nom du secret        | Valeur                              |
|-----------------------|--------------------------------------|
| `TELEGRAM_BOT_TOKEN`  | le token donné par BotFather         |
| `TELEGRAM_CHAT_ID`    | l'ID récupéré à l'étape 3            |
| `CITIES_JSON`         | le JSON complet de l'étape 4         |

## Étape 7 — Tester
Onglet **Actions** → **"Check CROUS Multi-villes"** → **Run workflow**.
Tu dois recevoir dans le canal un message
« ✅ Surveillance active pour : Grenoble, Paris, Lyon » (ou tes villes).

Ensuite ça tourne tout seul toutes les heures, pour toutes les villes.

## Limites
- Sans compte connecté (DSE), seule une partie de l'offre publique est
  visible — le bot est un signal d'alerte, pas une vue complète.
- Le bot ne réserve rien — ça reste à faire manuellement sur
  MesServices.etudiant.gouv.fr.
- Plus tu ajoutes de villes, plus chaque cycle de vérification prend du
  temps (le script boucle sur toutes les villes toutes les 30s) — au-delà
  d'une dizaine de villes, ça reste gérable mais à surveiller.
