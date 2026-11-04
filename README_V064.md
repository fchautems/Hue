# Hue Lab v0.6.4 — Parcours de l'historique

Dans l'onglet **Historique**, les 40 événements les plus récents s'affichent comme avant.
Les boutons **Plus anciens** et **Plus récents** permettent de parcourir les autres
événements sans ouvrir les fichiers CSV du Raspberry.

- Le bouton **Actualiser** revient à la première page.
- L'actualisation automatique toutes les 15 secondes n'agit que sur la première page : les archives ne bougent pas pendant la lecture.
- Les données restent locales : ni Internet ni commande Hue n'interviennent.
- Les noms de lampes sont rendus comme texte pour éviter toute injection HTML.
- L'ancienne API reste compatible : sans paramètre offset, le comportement ne change pas.
- Le navigateur charge 41 lignes pour en montrer 40 et savoir s'il existe une page plus ancienne.
- L'accès est plafonné à 10 000 événements de décalage pour limiter l'utilisation mémoire. Les événements archivés ne sont pas effacés.

## Tests logiciels

GitHub Actions : suite Python complète, tests de pagination avec horodatages identiques,
contrat API en lecture seule et simulation Node des boutons/rafraîchissements.
Le Raspberry et le pont Hue réels restent à vérifier.

## Essai

1. Depuis Hue Lab, ouvrir **Mises à jour** et installer la version.
2. Ouvrir **Historique**, cliquer **Plus anciens**, puis **Plus récents**.
3. Vérifier qu'une page d'archives ne saute pas automatiquement sur la première page.
4. Cliquer **Actualiser** pour retrouver les 40 dernières observations.

