import pygame
import yt_dlp
import threading
import os
import sys
import io
import requests
import unicodedata
import urllib.request
import hashlib
from PIL import Image
import tkinter as tk
from tkinter import filedialog

# ===================== SYSTÈME DE MISE À JOUR AUTO =====================
# Remplace cette URL par l'URL "Raw" de ton fichier sur GitHub
GITHUB_RAW_URL = "https://raw.github.com/rusher-code-330/pgr-video/blob/main/video.py"

def check_for_updates():
    """Vérifie le dépôt GitHub, télécharge le nouveau code si modifié et redémarre."""
    print("Recherche de mises à jour sur GitHub...")
    try:
        # Télécharge la version en ligne (sans utiliser le cache)
        req = urllib.request.Request(GITHUB_RAW_URL, headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=5) as response:
            online_code = response.read()

        # Lit la version locale actuelle
        with open(__file__, 'rb') as f:
            local_code = f.read()

        # Compare les signatures (hash MD5) des deux codes
        if hashlib.md5(online_code).hexdigest() != hashlib.md5(local_code).hexdigest():
            print("Nouvelle version détectée ! Mise à jour en cours...")
            
            # Écrase le fichier actuel avec le nouveau code
            with open(__file__, 'wb') as f:
                f.write(online_code)
                
            print("Mise à jour terminée. Redémarrage de l'application...")
            
            # Quitte Pygame proprement avant le redémarrage
            pygame.quit()
            
            # Relance le script avec la nouvelle version
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print("Le logiciel est déjà à la dernière version.")
            
    except Exception as e:
        print(f"Impossible de vérifier les mises à jour : {e}")

# ===================== CONFIGURATION & GRAPHIC THEME =====================
pygame.init()
pygame.key.set_repeat(400, 35)

# Charte graphique "Minimal Carbon"
BG_COLOR = (10, 12, 18)         # Fond ultra-sombre
CARD_COLOR = (18, 22, 32)       # Conteneurs principaux
CARD_HOVER = (26, 32, 46)       # Éléments survolés
ACCENT = (0, 180, 216)          # Cyan Électrique
ACCENT_HOVER = (144, 224, 239)  # Cyan clair interactif
SUCCESS = (46, 213, 115)        # Vert Fluide
TEXT = (245, 246, 250)          # Blanc pur
GRAY = (116, 125, 140)          # Gris neutre secondary
BORDER_COLOR = (29, 36, 51)     # Bordures fines

WIDTH, HEIGHT = 1000, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PGR Downloader Ultra")

def get_font(size, bold=False):
    try:
        return pygame.font.SysFont("Segoe UI", size, bold)
    except:
        return pygame.font.Font(None, size)

f_tiny = get_font(13)
f_small = get_font(16)
f_med = get_font(19, True)
f_big = get_font(26, True)

# Dossier de téléchargement initial par défaut
download_folder = os.path.join(os.path.expanduser("~"), "Downloads", "PGR_Downloads")
os.makedirs(download_folder, exist_ok=True)

# Variables d'état globales
url_input = ""
status = "Prêt. En attente d'un lien valide."
is_loading_info = False
metadata = None
thumb_surface = None
progress_pct = 0.0
is_downloading = False

# Configuration du Menu Déroulant
dropdown_open = False
selected_opt_idx = 0  # Mode automatique (Max Qualité) par défaut
dropdown_scroll_index = 0
max_visible_items = 4

options = [
    {"label": "Qualité Maximale Réelle (8K / 4K / 1080p)", "fmt": "bestvideo+bestaudio/best", "ext": "mp4"},
    {"label": "Limiter à Full HD (1080p)", "fmt": "bestvideo[height<=1080]+bestaudio/best", "ext": "mp4"},
    {"label": "Limiter à HD (720p)", "fmt": "bestvideo[height<=720]+bestaudio/best", "ext": "mp4"},
    {"label": "Audio - FLAC (Haute Fidélité Lossless)", "fmt": "bestaudio/best", "ext": "flac"},
    {"label": "Audio - WAV (Format Studio non compressé)", "fmt": "bestaudio/best", "ext": "wav"},
    {"label": "Audio - MP3 (Standard Standard 320kbps)", "fmt": "bestaudio/best", "ext": "mp3"},
]

# ===================== LOGIQUE ANTI-CRASH TEXTE =====================

def clean_text(text):
    if not text: return ""
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    cleaned = []
    for char in text:
        cp = ord(char)
        if 32 <= cp <= 126 or cp in [233, 232, 224, 249, 231, 234, 235, 206, 207, 212, 214, 219, 220]:
            cleaned.append(char)
        else:
            cleaned.append("-")
    return "".join(cleaned).strip()

def safe_clipboard_get():
    try:
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        return str(text).strip()
    except:
        return ""

def change_download_folder():
    """ Ouvre une boîte de dialogue pour choisir le dossier de destination """
    global download_folder
    try:
        root = tk.Tk()
        root.withdraw()  # Masque la fenêtre principale Tkinter
        root.attributes("-topmost", True)  # Force la boîte de dialogue au premier plan
        selected_dir = filedialog.askdirectory(initialdir=download_folder, title="Choisir le dossier d'enregistrement")
        root.destroy()
        if selected_dir:
            download_folder = os.path.normpath(selected_dir)
    except Exception as e:
        pass

# ===================== ENGINE DE TÉLÉCHARGEMENT =====================

def fetch_metadata(url):
    global metadata, is_loading_info, status, thumb_surface
    is_loading_info = True
    thumb_surface = None
    status = "Analyse du lien en cours..."
    
    try:
        ydl_opts = {
            'quiet': True, 
            'noplaylist': True, 
            'extract_flat': False, 
            'skip_download': True,
            'extractor_args': {'youtube': {'player_client': ['web', 'default']}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info: raise Exception("Aucune réponse du serveur.")
            
            thumb_url = info.get('thumbnail')
            img_bytes = None
            if thumb_url:
                try:
                    res = requests.get(thumb_url, timeout=5)
                    if res.status_code == 200: img_bytes = res.content
                except: pass
            
            duration_sec = info.get('duration', 0)
            duration_str = f"{duration_sec // 60}:{duration_sec % 60:02d}" if duration_sec else "Flux Direct"

            metadata = {
                'title': clean_text(info.get('title', 'Vidéo sans titre')),
                'duration': duration_str,
                'img_bytes': img_bytes,
                'url': url
            }
            status = "Vidéo détectée et prête au téléchargement."
    except Exception as e:
        status = "Erreur : Impossible d'analyser ce lien."
        metadata = None
    is_loading_info = False

def download_hook(d):
    global progress_pct, status
    if d['status'] == 'downloading':
        try:
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                progress_pct = (downloaded / total) * 100
            else:
                p = d.get('_percent_str', '0%').replace('%', '').strip()
                progress_pct = float(p)
        except:
            pass
        status = f"Téléchargement : {progress_pct:.1f}%"
    elif d['status'] == 'finished':
        status = "Finalisation et assemblage du fichier..."

def run_download():
    global is_downloading, status, progress_pct, url_input, metadata, thumb_surface
    if not metadata: return
    
    is_downloading = True
    progress_pct = 0.0
    opt = options[selected_opt_idx]
    
    ydl_opts = {
        'format': opt['fmt'],
        'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
        'progress_hooks': [download_hook],
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['web', 'default']}}
    }
    
    if opt['ext'] in ['mp3', 'wav', 'flac']:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': opt['ext'],
            'preferredquality': '0' if opt['ext'] == 'flac' else '320',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([metadata['url']])
        status = "✓ Téléchargement terminé avec succès !"
        url_input = ""
        metadata = None
        thumb_surface = None
    except Exception as e:
        status = f"Erreur lors de l'enregistrement."
    
    is_downloading = False
    progress_pct = 0.0

# ===================== RENDU ET COMPOSANTS =====================

def draw_text(txt, font, color, x, y, center_x=False, max_w=None):
    cleaned = clean_text(txt)
    surf = font.render(cleaned, True, color)
    if max_w and surf.get_width() > max_w:
        for i in range(len(cleaned), 0, -1):
            surf = font.render(cleaned[:i] + "...", True, color)
            if surf.get_width() <= max_w: break
    rect = surf.get_rect(topleft=(x, y))
    if center_x: rect.centerx = x
    screen.blit(surf, rect)

# ===================== MAIN LOOP =====================

def main():
    global url_input, metadata, is_loading_info, selected_opt_idx, dropdown_open, status, thumb_surface, dropdown_scroll_index, progress_pct, download_folder
    
    clock = pygame.time.Clock()
    
    input_rect = pygame.Rect(50, 95, 900, 52)
    left_panel = pygame.Rect(50, 175, 430, 370)
    right_panel = pygame.Rect(520, 175, 430, 370)
    
    drop_rect = pygame.Rect(right_panel.x + 25, right_panel.y + 65, 380, 48)
    dl_btn = pygame.Rect(right_panel.x + 25, right_panel.y + 275, 380, 60)
    path_btn = pygame.Rect(WIDTH - 150, HEIGHT - 33, 100, 24)
    
    item_h = 42
    dropdown_view_h = max_visible_items * item_h

    while True:
        m_pos = pygame.mouse.get_pos()
        screen.fill(BG_COLOR)
        
        if metadata and metadata.get('img_bytes') and thumb_surface is None:
            try:
                img_data = Image.open(io.BytesIO(metadata['img_bytes'])).convert("RGB")
                img_data = img_data.resize((390, 220))
                thumb_surface = pygame.image.fromstring(img_data.tobytes(), img_data.size, "RGB")
            except:
                thumb_surface = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if dropdown_open:
                    if event.button == 4:
                        dropdown_scroll_index = max(0, dropdown_scroll_index - 1)
                    elif event.button == 5:
                        dropdown_scroll_index = min(len(options) - max_visible_items, dropdown_scroll_index + 1)
                    elif event.button == 1:
                        clicked_inside_item = False
                        for i in range(max_visible_items):
                            actual_idx = dropdown_scroll_index + i
                            if actual_idx >= len(options): break
                            item_rect = pygame.Rect(drop_rect.x, drop_rect.bottom + (i * item_h), drop_rect.width - 12, item_h)
                            if item_rect.collidepoint(event.pos):
                                selected_opt_idx = actual_idx
                                dropdown_open = False
                                clicked_inside_item = True
                                break
                        if not clicked_inside_item: dropdown_open = False
                else:
                    if event.button == 1:
                        if drop_rect.collidepoint(event.pos): 
                            dropdown_open = True
                        elif dl_btn.collidepoint(event.pos) and not is_downloading and metadata:
                            threading.Thread(target=run_download, daemon=True).start()
                        elif path_btn.collidepoint(event.pos) and not is_downloading:
                            change_download_folder()

            if event.type == pygame.KEYDOWN:
                if not is_downloading:
                    if event.key == pygame.K_BACKSPACE: url_input = url_input[:-1]
                    elif event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                        clip = safe_clipboard_get()
                        if clip.startswith("http"):
                            url_input = clip
                            threading.Thread(target=fetch_metadata, args=(url_input,), daemon=True).start()
                    elif event.key == pygame.K_RETURN:
                        if url_input.strip().startswith("http"):
                            threading.Thread(target=fetch_metadata, args=(url_input,), daemon=True).start()
                    else:
                        if event.unicode.isprintable(): url_input += event.unicode

        # --- RENDU INTERFACE GRAPHIQUE ---
        draw_text("PGR DOWNLOADER ULTRA", f_big, TEXT, 50, 35)
        
        pygame.draw.rect(screen, CARD_COLOR, input_rect, border_radius=8)
        bar_border = SUCCESS if metadata else (ACCENT if url_input else BORDER_COLOR)
        pygame.draw.rect(screen, bar_border, input_rect, 1, border_radius=8)
        
        display_text = url_input if url_input else "Collez votre lien vidéo ici (Ctrl+V) puis appuyez sur Entrée..."
        text_color = TEXT if url_input else GRAY
        draw_text(display_text, f_small, text_color, input_rect.x + 20, input_rect.y + 16, max_w=855)

        pygame.draw.rect(screen, CARD_COLOR, left_panel, border_radius=8)
        pygame.draw.rect(screen, BORDER_COLOR, left_panel, 1, border_radius=8)
        
        if is_loading_info:
            draw_text("Analyse du flux vidéo...", f_small, ACCENT, left_panel.centerx, left_panel.y + 160, center_x=True)
        elif metadata:
            if thumb_surface:
                screen.blit(thumb_surface, (left_panel.x + 20, left_panel.y + 20))
                pygame.draw.rect(screen, BORDER_COLOR, (left_panel.x + 20, left_panel.y + 20, 390, 220), 1)
            else:
                fallback_rect = pygame.Rect(left_panel.x + 20, left_panel.y + 20, 390, 220)
                pygame.draw.rect(screen, BG_COLOR, fallback_rect, border_radius=4)
                draw_text("Pas d'aperçu disponible", f_small, GRAY, fallback_rect.centerx, fallback_rect.centery - 10, center_x=True)
                
            draw_text(metadata['title'], f_small, TEXT, left_panel.x + 20, left_panel.y + 260, max_w=390)
            draw_text(f"Durée : {metadata['duration']}", f_tiny, GRAY, left_panel.x + 20, left_panel.y + 295)
            draw_text("Lien validé - Prêt", f_tiny, SUCCESS, left_panel.x + 20, left_panel.y + 320)
        else:
            draw_text("Aucun média chargé actuellement.", f_small, GRAY, left_panel.centerx, left_panel.y + 160, center_x=True)

        pygame.draw.rect(screen, CARD_COLOR, right_panel, border_radius=8)
        pygame.draw.rect(screen, BORDER_COLOR, right_panel, 1, border_radius=8)
        draw_text("Format de sortie :", f_small, GRAY, right_panel.x + 25, right_panel.y + 30)
        
        drop_bg = CARD_HOVER if drop_rect.collidepoint(m_pos) else BG_COLOR
        pygame.draw.rect(screen, drop_bg, drop_rect, border_radius=6)
        pygame.draw.rect(screen, BORDER_COLOR, drop_rect, 1, border_radius=6)
        draw_text(options[selected_opt_idx]['label'], f_small, TEXT, drop_rect.x + 15, drop_rect.y + 14)
        draw_text("v", f_tiny, ACCENT, drop_rect.right - 25, drop_rect.y + 14)

        draw_text("Statut du système :", f_tiny, GRAY, right_panel.x + 25, right_panel.y + 145)
        status_color = SUCCESS if "✓" in status else (ACCENT if is_downloading else TEXT)
        draw_text(status, f_small, status_color, right_panel.x + 25, right_panel.y + 170, max_w=380)
        
        bar_rect = pygame.Rect(right_panel.x + 25, right_panel.y + 215, 380, 8)
        pygame.draw.rect(screen, BG_COLOR, bar_rect, border_radius=4)
        if progress_pct > 0:
            current_width = int((progress_pct / 100.0) * bar_rect.width)
            current_width = max(0, min(current_width, bar_rect.width))
            if current_width > 0:
                pygame.draw.rect(screen, ACCENT, (bar_rect.x, bar_rect.y, current_width, bar_rect.height), border_radius=4)

        if not metadata: btn_color, txt_color = BORDER_COLOR, GRAY
        elif is_downloading: btn_color, txt_color = CARD_HOVER, GRAY
        else:
            btn_color = ACCENT_HOVER if dl_btn.collidepoint(m_pos) else ACCENT
            txt_color = BG_COLOR
            
        pygame.draw.rect(screen, btn_color, dl_btn, border_radius=6)
        dl_text_rendering = "PATIENTEZ..." if is_downloading else "TÉLÉCHARGER"
        draw_text(dl_text_rendering, f_med, txt_color, dl_btn.centerx, dl_btn.centery - 10, center_x=True)

        if dropdown_open:
            dropdown_panel = pygame.Rect(drop_rect.x, drop_rect.bottom, drop_rect.width, dropdown_view_h)
            pygame.draw.rect(screen, CARD_COLOR, dropdown_panel)
            pygame.draw.rect(screen, ACCENT, dropdown_panel, 1)
            
            for i in range(max_visible_items):
                actual_idx = dropdown_scroll_index + i
                if actual_idx >= len(options): break
                
                opt = options[actual_idx]
                item_rect = pygame.Rect(drop_rect.x, drop_rect.bottom + (i * item_h), drop_rect.width - 12, item_h)
                
                if item_rect.collidepoint(m_pos):
                    pygame.draw.rect(screen, CARD_HOVER, (item_rect.x, item_rect.y, drop_rect.width, item_h))
                
                draw_text(opt['label'], f_small, TEXT, item_rect.x + 15, item_rect.y + 12)
                pygame.draw.line(screen, BORDER_COLOR, (dropdown_panel.x, item_rect.bottom), (dropdown_panel.right, item_rect.bottom), 1)

            scrollbar_rect = pygame.Rect(drop_rect.right - 10, drop_rect.bottom + 4, 6, dropdown_view_h - 8)
            pygame.draw.rect(screen, BG_COLOR, scrollbar_rect, border_radius=3)
            scroll_bar_ratio = max_visible_items / len(options)
            slider_h = max(15, int(scrollbar_rect.height * scroll_bar_ratio))
            max_scroll_slots = len(options) - max_visible_items
            scroll_pos_ratio = dropdown_scroll_index / max_scroll_slots if max_scroll_slots > 0 else 0
            slider_y = scrollbar_rect.y + int((scrollbar_rect.height - slider_h) * scroll_pos_ratio)
            pygame.draw.rect(screen, ACCENT, (scrollbar_rect.x, slider_y, scrollbar_rect.width, slider_h), border_radius=3)

        draw_text(f"Dossier cible : {download_folder}", f_tiny, GRAY, 50, HEIGHT - 25, max_w=780)
        
        path_bg = CARD_HOVER if path_btn.collidepoint(m_pos) else CARD_COLOR
        path_border = ACCENT if path_btn.collidepoint(m_pos) else BORDER_COLOR
        pygame.draw.rect(screen, path_bg, path_btn, border_radius=4)
        pygame.draw.rect(screen, path_border, path_btn, 1, border_radius=4)
        draw_text("Modifier", f_tiny, TEXT, path_btn.centerx, path_btn.y + 5, center_x=True)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    # Exécute la vérification de mise à jour au tout début
    check_for_updates()
    
    # Si aucune mise à jour (ou après redémarrage), lance l'interface
    main()
