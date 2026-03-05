"""
Oyun Arşiv - Veritabanı İşlemleri
SQLite tabanlı oyun, stok ve satış yönetimi
"""

import sqlite3
import os
import shutil
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oyunlar.db")

PLATFORMLAR = [
    "PlayStation 1", "PlayStation 2", "PlayStation 3", "PlayStation 4", "PlayStation 5",
    "Xbox", "Xbox 360", "Xbox One", "Xbox Series X/S",
    "Nintendo Switch", "Nintendo Wii", "Nintendo Wii U", "Nintendo DS", "Nintendo 3DS",
    "PC", "Game Boy", "PSP", "PS Vita", "Diğer"
]

TURLER = [
    "Aksiyon", "Macera", "RPG", "FPS", "Yarış", "Spor", "Strateji",
    "Simülasyon", "Korku", "Platform", "Dövüş", "Bulmaca", "MMORPG",
    "Müzik/Ritim", "Diğer"
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def tablelari_olustur():
    """Veritabanı tablolarını oluşturur."""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS oyunlar (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ad          TEXT NOT NULL,
            platform    TEXT NOT NULL,
            tur         TEXT DEFAULT '',
            yayinci     TEXT DEFAULT '',
            cikis_yili  INTEGER,
            fiyat       REAL DEFAULT 0.0,
            stok        INTEGER DEFAULT 0,
            barkod      TEXT UNIQUE,
            notlar      TEXT DEFAULT '',
            eklendi     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS satislar (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            oyun_id      INTEGER NOT NULL,
            miktar       INTEGER NOT NULL DEFAULT 1,
            satis_fiyati REAL NOT NULL DEFAULT 0.0,
            alici        TEXT DEFAULT '',
            satis_tarihi TEXT DEFAULT CURRENT_TIMESTAMP,
            notlar       TEXT DEFAULT '',
            FOREIGN KEY (oyun_id) REFERENCES oyunlar(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────── OYUN İŞLEMLERİ ───────────────────────────

def oyun_ekle(ad, platform, tur="", yayinci="", cikis_yili=None, fiyat=0.0, stok=0, notlar=""):
    conn = get_conn()
    c = conn.cursor()
    # Aynı ad + platform varsa stoğu artır
    mevcut = c.execute(
        "SELECT id, stok FROM oyunlar WHERE ad = ? AND platform = ? COLLATE NOCASE",
        (ad, platform)
    ).fetchone()
    if mevcut:
        yeni_stok = mevcut["stok"] + max(stok, 1)
        c.execute("UPDATE oyunlar SET stok = ? WHERE id = ?", (yeni_stok, mevcut["id"]))
        conn.commit()
        conn.close()
        return mevcut["id"]
    c.execute("""
        INSERT INTO oyunlar (ad, platform, tur, yayinci, cikis_yili, fiyat, stok, notlar)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ad, platform, tur, yayinci, cikis_yili, fiyat, stok, notlar))
    oyun_id = c.lastrowid
    # Barkod: OYUN + 6 haneli id
    barkod = f"OYUN{oyun_id:06d}"
    c.execute("UPDATE oyunlar SET barkod = ? WHERE id = ?", (barkod, oyun_id))
    conn.commit()
    conn.close()
    return oyun_id


def oyun_guncelle(oyun_id, ad, platform, tur, yayinci, cikis_yili, fiyat, stok, notlar):
    conn = get_conn()
    conn.execute("""
        UPDATE oyunlar
        SET ad=?, platform=?, tur=?, yayinci=?, cikis_yili=?, fiyat=?, stok=?, notlar=?
        WHERE id=?
    """, (ad, platform, tur, yayinci, cikis_yili, fiyat, stok, notlar, oyun_id))
    conn.commit()
    conn.close()


def oyun_sil(oyun_id):
    conn = get_conn()
    conn.execute("DELETE FROM oyunlar WHERE id=?", (oyun_id,))
    conn.commit()
    conn.close()


def tum_oyunlar(arama=""):
    conn = get_conn()
    if arama:
        rows = conn.execute("""
            SELECT * FROM oyunlar
            WHERE ad LIKE ? OR platform LIKE ? OR yayinci LIKE ? OR barkod LIKE ?
            ORDER BY ad COLLATE NOCASE
        """, (f"%{arama}%", f"%{arama}%", f"%{arama}%", f"%{arama}%")).fetchall()
    else:
        rows = conn.execute("SELECT * FROM oyunlar ORDER BY ad COLLATE NOCASE").fetchall()
    conn.close()
    return rows


def oyun_getir(oyun_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM oyunlar WHERE id=?", (oyun_id,)).fetchone()
    conn.close()
    return row


def stok_guncelle(oyun_id, yeni_stok):
    conn = get_conn()
    conn.execute("UPDATE oyunlar SET stok=? WHERE id=?", (yeni_stok, oyun_id))
    conn.commit()
    conn.close()


# ─────────────────────────── SATIŞ İŞLEMLERİ ──────────────────────────

def satis_ekle(oyun_id, miktar, satis_fiyati, alici="", notlar=""):
    conn = get_conn()
    c = conn.cursor()
    # Mevcut stok kontrolü
    oyun = conn.execute("SELECT stok FROM oyunlar WHERE id=?", (oyun_id,)).fetchone()
    if oyun is None:
        conn.close()
        raise ValueError("Oyun bulunamadı.")
    if oyun["stok"] < miktar:
        conn.close()
        raise ValueError(f"Yetersiz stok! Mevcut: {oyun['stok']}, İstenen: {miktar}")

    satis_tarihi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO satislar (oyun_id, miktar, satis_fiyati, alici, satis_tarihi, notlar)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (oyun_id, miktar, satis_fiyati, alici, satis_tarihi, notlar))
    # Stok düş
    c.execute("UPDATE oyunlar SET stok = stok - ? WHERE id=?", (miktar, oyun_id))
    conn.commit()
    conn.close()


def satis_sil(satis_id):
    """Satışı sil ve stoğu geri yükle."""
    conn = get_conn()
    satis = conn.execute("SELECT * FROM satislar WHERE id=?", (satis_id,)).fetchone()
    if satis:
        conn.execute("UPDATE oyunlar SET stok = stok + ? WHERE id=?",
                     (satis["miktar"], satis["oyun_id"]))
        conn.execute("DELETE FROM satislar WHERE id=?", (satis_id,))
        conn.commit()
    conn.close()


def tum_satislar(arama=""):
    conn = get_conn()
    if arama:
        rows = conn.execute("""
            SELECT s.*, o.ad AS oyun_adi, o.platform, o.barkod
            FROM satislar s
            JOIN oyunlar o ON s.oyun_id = o.id
            WHERE o.ad LIKE ? OR s.alici LIKE ? OR o.barkod LIKE ?
            ORDER BY s.satis_tarihi DESC
        """, (f"%{arama}%", f"%{arama}%", f"%{arama}%")).fetchall()
    else:
        rows = conn.execute("""
            SELECT s.*, o.ad AS oyun_adi, o.platform, o.barkod
            FROM satislar s
            JOIN oyunlar o ON s.oyun_id = o.id
            ORDER BY s.satis_tarihi DESC
        """).fetchall()
    conn.close()
    return rows


# ───────────────────────────── İSTATİSTİKLER ──────────────────────────

def istatistikler():
    conn = get_conn()
    toplam_oyun    = conn.execute("SELECT COUNT(*) FROM oyunlar").fetchone()[0]
    toplam_stok    = conn.execute("SELECT COALESCE(SUM(stok), 0) FROM oyunlar").fetchone()[0]
    dusuk_stok     = conn.execute("SELECT COUNT(*) FROM oyunlar WHERE stok <= 2").fetchone()[0]
    toplam_satis   = conn.execute("SELECT COUNT(*) FROM satislar").fetchone()[0]
    toplam_ciro    = conn.execute(
        "SELECT COALESCE(SUM(miktar * satis_fiyati), 0) FROM satislar"
    ).fetchone()[0]
    conn.close()
    return {
        "toplam_oyun":  toplam_oyun,
        "toplam_stok":  toplam_stok,
        "dusuk_stok":   dusuk_stok,
        "toplam_satis": toplam_satis,
        "toplam_ciro":  toplam_ciro,
    }


# ─────────────────────────── YEDEKLEME ─────────────────────────────

def db_yedekle(hedef_yol: str = None) -> str:
    """oyunlar.db dosyasını yedekler. Hedef yol belirtilmezse tarihli yedek oluşturur."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError("Veritabanı dosyası bulunamadı.")
    if hedef_yol is None:
        tarih = datetime.now().strftime("%Y%m%d_%H%M%S")
        yedek_klasor = os.path.join(os.path.dirname(DB_PATH), "yedekler")
        os.makedirs(yedek_klasor, exist_ok=True)
        hedef_yol = os.path.join(yedek_klasor, f"oyunlar_yedek_{tarih}.db")
    shutil.copy2(DB_PATH, hedef_yol)
    return hedef_yol


def db_geri_yukle(kaynak_yol: str):
    """Yedek veritabanını geri yükler. Mevcut DB öncesinde otomatik yedeklenir."""
    if not os.path.exists(kaynak_yol):
        raise FileNotFoundError("Yedek dosyası bulunamadı.")
    # Önce mevcut DB'yi otomatik yedekle
    if os.path.exists(DB_PATH):
        db_yedekle()
    shutil.copy2(kaynak_yol, DB_PATH)
