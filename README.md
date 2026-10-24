# AlgoClair

Site bilingue (FR/EN) sur les algorithmes des réseaux sociaux, qui vend le guide PDF « Décoder l'algorithme » (7 €).

- `content/<langue>/*.html` : articles, page de vente et pages légales (fragments avec un en-tête JSON).
- `python3 build.py` : génère le site dans `docs/` (GitHub Pages : branche main, dossier /docs).
- `WORKER_URL` dans `build.py` : adresse du serveur de paiement. Tant qu'elle est vide, le bouton affiche « Disponible très bientôt ».
- Le guide payant (texte et PDF) n'est pas dans ce dépôt public : il reste dans les fichiers privés du projet, et seul le serveur de paiement livre les PDF.
