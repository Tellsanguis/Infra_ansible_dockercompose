# Mises à jour du serveur

## 2025-06-01 - Changement d'infra : 2 instances Traefik, une par interface réseau (Interne / Externe).
Une instance Traefik permet d'exposer sur *.tellserv.fr et l'autre sert pour les services externes afin de permettre un meilleur cloisonnement.

## 2025-05-24 - Glance remplace Flame : Nouveau dashboard, détection auto des services, widget Plex.
Ajout d’un script pour détecter automatiquement les services exposés, et intégration d’un widget Plex affichant les différentes bibliothèques et leur nombre de médias.

## 2025-05-23 - Nouvelle collection Plex : Films non vus choisis au hasard.
Une collection aléatoire a été ajoutée sur Plex, permettant de voir un film non vu encore.

## 2025-05-09 - Relance des services restants : Minecraft, Photoprism...
Les derniers services encore non fonctionnels, comme le serveur Minecraft, sont relancés.

## 2025-05-07 - Notifications via Gotify : Mise en place d’un système d’alertes centralisé.
Mise en place du système de notifications centralisé avec Gotify.

## 2025-05-06 - Migration vers Proxmox : Serveur déplacé dans une VM Proxmox.
Migration complète du serveur principal dans une machine virtuelle sous Proxmox.

