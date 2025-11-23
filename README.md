# Homeserver Infrastructure

Infrastructure as Code (IaC) pour provisionner un homeserver Ubuntu avec Ansible et Docker Compose.

## Prérequis

- Ansible 2.15+
- Accès SSH au serveur cible
- Python 3.x sur la machine de contrôle

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
              ┌───────────▼───────────┐
              │   Traefik Public      │ ← Reverse proxy (192.168.1.2)
              │   + CrowdSec Bouncer  │   SSL via Cloudflare DNS
              └───────────┬───────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
    ▼                     ▼                     ▼
┌────────┐          ┌──────────┐         ┌──────────┐
│Services│          │ Services │         │ Services │
│Publics │          │ Protégés │         │  Locaux  │
└────────┘          │(TinyAuth)│         └──────────┘
                    └──────────┘               │
                                               │
                               ┌───────────────▼───────────┐
                               │   Traefik Private         │
                               │   (192.168.1.3)           │
                               └───────────────────────────┘
```

### Rôles Ansible

| Rôle | Description |
|------|-------------|
| `common` | Paquets de base, dnsmasq (DNS local `*.local.tellserv.fr`), firewalld |
| `cockpit` | Interface web d'administration serveur |
| `docker` | Docker CE, réseau `traefik_network` |
| `services` | Synchronisation et déploiement des stacks Docker |

### Services déployés

**Infrastructure :** Traefik, CrowdSec, Watchtower, Autoheal, Beszel, Uptime-Kuma, Dockge, Kopia

**Productivité :** Vaultwarden, Vikunja, Paperless-ngx, Kavita, FreshRSS, SearXNG

**Media :** Plex, Photoprism, Audiobookshelf, qBittorrent

**Autres :** Gotify, Glance, Ghost (blog), Mobilizon, EteSync

## Installation

### 1. Configuration de l'inventaire

Modifiez `inventory/hosts.yml` avec l'IP et l'utilisateur SSH de votre serveur :

```yaml
all:
  children:
    homeserver:
      hosts:
        192.168.x.x:
          ansible_user: votre_utilisateur
          ansible_ssh_private_key_file: ~/.ssh/votre_cle
```

### 2. Configuration des secrets

```bash
# Copier le fichier d'exemple
cp vars/secrets.yml.example vars/secrets.yml

# Éditer avec vos vraies valeurs
nano vars/secrets.yml

# Chiffrer avec Ansible Vault
ansible-vault encrypt vars/secrets.yml
```

### 3. Exécution

```bash
# Provisionnement complet
ansible-playbook -i inventory/hosts.yml playbook.yml --ask-vault-pass

# Générer uniquement les fichiers .env (sans déployer)
ansible-playbook -i inventory/hosts.yml playbook.yml --tags env --ask-vault-pass

# Déployer un service spécifique
ansible-playbook -i inventory/hosts.yml playbook.yml --tags traefik --ask-vault-pass
```

## Structure du projet

```
.
├── inventory/
│   └── hosts.yml           # Inventaire des serveurs
├── roles/
│   ├── common/             # Configuration système de base
│   ├── cockpit/            # Interface web admin
│   ├── docker/             # Installation Docker
│   └── services/           # Déploiement des stacks
├── stacks/                 # Docker Compose projects
│   ├── traefik/
│   ├── vaultwarden/
│   └── ...
├── templates/
│   └── env/                # Templates .env.j2 (secrets)
├── vars/
│   ├── secrets.yml         # Secrets chiffrés (Vault)
│   └── secrets.yml.example # Template des secrets
└── playbook.yml            # Playbook principal
```

## Ajout d'un nouveau service

1. Créer `stacks/<service>/compose.yml`
2. Ajouter les labels Traefik pour le routage
3. Si secrets nécessaires : créer `templates/env/<service>.env.j2`
4. Ajouter le service dans `roles/services/tasks/main.yml`

## Sécurité

- **Secrets** : Tous les secrets sont gérés via Ansible Vault
- **CrowdSec** : Protection IPS avec blocage automatique
- **TinyAuth** : Authentification OAuth pour les services sensibles
- **Firewalld** : Pare-feu configuré automatiquement
- **TLS** : Certificats Let's Encrypt via Cloudflare DNS challenge

## CI/CD

Le CI/CD n'est pas implémenté dans ce dépôt. Le projet migre vers [Forgejo](https://forgejo.tellserv.fr/Tellsanguis/Homelab).

Une approche CI/CD possible :
- **Forgejo Runner** pour l'exécution des pipelines
- **Secrets Forgejo** pour l'IP serveur et l'utilisateur SSH (génération de `inventory/hosts.yml`)
- **Renovate Bot** pour les mises à jour d'images Docker via PR automatiques (alternative à Watchtower)

## License

MIT License - voir [LICENSE](LICENSE)
