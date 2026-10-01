# Alerte réassort – LEGO Astro Bot (PlayStation Direct)

Vérifie toutes les 15 minutes, dans le cloud (GitHub Actions, gratuit), si le
LEGO Astro Bot est de nouveau achetable sur PlayStation Direct, et envoie une
notification push sur ton téléphone dès qu'il revient. Aucun ordinateur à
laisser allumé.

## Mise en place (10 minutes)

### 1. Notifications sur le téléphone (ntfy)
1. Installe l'app **ntfy** (iOS / Android, gratuite, sans compte).
2. Touche « + » et abonne-toi à un nom de sujet difficile à deviner,
   par exemple `astrobot-mathieu-7f3k92` (n'importe qui connaissant ce nom
   peut lire les messages, donc évite un nom trop simple).

### 2. Dépôt GitHub
1. Crée un dépôt **public** sur GitHub (les minutes Actions sont illimitées
   sur un dépôt public ; en privé, 2 000 min/mois suffisent à peine pour un
   check toutes les 15 min). Le nom du sujet ntfy reste secret, lui.
2. Dépose les fichiers ainsi :
   ```
   check_stock.py
   README.md
   .github/workflows/stock-alert.yml
   ```
   (le fichier `stock-alert.yml` doit être dans le dossier `.github/workflows/`)

### 3. Secret
Dans le dépôt : **Settings → Secrets and variables → Actions → New repository
secret**
- Nom : `NTFY_TOPIC`
- Valeur : le nom du sujet choisi à l'étape 1

### 4. Test
Onglet **Actions → Alerte stock LEGO Astro Bot → Run workflow**, coche
« Envoyer une notification de test », lance.
- Tu dois recevoir la notif de test sur ton téléphone.
- Dans le résumé du run, l'artefact **capture** montre ce que le robot a vu.
- Le fichier `state.json` apparaît dans le dépôt avec le statut lu
  (normalement `out_of_stock` aujourd'hui).

Ensuite, ça tourne tout seul.

## Ce que tu recevras
- 🎉 **Retour en stock** (priorité max) : touche la notif pour ouvrir la page.
- ⚠️ **Statut illisible** (discret, une seule fois) : le site a probablement
  bloqué le robot. Regarde la capture dans le dernier run.
- Repassage en rupture, si ça arrive.

## Bon à savoir
- GitHub peut retarder les tâches planifiées de quelques minutes aux heures
  chargées.
- GitHub désactive les tâches planifiées après 60 jours sans activité sur le
  dépôt : il suffit de cliquer « Enable workflow » s'il te le signale par mail.
- Pour arrêter : Actions → le workflow → « … » → **Disable workflow**.
- Pour surveiller un autre produit : change `PRODUCT_URL` et `PRODUCT_NAME`
  en haut de `check_stock.py`.
