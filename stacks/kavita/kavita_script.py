#!/usr/bin/env python3
import os
import shutil
import subprocess
import logging
import time
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import threading

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Chemins de base
BASE_PATH = "/mnt/storage/kavita"
DOWNLOAD_DIR = f"{BASE_PATH}/download"
TO_CONVERT_DIR = f"{BASE_PATH}/to_convert"
CBZ_CONVERT_DIR = f"{BASE_PATH}/cbz_convert"

# Chemins de destination
MANGA_DEST = f"{BASE_PATH}/scans/Mangas"
COMICS_DEST = f"{BASE_PATH}/scans/Comics"
BD_DEST = f"{BASE_PATH}/scans/BD"

# Chemins source après conversion
MANGA_SRC = f"{CBZ_CONVERT_DIR}/manga"
COMICS_SRC = f"{CBZ_CONVERT_DIR}/comics"
BD_SRC = f"{CBZ_CONVERT_DIR}/bd"

# Variables pour la détection de fichiers
detected_files = {}  # Dictionnaire pour suivre les fichiers détectés et leur stabilité
folder_files = {}    # Dictionnaire pour suivre les fichiers par dossier
files_to_process = [] # Liste des fichiers à traiter dans le cycle courant
processing_lock = threading.Lock()  # Verrou pour éviter des traitements concurrents
conversion_in_progress = False  # Indicateur pour suivre si une conversion est en cours

# Extensions à ignorer
IGNORED_EXTENSIONS = ['.parts']

def run_command(command, cwd=None):
    """Exécute une commande shell et affiche la sortie"""
    logging.info(f"Exécution de la commande: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.stdout:
            logging.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Erreur lors de l'exécution de la commande: {e}")
        if e.stdout:
            logging.info(e.stdout)
        if e.stderr:
            logging.error(e.stderr)
        return False

def pdf_to_cbz(pdf_path, output_dir):
    """Convertit un PDF en CBZ en utilisant pdftoppm et ZIP"""
    try:
        # Obtenir le nom de base du fichier (sans extension)
        pdf_name = os.path.basename(pdf_path)
        base_name = os.path.splitext(pdf_name)[0]
        output_cbz = os.path.join(output_dir, f"{base_name}.cbz")
        
        logging.info(f"Conversion du PDF: {pdf_name} en CBZ")
        
        # Créer un répertoire temporaire pour les images extraites
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convertir le PDF en images avec pdftoppm (partie de poppler-utils)
            # Traitement page par page avec une qualité réduite pour éviter les problèmes de mémoire
            pdftoppm_cmd = f"pdftoppm -jpeg -r 150 '{pdf_path}' '{temp_dir}/page'"
            if not run_command(pdftoppm_cmd):
                logging.error(f"Échec de l'extraction des images du PDF: {pdf_name}")
                return False
            
            # Vérifier que des images ont été extraites
            image_files = sorted([f for f in os.listdir(temp_dir) if f.endswith(('.jpg', '.jpeg'))])
            if not image_files:
                logging.error(f"Aucune image extraite du PDF: {pdf_name}")
                return False
            
            logging.info(f"Nombre de pages extraites du PDF: {len(image_files)}")
            
            # Créer un fichier CBZ (ZIP) contenant les images
            with zipfile.ZipFile(output_cbz, 'w') as zipf:
                for img_file in image_files:
                    img_path = os.path.join(temp_dir, img_file)
                    zipf.write(img_path, arcname=img_file)
            
            # Vérifier que le CBZ a été créé
            if not os.path.exists(output_cbz):
                logging.error(f"Échec de la création du CBZ: {output_cbz}")
                return False
            
            logging.info(f"Conversion réussie: {pdf_name} -> {output_cbz}")
            return True
    
    except Exception as e:
        logging.error(f"Erreur lors de la conversion du PDF {pdf_path}: {e}")
        return False

def convert_non_pdf_files(file_path, output_dir):
    """Convertit un fichier non-PDF avec cbconvert"""
    file_name = os.path.basename(file_path)
    logging.info(f"Conversion du fichier non-PDF: {file_name}")
    
    cmd = f"cbconvert convert --no-nonimage --outdir '{output_dir}' --quality 85 '{file_path}'"
    success = run_command(cmd)
    
    # Vérifier si la conversion a réussi en cherchant le fichier de sortie
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    expected_output = os.path.join(output_dir, f"{base_name}.cbz")
    
    if not os.path.exists(expected_output):
        logging.error(f"La conversion a échoué, aucun fichier de sortie trouvé pour: {file_name}")
        return False
    
    logging.info(f"Conversion réussie: {file_name} -> {expected_output}")
    return True

def convert_files():
    """Convertit les fichiers en CBZ"""
    global files_to_process
    
    logging.info("Début de la conversion des fichiers...")
    
    # Copier la liste des fichiers à traiter pour ce cycle
    with processing_lock:
        current_files = files_to_process.copy()
        logging.info(f"Traitement de {len(current_files)} fichiers dans ce cycle")
    
    # Si aucun fichier à traiter
    if not current_files:
        return True
    
    # Collecter tous les fichiers à traiter
    all_files = []
    for file_path in current_files:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            all_files.append(file_path)
    
    # Structure pour suivre la progression
    file_stats = {
        'total': len(all_files),
        'success': 0,
        'failed': 0
    }
    
    # Convertir chaque fichier individuellement
    converted_files = []
    
    for file_path in all_files:
        # Déterminer le répertoire de sortie
        rel_path = os.path.relpath(file_path, TO_CONVERT_DIR)
        output_dir = os.path.join(CBZ_CONVERT_DIR, os.path.dirname(rel_path))
        
        # Créer le dossier de sortie si nécessaire
        os.makedirs(output_dir, exist_ok=True)
        
        # Convertir le fichier en fonction de son type
        success = False
        if file_path.lower().endswith('.pdf'):
            # Utiliser notre fonction personnalisée pour convertir les PDF
            logging.info(f"Utilisation de la méthode personnalisée pour le PDF: {file_path}")
            success = pdf_to_cbz(file_path, output_dir)
        else:
            # Utiliser cbconvert pour les autres formats
            success = convert_non_pdf_files(file_path, output_dir)
        
        if success:
            converted_files.append(file_path)
            file_stats['success'] += 1
        else:
            file_stats['failed'] += 1
            logging.error(f"Échec de la conversion du fichier: {file_path}")
    
    # Mettre à jour la liste des fichiers à traiter (retirer ceux qui ont été convertis)
    with processing_lock:
        for file_path in converted_files:
            if file_path in files_to_process:
                files_to_process.remove(file_path)
    
    # Rapport de conversion
    logging.info(f"Conversion terminée: {file_stats['success']}/{file_stats['total']} fichiers convertis avec succès")
    
    # Si tous les fichiers ont été convertis avec succès, retourner True
    return file_stats['failed'] == 0

def clean_processed_files(processed_files):
    """Supprime uniquement les fichiers qui ont été traités avec succès"""
    logging.info(f"Nettoyage de {len(processed_files)} fichiers traités")
    
    for file_path in processed_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Fichier supprimé après traitement: {file_path}")
                
                # Supprimer les dossiers parents vides
                parent_dir = os.path.dirname(file_path)
                while parent_dir.startswith(TO_CONVERT_DIR) and os.path.exists(parent_dir) and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                    logging.info(f"Dossier vide supprimé: {parent_dir}")
                    parent_dir = os.path.dirname(parent_dir)
        except Exception as e:
            logging.error(f"Erreur lors de la suppression du fichier {file_path}: {e}")

def clean_to_convert_directory():
    """Supprime tous les fichiers du répertoire to_convert"""
    logging.info(f"Nettoyage du répertoire de conversion: {TO_CONVERT_DIR}")
    try:
        if os.path.exists(TO_CONVERT_DIR):
            for item in os.listdir(TO_CONVERT_DIR):
                path = os.path.join(TO_CONVERT_DIR, item)
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        return True
    except Exception as e:
        logging.error(f"Erreur lors du nettoyage du répertoire: {e}")
        return False

def rename_and_move(source_dir, dest_dir, category):
    """Renomme et déplace les fichiers d'une catégorie spécifique"""
    logging.info(f"Traitement de la catégorie: {category}")
    
    # Vérifier si le répertoire source existe
    if not os.path.exists(source_dir):
        logging.warning(f"Le répertoire source n'existe pas: {source_dir}")
        return True  # Non critique, continuez
    
    # Vérifier si le répertoire de destination existe, sinon le créer
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        logging.info(f"Répertoire de destination créé: {dest_dir}")
    
    # Renommer les fichiers dans chaque sous-dossier
    for item in os.listdir(source_dir):
        item_path = os.path.join(source_dir, item)
        if os.path.isdir(item_path):
            # Utiliser f2 pour renommer les fichiers
            cmd = 'f2 -r "{{p}} v{%02d}" -e -x'
            if not run_command(cmd, cwd=item_path):
                logging.error(f"Échec du renommage dans: {item_path}")
    
    # Déplacer les dossiers vers la destination
    for item in os.listdir(source_dir):
        item_path = os.path.join(source_dir, item)
        if os.path.isdir(item_path):
            dest_path = os.path.join(dest_dir, item)
            try:
                # Si le dossier de destination existe déjà, fusionner
                if os.path.exists(dest_path):
                    for file in os.listdir(item_path):
                        file_src = os.path.join(item_path, file)
                        file_dest = os.path.join(dest_path, file)
                        shutil.move(file_src, file_dest)
                    os.rmdir(item_path)
                else:
                    # Sinon, déplacer le dossier entier
                    shutil.move(item_path, dest_dir)
                logging.info(f"Déplacé: {item} vers {dest_dir}")
            except Exception as e:
                logging.error(f"Erreur lors du déplacement de {item}: {e}")
    
    return True

def process_convert_directory():
    """Traite les fichiers dans le répertoire to_convert"""
    global conversion_in_progress, files_to_process
    
    with processing_lock:
        if conversion_in_progress:
            return
        if not files_to_process:
            return
        conversion_in_progress = True
        current_batch = files_to_process.copy()
    
    try:
        logging.info("Début du traitement des fichiers à convertir...")
        
        # 1. Convertir les fichiers
        conversion_success = convert_files()
        
        # 2. Si la conversion a réussi, traiter les mangas, comics et BD
        if conversion_success:
            if rename_and_move(MANGA_SRC, MANGA_DEST, "Manga"):
                if rename_and_move(COMICS_SRC, COMICS_DEST, "Comics"):
                    rename_and_move(BD_SRC, BD_DEST, "BD")
            
            # 3. Nettoyer uniquement les fichiers traités avec succès
            clean_processed_files(current_batch)
            
            logging.info("Traitement terminé avec succès")
        else:
            logging.error("Échec de la conversion, certains fichiers n'ont pas été traités")
    
    except Exception as e:
        logging.error(f"Erreur pendant le traitement: {e}")
    finally:
        with processing_lock:
            conversion_in_progress = False

def should_ignore_file(file_path):
    """Détermine si un fichier doit être ignoré"""
    # Vérifier si l'extension du fichier est dans la liste des extensions à ignorer
    for ext in IGNORED_EXTENSIONS:
        if file_path.lower().endswith(ext):
            return True
    
    # Vérifier si le fichier contient .parts dans son chemin (cas des dossiers temporaires)
    if '.parts' in file_path:
        return True
    
    return False

def get_folder_path(file_path):
    """Obtient le chemin du dossier parent d'un fichier"""
    return os.path.dirname(file_path)

def update_folder_files():
    """Met à jour le dictionnaire des fichiers par dossier"""
    folder_files.clear()
    
    for file_path in detected_files:
        folder = get_folder_path(file_path)
        if folder not in folder_files:
            folder_files[folder] = []
        folder_files[folder].append(file_path)

def check_folder_stability(folder):
    """Vérifie si tous les fichiers d'un dossier sont stables"""
    if folder not in folder_files:
        return False
    
    for file_path in folder_files[folder]:
        if file_path in detected_files and not detected_files[file_path]['stable']:
            return False
    
    return True

def move_folder_to_convert(folder):
    """Déplace un dossier stable vers to_convert et retourne la liste des fichiers déplacés"""
    if not os.path.exists(folder):
        return []
    
    # Créer le dossier de destination s'il n'existe pas
    if not os.path.exists(TO_CONVERT_DIR):
        os.makedirs(TO_CONVERT_DIR, exist_ok=True)
    
    # Créer le sous-dossier de destination en conservant la structure
    rel_path = os.path.relpath(folder, DOWNLOAD_DIR)
    dest_folder = os.path.join(TO_CONVERT_DIR, rel_path)
    os.makedirs(os.path.dirname(dest_folder), exist_ok=True)
    
    moved_files = []
    try:
        # Déplacer tous les fichiers stables
        for file_path in folder_files[folder]:
            if file_path in detected_files and detected_files[file_path]['stable']:
                dest_file = os.path.join(TO_CONVERT_DIR, os.path.relpath(file_path, DOWNLOAD_DIR))
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                shutil.move(file_path, dest_file)
                moved_files.append(dest_file)
                logging.info(f"Déplacé le fichier stable vers to_convert: {file_path}")
                # Supprimer le fichier de notre suivi
                del detected_files[file_path]
        
        # Supprimer le dossier source s'il est vide
        if os.path.exists(folder) and not os.listdir(folder):
            os.rmdir(folder)
            logging.info(f"Dossier source supprimé car vide: {folder}")
        
        return moved_files
    except Exception as e:
        logging.error(f"Erreur lors du déplacement du dossier {folder} vers to_convert: {e}")
        return []

def process_stable_folders():
    """Traite les dossiers stables en les déplaçant vers to_convert"""
    global conversion_in_progress
    folders_to_process = []
    
    # Si une conversion est en cours, ne pas déplacer de nouveaux fichiers
    with processing_lock:
        if conversion_in_progress:
            logging.info("Une conversion est en cours, report du déplacement des dossiers stables")
            return
    
    # Identifier les dossiers stables
    for folder in folder_files:
        if check_folder_stability(folder):
            folders_to_process.append(folder)
    
    # Si aucun dossier stable, sortir
    if not folders_to_process:
        return
        
    # Déplacer les dossiers stables vers to_convert
    moved_files = []
    for folder in folders_to_process:
        files = move_folder_to_convert(folder)
        if files:
            moved_files.extend(files)
    
    # Mettre à jour la liste des fichiers à traiter
    with processing_lock:
        files_to_process.extend(moved_files)
    
    logging.info(f"Ajout de {len(moved_files)} fichiers à la liste de traitement")

def scan_download_directory():
    """Scanne le répertoire de téléchargement pour détecter les nouveaux fichiers et leur stabilité"""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        logging.info(f"Répertoire de téléchargement créé: {DOWNLOAD_DIR}")
        return
    
    current_time = datetime.now()
    
    # Parcourir récursivement tous les fichiers dans le répertoire de téléchargement
    for root, dirs, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Ignorer les fichiers spécifiés
            if should_ignore_file(file_path):
                continue
            
            # Si le fichier n'est pas déjà dans notre liste
            if file_path not in detected_files:
                file_size = os.path.getsize(file_path)
                detected_files[file_path] = {
                    'size': file_size,
                    'time': current_time,
                    'stable': False,
                    'stable_count': 0
                }
                logging.info(f"Nouveau fichier détecté: {file_path}")
            else:
                # Vérifier si la taille du fichier a changé
                current_size = os.path.getsize(file_path)
                if current_size != detected_files[file_path]['size']:
                    detected_files[file_path] = {
                        'size': current_size,
                        'time': current_time,
                        'stable': False,
                        'stable_count': 0
                    }
                    logging.info(f"Fichier modifié: {file_path}")
                elif not detected_files[file_path]['stable']:
                    # Incrémenter le compteur de stabilité
                    detected_files[file_path]['stable_count'] += 1
                    
                    # Marquer comme stable si la taille n'a pas changé pendant plusieurs vérifications
                    # (ici, après 5 vérifications consécutives, soit environ 150 secondes avec un intervalle de 30s)
                    if detected_files[file_path]['stable_count'] >= 5:
                        detected_files[file_path]['stable'] = True
                        logging.info(f"Fichier stable: {file_path}")
    
    # Supprimer les entrées pour les fichiers qui n'existent plus
    file_paths = set()
    for root, dirs, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            if not should_ignore_file(file_path):
                file_paths.add(file_path)
    
    deleted_files = [path for path in detected_files.keys() if path not in file_paths]
    for path in deleted_files:
        logging.info(f"Fichier supprimé ou déplacé: {path}")
        del detected_files[path]
    
    # Mettre à jour la liste des fichiers par dossier
    update_folder_files()

def check_to_convert_has_files():
    """Vérifie si des fichiers sont prêts à être traités"""
    with processing_lock:
        return len(files_to_process) > 0

def main():
    """Fonction principale de surveillance"""
    logging.info("Démarrage de la surveillance du répertoire de téléchargement...")
    logging.info(f"Extensions ignorées: {IGNORED_EXTENSIONS}")
    
    # Créer les répertoires nécessaires
    if not os.path.exists(TO_CONVERT_DIR):
        os.makedirs(TO_CONVERT_DIR, exist_ok=True)
    
    while True:
        try:
            # 1. Scanner le répertoire de téléchargement
            scan_download_directory()
            
            # 2. Traiter les dossiers stables (déplacer vers to_convert)
            process_stable_folders()
            
            # 3. Si des fichiers sont dans to_convert et qu'aucune conversion n'est en cours
            if check_to_convert_has_files() and not conversion_in_progress:
                # Lancer le processus de conversion
                threading.Thread(target=process_convert_directory, daemon=True).start()
            
            # Attendre 30 secondes avant la prochaine vérification
            time.sleep(30)
            
        except Exception as e:
            logging.error(f"Erreur durant la surveillance: {e}")
            time.sleep(60)  # Attendre en cas d'erreur

if __name__ == "__main__":
    main()