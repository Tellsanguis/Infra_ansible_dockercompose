#!/usr/bin/env python3
import docker
import yaml
import os
import json
import requests
from bs4 import BeautifulSoup

client = docker.from_env()
containers = client.containers.list()
output = {}

print(f"[•] Détection de {len(containers)} conteneur(s)...\n")

override_path = "/app/config/icon_overrides.json"
overrides = {}

# Charger les overrides si présents
if os.path.exists(override_path):
    with open(override_path, "r", encoding="utf-8") as f:
        overrides = json.load(f)

def extract_image_name(image):
    name = image.split("/")[-1]
    return name.split(":")[0] if ":" in name else name

def find_favicon(url, project_name, image_name):
    print(f"[→] Recherche favicon pour {url}")

    # Override manuel ?
    if project_name in overrides and overrides[project_name]:
        print(f"[✓] Favicon forcé depuis override : {overrides[project_name]}")
        return overrides[project_name]

    icon_url = None
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        icons = soup.find_all("link", rel=lambda x: x and 'icon' in x.lower())
        if icons:
            href = icons[0].get("href")
            if href:
                icon_url = href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
                print(f"[✓] Favicon trouvé via HTML : {icon_url}")
                return icon_url
        else:
            print("[✗] Aucun favicon trouvé dans HTML")
    except Exception:
        print(f"[✗] Impossible de charger HTML depuis {url}")

    test_favicon = f"{url.rstrip('/')}/favicon.ico"
    try:
        r = requests.get(test_favicon, timeout=5)
        if r.ok:
            print(f"[✓] Favicon trouvé via /favicon.ico : {test_favicon}")
            return test_favicon
    except:
        pass

    github_icon = f"https://raw.githubusercontent.com/selfhst/icons/refs/heads/main/png/{project_name}.png"
    try:
        r = requests.get(github_icon, timeout=5)
        if r.ok:
            print(f"[✓] Favicon fallback via GitHub (project_name) : {github_icon}")
            return github_icon
    except:
        print(f"[✗] Pas d’icône GitHub pour {project_name}")

    github_icon = f"https://raw.githubusercontent.com/selfhst/icons/refs/heads/main/png/{image_name}.png"
    try:
        r = requests.get(github_icon, timeout=5)
        if r.ok:
            print(f"[✓] Favicon fallback via GitHub (image) : {github_icon}")
            return github_icon
    except:
        print(f"[✗] Pas d’icône GitHub pour {image_name}")

    print("[✗] Aucun favicon disponible\n")
    return None

for container in containers:
    labels = container.labels
    name = container.name
    image_name = extract_image_name(container.image.tags[0]) if container.image.tags else container.image.short_id
    project_name = labels.get("com.docker.compose.project", name).lower()

    print(f"[•] Analyse du conteneur : {name} (projet : {project_name})")

    domain = None
    for key, value in labels.items():
        if key.startswith(f"traefik.http.routers.{project_name}-prod.rule") and "Host(`" in value:
            domain = value.split("Host(`")[1].split("`)")[0]
            break

    if domain:
        url = f"https://{domain}"
        icon = find_favicon(url, project_name, image_name)

        output[name] = {
            "name": project_name.capitalize(),
            "url": url,
            "icon": icon or "mdi:web",
            "hide": False
        }

        if project_name not in overrides:
            overrides[project_name] = ""

        print(f"[✓] Conteneur ajouté : {project_name} → {url}\n")
    else:
        print("[!] Aucune règle Traefik -prod trouvée pour ce conteneur.\n")

# Générer fichiers
os.makedirs("/output", exist_ok=True)

with open("/output/containers.yml", "w", encoding="utf-8") as f:
    yaml.dump({"containers": output}, f, sort_keys=False)

with open(override_path, "w", encoding="utf-8") as f:
    json.dump(overrides, f, indent=2, ensure_ascii=False)

print("✅ Fichier containers.yml généré : /output/containers.yml")
print(f"✅ Fichier overrides mis à jour : {override_path}")
