"""
Oyun Arşiv – Otomatik Güncelleme Sistemi
GitHub Releases üzerinden sürüm kontrolü ve güncelleme.
"""

import threading
import urllib.request
import urllib.error
import json
import os
import sys
import zipfile
import shutil
import tempfile
import subprocess
from packaging.version import Version

# ─── Güncelleme Ayarları ───────────────────────────────
VERSION      = "1.1.4"          # Bu sürüm numarası
GITHUB_OWNER = "EmreBekcan"
GITHUB_REPO  = "oyun-arsiv"
API_URL      = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
TIMEOUT      = 8                # saniye
# ──────────────────────────────────────────────────────

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _surum_karsilastir(mevcut: str, yeni: str) -> bool:
    """Yeni sürüm mevcuttan büyükse True döner."""
    try:
        return Version(yeni) > Version(mevcut)
    except Exception:
        return False


def _api_kontrol() -> dict | None:
    """
    GitHub API'ye istek atar. Başarılıysa release bilgisini döner,
    hata varsa None döner. (Ağ yoksa sessizce geçer.)
    """
    try:
        req = urllib.request.Request(
            API_URL,
            headers={"User-Agent": "OyunArsiv-Updater/1.0",
                     "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def guncelleme_kontrol(callback):
    """
    Arka planda sürüm kontrolü yapar.
    Yeni sürüm varsa: callback(yeni_surum, indirme_url, release_url) çağırır.
    Yoksa veya hata olursa: callback çağırılmaz.

    callback(yeni_surum: str, zipball_url: str, html_url: str)
    """
    def _run():
        veri = _api_kontrol()
        if not veri:
            return
        tag = veri.get("tag_name", "").lstrip("v")
        if _surum_karsilastir(VERSION, tag):
            zipball  = veri.get("zipball_url", "")
            html_url = veri.get("html_url", "")
            try:
                callback(tag, zipball, html_url)
            except Exception:
                pass
    threading.Thread(target=_run, daemon=True).start()


def guncelleme_indir_ve_uygula(zipball_url: str,
                                ilerleme_cb=None,
                                bitti_cb=None,
                                hata_cb=None):
    """
    Güncellemeyi arka planda indirir ve uygular.

    ilerleme_cb(yuzde: int)   — indirme ilerlemesi  (0-100)
    bitti_cb()                — güncelleme başarıyla uygulandı
    hata_cb(mesaj: str)       — hata oluştu
    """
    def _run():
        tmp_zip = None
        tmp_dir = None
        try:
            # ── 1. Zip indir ──────────────────────────────
            tmp_zip = tempfile.mktemp(suffix=".zip")
            req = urllib.request.Request(
                zipball_url,
                headers={"User-Agent": "OyunArsiv-Updater/1.0"})

            with urllib.request.urlopen(req, timeout=60) as resp:
                toplam = int(resp.headers.get("Content-Length", 0))
                indirilen = 0
                chunk = 8192
                with open(tmp_zip, "wb") as f:
                    while True:
                        data = resp.read(chunk)
                        if not data:
                            break
                        f.write(data)
                        indirilen += len(data)
                        if ilerleme_cb and toplam > 0:
                            try:
                                ilerleme_cb(int(indirilen / toplam * 100))
                            except Exception:
                                pass

            # ── 2. Zip'i geçici klasöre aç ───────────────
            tmp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_zip, "r") as z:
                z.extractall(tmp_dir)

            # GitHub zip içinde "owner-repo-commithash/" gibi bir klasör açar
            icerik = os.listdir(tmp_dir)
            kaynak = os.path.join(tmp_dir, icerik[0]) if len(icerik) == 1 else tmp_dir

            # ── 3. .py, .txt dosyalarını kopyala ─────────
            kopyalanmaz = {"oyunlar.db", "yedekler", "__pycache__",
                           ".git", ".gitignore", "icon.png"}
            for dosya in os.listdir(kaynak):
                if dosya in kopyalanmaz:
                    continue
                kaynak_yol = os.path.join(kaynak, dosya)
                hedef_yol  = os.path.join(APP_DIR, dosya)
                if os.path.isfile(kaynak_yol):
                    shutil.copy2(kaynak_yol, hedef_yol)

            if bitti_cb:
                try:
                    bitti_cb()
                except Exception:
                    pass

        except Exception as e:
            if hata_cb:
                try:
                    hata_cb(str(e))
                except Exception:
                    pass
        finally:
            if tmp_zip and os.path.exists(tmp_zip):
                os.remove(tmp_zip)
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    threading.Thread(target=_run, daemon=True).start()


def uygulamayi_yeniden_baslat():
    """Uygulamayı kapatıp yeniden başlatır (Windows + Linux uyumlu)."""
    python = sys.executable
    args   = sys.argv[:]

    if sys.platform == "win32":
        # Windows: bat dosyasıyla geciktirilmiş yeniden başlatma
        # (Uygulama kapanmadan .py dosyaları kilitli olduğundan)
        bat_yol = os.path.join(APP_DIR, "_restart.bat")
        with open(bat_yol, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write("timeout /t 2 /nobreak >nul\n")
            arglar = " ".join(f'"{a}"' for a in args)
            f.write(f'start "" "{python}" {arglar}\n')
            f.write(f'del "%~f0"\n')  # bat kendini siler
        subprocess.Popen(["cmd", "/c", bat_yol],
                         creationflags=subprocess.CREATE_NO_WINDOW,
                         close_fds=True)
    else:
        # Linux / macOS
        subprocess.Popen([python] + args)

    sys.exit(0)
