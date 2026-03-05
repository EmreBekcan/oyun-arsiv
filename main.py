"""
Oyun Arşiv - Ana Uygulama
Video oyun koleksiyonu, stok ve satış yönetimi
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import os, subprocess, sys, webbrowser, urllib.parse, json
from PIL import Image, ImageTk
import io

import database as db
import barcode_gen as bk
import updater

# ─────────────────── AYAR DOSYASI ──────────────────────
_CONFIG_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def _ayar_yukle(anahtar: str, varsayilan):
    try:
        with open(_CONFIG_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f).get(anahtar, varsayilan)
    except Exception:
        return varsayilan

def _ayar_kaydet(**kwargs):
    ayarlar = {}
    try:
        with open(_CONFIG_DOSYASI, "r", encoding="utf-8") as f:
            ayarlar = json.load(f)
    except Exception:
        pass
    ayarlar.update(kwargs)
    try:
        with open(_CONFIG_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(ayarlar, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ─────────────────── TEMA & RENKLER ────────────────────
ctk.set_default_color_theme("blue")

TEMALAR = {
    "dark": {
        "bg":        "#1a1a2e",
        "sidebar":   "#16213e",
        "card":      "#0f3460",
        "accent":    "#4a9fff",
        "accent2":   "#e94560",
        "text":      "#eaeaea",
        "text2":     "#a0a0b0",
        "success":   "#4caf50",
        "warning":   "#ff9800",
        "error":     "#f44336",
        "tree_bg":   "#1e1e2e",
        "tree_fg":   "#cdd6f4",
        "tree_sel":  "#45475a",
        "tree_head": "#11111b",
        "row_odd":   "#1e1e2e",
        "row_even":  "#242436",
    },
    "light": {
        "bg":        "#f0f4f8",
        "sidebar":   "#dde5f0",
        "card":      "#c3d2e8",
        "accent":    "#1565c0",
        "accent2":   "#c62828",
        "text":      "#1a202c",
        "text2":     "#4a5568",
        "success":   "#276749",
        "warning":   "#c05621",
        "error":     "#c53030",
        "tree_bg":   "#ffffff",
        "tree_fg":   "#1a202c",
        "tree_sel":  "#bee3f8",
        "tree_head": "#c3d2e8",
        "row_odd":   "#ffffff",
        "row_even":  "#f0f4f8",
    },
}

_aktif_tema = _ayar_yukle("tema", "dark")
ctk.set_appearance_mode(_aktif_tema)

C = dict(TEMALAR[_aktif_tema])


def ttk_style_ayarla():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.Treeview",
        background=C["tree_bg"], foreground=C["tree_fg"],
        rowheight=30, fieldbackground=C["tree_bg"],
        bordercolor=C["card"], borderwidth=0,
        font=("Segoe UI", 10))
    style.configure("Dark.Treeview.Heading",
        background=C["tree_head"], foreground=C["text"],
        relief="flat", font=("Segoe UI", 10, "bold"), padding=6)
    style.map("Dark.Treeview",
        background=[("selected", C["tree_sel"])],
        foreground=[("selected", "#ffffff")])
    style.map("Dark.Treeview.Heading",
        background=[("active", C["card"])])
    style.configure("Vertical.TScrollbar",
        background=C["card"], troughcolor=C["tree_bg"],
        bordercolor=C["bg"], arrowcolor=C["text2"])
    style.configure("Horizontal.TScrollbar",
        background=C["card"], troughcolor=C["tree_bg"],
        bordercolor=C["bg"], arrowcolor=C["text2"])


# ════════════════════════════════════════════════════════
#  OYUN FORM DİYALOĞU  (Ekle / Düzenle)
# ════════════════════════════════════════════════════════
class OyunFormDialog(ctk.CTkToplevel):
    def __init__(self, master, oyun_id=None, on_save=None):
        super().__init__(master)
        self.oyun_id = oyun_id
        self.on_save = on_save
        self.title("Oyun Düzenle" if oyun_id else "Yeni Oyun Ekle")
        self.geometry("520x640")
        self.resizable(False, False)
        self.configure(fg_color=C["bg"])
        self.lift()
        self.focus_force()
        self.after(100, self.grab_set)
        self._olustur()
        if oyun_id:
            self._doldur()

    def _olustur(self):
        ctk.CTkLabel(self, text=("Oyun Düzenle" if self.oyun_id else "Yeni Oyun Ekle"),
                     font=("Segoe UI", 18, "bold"), text_color=C["accent"]).pack(pady=(20, 5))

        form = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=12)
        form.pack(padx=20, pady=10, fill="both", expand=True)

        def satir(etiket, widget_fn, **kw):
            f = ctk.CTkFrame(form, fg_color="transparent")
            f.pack(fill="x", padx=16, pady=6)
            ctk.CTkLabel(f, text=etiket, width=110, anchor="w",
                         text_color=C["text2"], font=("Segoe UI", 11)).pack(side="left")
            w = widget_fn(f, **kw)
            w.pack(side="left", fill="x", expand=True)
            return w

        self.e_ad      = satir("Oyun Adı *", ctk.CTkEntry, placeholder_text="Örn: God of War")
        self.e_platform = satir("Platform *", ctk.CTkComboBox,
                                values=db.PLATFORMLAR, state="readonly")
        self.e_platform.set(db.PLATFORMLAR[3])  # PS4 default
        self.e_tur     = satir("Tür", ctk.CTkComboBox,
                                values=[""] + db.TURLER, state="readonly")
        self.e_yayinci = satir("Yayıncı", ctk.CTkEntry,
                                placeholder_text="Örn: Sony Santa Monica")
        self.e_yil     = satir("Çıkış Yılı", ctk.CTkEntry, placeholder_text="Örn: 2022")
        self.e_fiyat   = satir("Fiyat (₺)", ctk.CTkEntry, placeholder_text="0.00")
        self.e_stok    = satir("Stok Miktarı", ctk.CTkEntry, placeholder_text="0")

        nf = ctk.CTkFrame(form, fg_color="transparent")
        nf.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(nf, text="Notlar", width=110, anchor="w",
                     text_color=C["text2"], font=("Segoe UI", 11)).pack(side="left", anchor="n")
        self.e_notlar = ctk.CTkTextbox(nf, height=70, corner_radius=8)
        self.e_notlar.pack(side="left", fill="x", expand=True)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(5, 20))
        ctk.CTkButton(bf, text="Vazgeç", fg_color=C["card"], hover_color="#1a3a6e",
                      text_color=C["text"], command=self.destroy, width=100).pack(side="right", padx=5)
        ctk.CTkButton(bf, text="Kaydet", fg_color=C["accent"], hover_color="#2a7fdf",
                      text_color="white", command=self._kaydet, width=120).pack(side="right", padx=5)

    def _doldur(self):
        o = db.oyun_getir(self.oyun_id)
        if not o:
            return
        self.e_ad.insert(0, o["ad"])
        self.e_platform.set(o["platform"])
        if o["tur"]:
            self.e_tur.set(o["tur"])
        self.e_yayinci.insert(0, o["yayinci"] or "")
        self.e_yil.insert(0, str(o["cikis_yili"]) if o["cikis_yili"] else "")
        self.e_fiyat.insert(0, str(o["fiyat"]))
        self.e_stok.insert(0, str(o["stok"]))
        if o["notlar"]:
            self.e_notlar.insert("1.0", o["notlar"])

    def _kaydet(self):
        ad = self.e_ad.get().strip()
        if not ad:
            messagebox.showerror("Hata", "Oyun adı zorunludur!", parent=self)
            return
        platform = self.e_platform.get()
        tur      = self.e_tur.get()
        yayinci  = self.e_yayinci.get().strip()
        yil_str  = self.e_yil.get().strip()
        yil      = int(yil_str) if yil_str.isdigit() else None
        try:
            fiyat = float(self.e_fiyat.get().strip() or 0)
            stok  = int(self.e_stok.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Hata", "Fiyat ve stok sayısal olmalıdır!", parent=self)
            return
        notlar = self.e_notlar.get("1.0", "end").strip()

        if self.oyun_id:
            db.oyun_guncelle(self.oyun_id, ad, platform, tur, yayinci, yil, fiyat, stok, notlar)
        else:
            # Aynı ad+platform var mı kontrol et (kullanıcıya bilgi ver)
            from database import get_conn
            conn = get_conn()
            mevcut = conn.execute(
                "SELECT id, stok FROM oyunlar WHERE ad = ? AND platform = ? COLLATE NOCASE",
                (ad, platform)).fetchone()
            conn.close()
            if mevcut:
                messagebox.showinfo("Bilgi",
                    f"'{ad}' ({platform}) zaten kayıtlı.\n"
                    f"Stok miktarı +{max(stok, 1)} artırıldı.",
                    parent=self)
            db.oyun_ekle(ad, platform, tur, yayinci, yil, fiyat, stok, notlar)

        if self.on_save:
            self.on_save()
        self.destroy()


# ════════════════════════════════════════════════════════
#  BARKOD DİYALOĞU
# ════════════════════════════════════════════════════════
class BarkodDialog(ctk.CTkToplevel):
    def __init__(self, master, oyunlar: list):
        """oyunlar: [{"id":, "ad":, "barkod":, "platform":}, ...]"""
        super().__init__(master)
        self.oyunlar = oyunlar
        self.indeks  = 0
        self.title("Barkod Görüntüle")
        self.geometry("520x440")
        self.resizable(False, False)
        self.configure(fg_color=C["bg"])
        self.lift()
        self.focus_force()
        self.after(100, self.grab_set)
        self._olustur()
        self._barkod_goster()

    def _olustur(self):
        ctk.CTkLabel(self, text="Barkod Görüntüleyici",
                     font=("Segoe UI", 16, "bold"), text_color=C["accent"]).pack(pady=(16, 4))

        self.lbl_oyun = ctk.CTkLabel(self, text="", font=("Segoe UI", 12),
                                     text_color=C["text2"])
        self.lbl_oyun.pack()

        self.lbl_barkod_img = ctk.CTkLabel(self, text="Yükleniyor...")
        self.lbl_barkod_img.pack(pady=14)

        nf = ctk.CTkFrame(self, fg_color="transparent")
        nf.pack(pady=4)
        if len(self.oyunlar) > 1:
            ctk.CTkButton(nf, text="◀ Önceki", width=90, fg_color=C["card"],
                          text_color=C["text"], command=self._onceki).pack(side="left", padx=4)
        self.lbl_sayac = ctk.CTkLabel(nf, text="", text_color=C["text2"])
        self.lbl_sayac.pack(side="left", padx=10)
        if len(self.oyunlar) > 1:
            ctk.CTkButton(nf, text="Sonraki ▶", width=90, fg_color=C["card"],
                          text_color=C["text"], command=self._sonraki).pack(side="left", padx=4)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(pady=(8, 16))
        ctk.CTkButton(bf, text="PNG Kaydet", width=120,
                      fg_color=C["accent2"], hover_color="#c03050",
                      text_color="white", command=self._png_kaydet).pack(side="left", padx=6)
        ctk.CTkButton(bf, text="PDF Etiket (Tümü)", width=150,
                      fg_color="#533483", hover_color="#6a45a0",
                      text_color="white", command=self._pdf_kaydet).pack(side="left", padx=6)
        ctk.CTkButton(bf, text="Kapat", width=80, fg_color=C["card"],
                      text_color=C["text"], command=self.destroy).pack(side="left", padx=6)

    def _barkod_goster(self):
        oyun = self.oyunlar[self.indeks]
        self.lbl_oyun.configure(
            text=f"{oyun['ad']}  |  {oyun.get('platform', '')}  |  {oyun['barkod']}")
        self.lbl_sayac.configure(
            text=f"{self.indeks + 1} / {len(self.oyunlar)}")
        try:
            img_bytes = bk.barkod_bytes_getir(oyun["barkod"], oyun["ad"])
            photo = ImageTk.PhotoImage(data=img_bytes)
            self.lbl_barkod_img.configure(image=photo, text="")
            self.lbl_barkod_img.image = photo
        except Exception as e:
            self.lbl_barkod_img.configure(text=f"Barkod oluşturulamadı:\n{e}")

    def _onceki(self):
        if self.indeks > 0:
            self.indeks -= 1
            self._barkod_goster()

    def _sonraki(self):
        if self.indeks < len(self.oyunlar) - 1:
            self.indeks += 1
            self._barkod_goster()

    def _png_kaydet(self):
        oyun = self.oyunlar[self.indeks]
        yol = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Dosyası", "*.png")],
            initialfile=f"{oyun['barkod']}.png",
            title="PNG Kaydet")
        if not yol:
            return
        try:
            bk.barkod_olustur_png(oyun["barkod"], oyun["ad"])
            kaynak = os.path.join(bk.BARKOD_KLASOR, f"{oyun['barkod']}.png")
            import shutil
            shutil.copy2(kaynak, yol)
            messagebox.showinfo("Başarılı", f"PNG kaydedildi:\n{yol}", parent=self)
        except Exception as e:
            messagebox.showerror("Hata", str(e), parent=self)

    def _pdf_kaydet(self):
        yol = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Dosyası", "*.pdf")],
            initialfile="barkod_etiketler.pdf",
            title="PDF Kaydet")
        if not yol:
            return
        try:
            pdf_yolu = bk.pdf_etiket_olustur(self.oyunlar, yol)
            messagebox.showinfo("Başarılı",
                f"PDF oluşturuldu:\n{pdf_yolu}\n"
                f"({len(self.oyunlar)} etiket)", parent=self)
            if sys.platform == "linux":
                subprocess.Popen(["xdg-open", pdf_yolu])
        except Exception as e:
            messagebox.showerror("Hata", str(e), parent=self)


# ════════════════════════════════════════════════════════
#  SATIŞ FORM DİYALOĞU
# ════════════════════════════════════════════════════════
class SatisFormDialog(ctk.CTkToplevel):
    def __init__(self, master, oyun_id=None, on_save=None):
        super().__init__(master)
        self.oyun_id = oyun_id
        self.on_save = on_save
        self.title("Yeni Satış Kaydı")
        self.geometry("460x420")
        self.resizable(False, False)
        self.configure(fg_color=C["bg"])
        self.lift()
        self.focus_force()
        self.after(100, self.grab_set)
        self._olustur()
        if oyun_id:
            o = db.oyun_getir(oyun_id)
            if o:
                self.combo_oyun.set(f"{o['ad']} [{o['platform']}]")
                self.e_fiyat.insert(0, str(o["fiyat"]))
                self._guncel_stok = o["stok"]
                self.lbl_stok.configure(text=f"Mevcut Stok: {o['stok']}")

    def _olustur(self):
        ctk.CTkLabel(self, text="Yeni Satış Kaydı",
                     font=("Segoe UI", 18, "bold"), text_color=C["accent"]).pack(pady=(20, 5))

        form = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=12)
        form.pack(padx=20, pady=10, fill="both", expand=True)

        def satir(etiket, widget):
            f = ctk.CTkFrame(form, fg_color="transparent")
            f.pack(fill="x", padx=16, pady=7)
            ctk.CTkLabel(f, text=etiket, width=120, anchor="w",
                         text_color=C["text2"], font=("Segoe UI", 11)).pack(side="left")
            widget = widget(f)
            widget.pack(side="left", fill="x", expand=True)
            return widget

        # Oyun seçimi
        tum = db.tum_oyunlar()
        self._oyun_map = {f"{o['ad']} [{o['platform']}]": o["id"] for o in tum}
        oyun_listesi = list(self._oyun_map.keys())

        f_oyun = ctk.CTkFrame(form, fg_color="transparent")
        f_oyun.pack(fill="x", padx=16, pady=7)
        ctk.CTkLabel(f_oyun, text="Oyun *", width=120, anchor="w",
                     text_color=C["text2"], font=("Segoe UI", 11)).pack(side="left")
        self.combo_oyun = ctk.CTkComboBox(f_oyun, values=oyun_listesi,
                                          command=self._oyun_secildi)
        self.combo_oyun.pack(side="left", fill="x", expand=True)

        self.lbl_stok = ctk.CTkLabel(form, text="", text_color=C["warning"],
                                     font=("Segoe UI", 10))
        self.lbl_stok.pack(padx=16, anchor="w")

        self.e_miktar = satir("Miktar *", lambda p: ctk.CTkEntry(p, placeholder_text="1"))
        self.e_fiyat  = satir("Satış Fiyatı (₺) *", lambda p: ctk.CTkEntry(p, placeholder_text="0.00"))
        self.e_alici  = satir("Alıcı Adı", lambda p: ctk.CTkEntry(p, placeholder_text="Opsiyonel"))

        nf = ctk.CTkFrame(form, fg_color="transparent")
        nf.pack(fill="x", padx=16, pady=7)
        ctk.CTkLabel(nf, text="Notlar", width=120, anchor="w",
                     text_color=C["text2"], font=("Segoe UI", 11)).pack(side="left", anchor="n")
        self.e_notlar = ctk.CTkTextbox(nf, height=55, corner_radius=8)
        self.e_notlar.pack(side="left", fill="x", expand=True)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(5, 20))
        ctk.CTkButton(bf, text="Vazgeç", fg_color=C["card"], hover_color="#1a3a6e",
                      text_color=C["text"], command=self.destroy, width=100).pack(side="right", padx=5)
        ctk.CTkButton(bf, text="Satışı Kaydet", fg_color=C["success"],
                      hover_color="#388e3c", text_color="white", command=self._kaydet, width=140).pack(side="right", padx=5)

    def _oyun_secildi(self, secim):
        oyun_id = self._oyun_map.get(secim)
        if oyun_id:
            o = db.oyun_getir(oyun_id)
            if o:
                self.lbl_stok.configure(text=f"Mevcut Stok: {o['stok']}")

    def _kaydet(self):
        secim = self.combo_oyun.get()
        oyun_id = self._oyun_map.get(secim)
        if not oyun_id:
            messagebox.showerror("Hata", "Oyun seçiniz!", parent=self)
            return
        try:
            miktar = int(self.e_miktar.get().strip() or 1)
            fiyat  = float(self.e_fiyat.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Hata", "Miktar ve fiyat sayısal olmalıdır!", parent=self)
            return
        alici  = self.e_alici.get().strip()
        notlar = self.e_notlar.get("1.0", "end").strip()

        try:
            db.satis_ekle(oyun_id, miktar, fiyat, alici, notlar)
        except ValueError as e:
            messagebox.showerror("Hata", str(e), parent=self)
            return

        if self.on_save:
            self.on_save()
        self.destroy()


# ════════════════════════════════════════════════════════
#  OYUNLAR SAYFASI
# ════════════════════════════════════════════════════════
class OyunlarPage(ctk.CTkFrame):
    SUTUNLAR = [
        ("id",      "#",            40,  tk.CENTER),
        ("ad",      "Oyun Adı",    220,  tk.W),
        ("platform","Platform",    110,  tk.CENTER),
        ("tur",     "Tür",         100,  tk.CENTER),
        ("yayinci", "Yayıncı",     120,  tk.W),
        ("yil",     "Yıl",          50,  tk.CENTER),
        ("fiyat",   "Fiyat (₺)",    80,  tk.E),
        ("stok",    "Stok",         60,  tk.CENTER),
        ("barkod",  "Barkod",      110,  tk.CENTER),
    ]

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._olustur()
        self.yenile()

    def _olustur(self):
        # Üst araç çubuğu
        ust = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        ust.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(ust, text="Oyun Koleksiyonu",
                     font=("Segoe UI", 16, "bold"), text_color=C["accent"]).pack(
                     side="left", padx=16, pady=10)

        self.e_ara = ctk.CTkEntry(ust, placeholder_text="🔍 Ara...", width=220)
        self.e_ara.pack(side="left", padx=8)
        self.e_ara.bind("<Return>", lambda e: self.yenile())
        ctk.CTkButton(ust, text="Ara", width=60, fg_color=C["card"],
                      text_color=C["text"], command=self.yenile).pack(side="left", padx=4)

        ctk.CTkButton(ust, text="+ Oyun Ekle", fg_color=C["accent"],
                      hover_color="#2a7fdf", text_color="white", command=self._ekle).pack(side="right", padx=8)
        ctk.CTkButton(ust, text="PDF Etiket", fg_color="#533483",
                      hover_color="#6a45a0", text_color="white", command=self._pdf_tumu).pack(side="right", padx=4)
        ctk.CTkButton(ust, text="🏷 Barkod", fg_color=C["card"],
                      text_color=C["text"], command=self._barkod_goster).pack(side="right", padx=4)
        ctk.CTkButton(ust, text="✏ Düzenle", fg_color=C["card"],
                      text_color=C["text"], command=self._duzenle).pack(side="right", padx=4)
        ctk.CTkButton(ust, text="🗑 Sil", fg_color=C["error"],
                      hover_color="#c62828", text_color="white", command=self._sil).pack(side="right", padx=4)

        # Treeview
        tree_frame = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = [s[0] for s in self.SUTUNLAR]
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="Dark.Treeview", selectmode="extended")
        for key, baslik, gen, anchor in self.SUTUNLAR:
            self.tree.heading(key, text=baslik,
                              command=lambda k=key: self._sirala(k))
            self.tree.column(key, width=gen, minwidth=gen, anchor=anchor)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda e: self._duzenle())
        self.tree.tag_configure("sıfır", foreground=C["error"])
        self.tree.tag_configure("az",    foreground=C["warning"])
        self.tree.tag_configure("normal",foreground=C["tree_fg"])

        # Alt durum çubuğu
        alt = ctk.CTkFrame(self, fg_color="transparent")
        alt.pack(fill="x", padx=14, pady=(0, 6))
        self.lbl_durum = ctk.CTkLabel(alt, text="", text_color=C["text2"],
                                       font=("Segoe UI", 10))
        self.lbl_durum.pack(side="left")

        self._siralama = {"sutun": None, "artan": True}

    def yenile(self):
        arama = self.e_ara.get().strip() if hasattr(self, "e_ara") else ""
        rows = db.tum_oyunlar(arama)
        self.tree.delete(*self.tree.get_children())
        for o in rows:
            yil  = str(o["cikis_yili"]) if o["cikis_yili"] else "-"
            fiyat_str = f"{o['fiyat']:.2f} ₺"
            tag = "sıfır" if o["stok"] == 0 else ("az" if o["stok"] <= 2 else "normal")
            self.tree.insert("", "end", iid=str(o["id"]),
                values=(o["id"], o["ad"], o["platform"], o["tur"] or "-",
                        o["yayinci"] or "-", yil, fiyat_str, o["stok"], o["barkod"]),
                tags=(tag,))
        self.lbl_durum.configure(text=f"{len(rows)} oyun listeleniyor")

    def _secili_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen bir oyun seçin.", parent=self)
            return None
        return int(sel[0])

    def _secili_idler(self):
        return [int(s) for s in self.tree.selection()]

    def _ekle(self):
        OyunFormDialog(self, on_save=self.yenile)

    def _duzenle(self):
        oid = self._secili_id()
        if oid:
            OyunFormDialog(self, oyun_id=oid, on_save=self.yenile)

    def _sil(self):
        idler = self._secili_idler()
        if not idler:
            messagebox.showwarning("Uyarı", "Lütfen silmek için oyun seçin.", parent=self)
            return
        if not messagebox.askyesno("Onayla",
                f"{len(idler)} oyun silinecek. Emin misiniz?\n(İlgili satışlar da silinir!)",
                parent=self):
            return
        for oid in idler:
            db.oyun_sil(oid)
        self.yenile()

    def _barkod_goster(self):
        idler = self._secili_idler()
        if not idler:
            messagebox.showwarning("Uyarı", "Barkod için oyun seçin.", parent=self)
            return
        oyunlar = []
        for oid in idler:
            o = db.oyun_getir(oid)
            if o:
                oyunlar.append({"id": o["id"], "ad": o["ad"],
                                 "barkod": o["barkod"], "platform": o["platform"]})
        BarkodDialog(self, oyunlar)

    def _pdf_tumu(self):
        rows = db.tum_oyunlar()
        oyunlar = [{"id": o["id"], "ad": o["ad"],
                     "barkod": o["barkod"], "platform": o["platform"]} for o in rows]
        if not oyunlar:
            messagebox.showinfo("Bilgi", "Veritabanında oyun yok.", parent=self)
            return
        yol = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="tum_barkodlar.pdf")
        if not yol:
            return
        try:
            bk.pdf_etiket_olustur(oyunlar, yol)
            messagebox.showinfo("Başarılı", f"PDF oluşturuldu:\n{yol}", parent=self)
            subprocess.Popen(["xdg-open", yol])
        except Exception as e:
            messagebox.showerror("Hata", str(e), parent=self)

    def _sirala(self, sutun):
        s = self._siralama
        artan = not s["artan"] if s["sutun"] == sutun else True
        s["sutun"] = sutun; s["artan"] = artan
        items = [(self.tree.set(iid, sutun), iid) for iid in self.tree.get_children("")]
        try:
            items.sort(key=lambda x: float(x[0].replace(" ₺","").replace(",",".")),
                       reverse=not artan)
        except (ValueError, AttributeError):
            items.sort(key=lambda x: x[0].lower(), reverse=not artan)
        for idx, (_, iid) in enumerate(items):
            self.tree.move(iid, "", idx)


# ════════════════════════════════════════════════════════
#  STOK SAYFASI
# ════════════════════════════════════════════════════════
class StokPage(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._olustur()
        self.yenile()

    def _olustur(self):
        ust = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        ust.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(ust, text="Stok Yönetimi",
                     font=("Segoe UI", 16, "bold"), text_color=C["accent"]).pack(
                     side="left", padx=16, pady=10)

        self.e_ara = ctk.CTkEntry(ust, placeholder_text="🔍 Ara...", width=200)
        self.e_ara.pack(side="left", padx=8)
        self.e_ara.bind("<Return>", lambda e: self.yenile())

        self.platform_var = ctk.StringVar(value="Tümü")
        self.combo_platform = ctk.CTkComboBox(
            ust, values=["Tümü"] + db.PLATFORMLAR,
            variable=self.platform_var, width=160,
            command=lambda _: self.yenile())
        self.combo_platform.pack(side="left", padx=8)

        ctk.CTkButton(ust, text="Stok Güncelle", fg_color=C["accent"],
                      text_color="white", command=self._guncelle).pack(side="right", padx=8)
        ctk.CTkButton(ust, text="+ Ekle", fg_color=C["success"], hover_color="#388e3c",
                      text_color="white", command=lambda: self._delta(+1)).pack(side="right", padx=4)
        ctk.CTkButton(ust, text="– Çıkar", fg_color=C["error"], hover_color="#c62828",
                      text_color="white", command=lambda: self._delta(-1)).pack(side="right", padx=4)

        # Legand
        leg = ctk.CTkFrame(self, fg_color="transparent")
        leg.pack(fill="x", padx=14, pady=(0, 4))
        for renk, metin in [(C["error"], "● Stok Yok (0)"),
                             (C["warning"], "● Az Stok (1-2)"),
                             (C["success"], "● Yeterli (3+)")]:
            ctk.CTkLabel(leg, text=metin, text_color=renk,
                         font=("Segoe UI", 10)).pack(side="left", padx=10)

        # Treeview
        tf = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        tf.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ["id", "ad", "platform", "stok", "durum", "fiyat", "barkod"]
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                  style="Dark.Treeview")
        specs = [
            ("id",       "#",        40,  tk.CENTER),
            ("ad",       "Oyun Adı", 230, tk.W),
            ("platform", "Platform", 120, tk.CENTER),
            ("stok",     "Stok",      70, tk.CENTER),
            ("durum",    "Durum",     80, tk.CENTER),
            ("fiyat",    "Fiyat (₺)",90, tk.E),
            ("barkod",   "Barkod",   110, tk.CENTER),
        ]
        for key, baslik, gen, anchor in specs:
            self.tree.heading(key, text=baslik)
            self.tree.column(key, width=gen, minwidth=gen, anchor=anchor)

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        self.tree.tag_configure("sıfır",  foreground=C["error"])
        self.tree.tag_configure("az",     foreground=C["warning"])
        self.tree.tag_configure("normal", foreground=C["success"])

        alt = ctk.CTkFrame(self, fg_color="transparent")
        alt.pack(fill="x", padx=14)
        self.lbl_durum = ctk.CTkLabel(alt, text="", text_color=C["text2"],
                                       font=("Segoe UI", 10))
        self.lbl_durum.pack(side="left")

    def yenile(self):
        arama    = self.e_ara.get().strip() if hasattr(self, "e_ara") else ""
        platform = self.platform_var.get() if hasattr(self, "platform_var") else "Tümü"
        rows = db.tum_oyunlar(arama)
        if platform != "Tümü":
            rows = [r for r in rows if r["platform"] == platform]
        # Stok'a göre sırala: 0 önce, sonra az
        rows = sorted(rows, key=lambda x: x["stok"])
        self.tree.delete(*self.tree.get_children())
        toplam_stok = 0
        for o in rows:
            toplam_stok += o["stok"]
            if o["stok"] == 0:   tag = "sıfır"; durum = "❌ Yok"
            elif o["stok"] <= 2: tag = "az";    durum = "⚠️ Az"
            else:                 tag = "normal"; durum = "✅ Var"
            self.tree.insert("", "end", iid=str(o["id"]),
                values=(o["id"], o["ad"], o["platform"],
                        o["stok"], durum, f"{o['fiyat']:.2f} ₺", o["barkod"]),
                tags=(tag,))
        self.lbl_durum.configure(
            text=f"{len(rows)} oyun | Toplam Stok: {toplam_stok}")

    def _secili_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Uyarı", "Oyun seçin.", parent=self)
            return None
        return int(sel[0])

    def _guncelle(self):
        oid = self._secili_id()
        if not oid:
            return
        o = db.oyun_getir(oid)
        dlg = ctk.CTkInputDialog(text=f"'{o['ad']}' yeni stok miktarı:",
                                  title="Stok Güncelle")
        val = dlg.get_input()
        if val and val.isdigit():
            db.stok_guncelle(oid, int(val))
            self.yenile()

    def _delta(self, miktar):
        oid = self._secili_id()
        if not oid:
            return
        o = db.oyun_getir(oid)
        yeni = max(0, o["stok"] + miktar)
        db.stok_guncelle(oid, yeni)
        self.yenile()


# ════════════════════════════════════════════════════════
#  SATIŞLAR SAYFASI
# ════════════════════════════════════════════════════════
class SatislarPage(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._olustur()
        self.yenile()

    def _olustur(self):
        ust = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        ust.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(ust, text="Satış Geçmişi",
                     font=("Segoe UI", 16, "bold"), text_color=C["accent"]).pack(
                     side="left", padx=16, pady=10)

        self.e_ara = ctk.CTkEntry(ust, placeholder_text="🔍 Ara...", width=200)
        self.e_ara.pack(side="left", padx=8)
        self.e_ara.bind("<Return>", lambda e: self.yenile())

        ctk.CTkButton(ust, text="+ Yeni Satış", fg_color=C["success"],
                      hover_color="#388e3c", text_color="white", command=self._yeni).pack(side="right", padx=8)
        ctk.CTkButton(ust, text="🗑 Sil", fg_color=C["error"], hover_color="#c62828",
                      text_color="white", command=self._sil).pack(side="right", padx=4)

        # Treeview
        tf = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        tf.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ["id","tarih","oyun","platform","miktar","satis_fiyati","toplam","alici"]
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                  style="Dark.Treeview")
        specs = [
            ("id",          "#",             40,  tk.CENTER),
            ("tarih",       "Tarih",        140,  tk.CENTER),
            ("oyun",        "Oyun",         200,  tk.W),
            ("platform",    "Platform",     110,  tk.CENTER),
            ("miktar",      "Miktar",        60,  tk.CENTER),
            ("satis_fiyati","Birim Fiyat",   90,  tk.E),
            ("toplam",      "Toplam",        90,  tk.E),
            ("alici",       "Alıcı",        130,  tk.W),
        ]
        for key, baslik, gen, anchor in specs:
            self.tree.heading(key, text=baslik)
            self.tree.column(key, width=gen, minwidth=gen, anchor=anchor)

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        alt = ctk.CTkFrame(self, fg_color="transparent")
        alt.pack(fill="x", padx=14, pady=(0, 6))
        self.lbl_durum = ctk.CTkLabel(alt, text="", text_color=C["text2"],
                                       font=("Segoe UI", 10))
        self.lbl_durum.pack(side="left")
        self.lbl_ciro = ctk.CTkLabel(alt, text="", text_color=C["success"],
                                      font=("Segoe UI", 11, "bold"))
        self.lbl_ciro.pack(side="right")

    def yenile(self):
        arama = self.e_ara.get().strip() if hasattr(self, "e_ara") else ""
        rows = db.tum_satislar(arama)
        self.tree.delete(*self.tree.get_children())
        toplam_ciro = 0.0
        for s in rows:
            toplam = s["miktar"] * s["satis_fiyati"]
            toplam_ciro += toplam
            self.tree.insert("", "end", iid=str(s["id"]),
                values=(s["id"],
                        s["satis_tarihi"][:16],
                        s["oyun_adi"],
                        s["platform"],
                        s["miktar"],
                        f"{s['satis_fiyati']:.2f} ₺",
                        f"{toplam:.2f} ₺",
                        s["alici"] or "-"))
        self.lbl_durum.configure(text=f"{len(rows)} satış kaydı")
        self.lbl_ciro.configure(text=f"Toplam Ciro: {toplam_ciro:,.2f} ₺")

    def _yeni(self):
        SatisFormDialog(self, on_save=self.yenile)

    def _sil(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Uyarı", "Silmek için satış seçin.", parent=self)
            return
        if not messagebox.askyesno("Onayla",
            "Seçili satış silinecek ve stok geri yüklenecek.\nEmin misiniz?", parent=self):
            return
        for iid in sel:
            db.satis_sil(int(iid))
        self.yenile()


# ════════════════════════════════════════════════════════
#  RAPOR SAYFASI
# ════════════════════════════════════════════════════════
class RaporPage(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._olustur()
        self.yenile()

    def _kart(self, parent, baslik, deger_text, renk, sira):
        kart = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=14,
                             border_width=1, border_color=renk)
        kart.grid(row=0, column=sira, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(kart, text=baslik, text_color=C["text2"],
                     font=("Segoe UI", 12)).pack(pady=(18, 4))
        self._deger_lbls[baslik] = ctk.CTkLabel(
            kart, text=deger_text, text_color=renk,
            font=("Segoe UI", 26, "bold"))
        self._deger_lbls[baslik].pack(pady=(0, 18))
        return kart

    def _olustur(self):
        self._deger_lbls = {}

        ctk.CTkLabel(self, text="Genel Rapor",
                     font=("Segoe UI", 20, "bold"), text_color=C["accent"]).pack(
                     pady=(20, 10), padx=20, anchor="w")

        kart_frame = ctk.CTkFrame(self, fg_color="transparent")
        kart_frame.pack(fill="x", padx=10)
        for i in range(5):
            kart_frame.grid_columnconfigure(i, weight=1)

        veriler = [
            ("Toplam Oyun",  "0",    C["accent"]),
            ("Toplam Stok",  "0",    "#a8dadc"),
            ("Düşük Stok",   "0",    C["warning"]),
            ("Toplam Satış", "0",    C["success"]),
            ("Toplam Ciro",  "0 ₺",  "#c77dff"),
        ]
        for i, (b, d, r) in enumerate(veriler):
            self._kart(kart_frame, b, d, r, i)

        # Düşük stok uyarısı listesi
        ctk.CTkLabel(self, text="⚠️  Düşük/Sıfır Stoklu Oyunlar",
                     font=("Segoe UI", 13, "bold"), text_color=C["warning"]).pack(
                     padx=16, pady=(20, 6), anchor="w")

        tf = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        tf.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ["ad", "platform", "stok"]
        self.tree_dusuk = ttk.Treeview(tf, columns=cols, show="headings",
                                        style="Dark.Treeview", height=8)
        for key, baslik, gen in [("ad","Oyun",260), ("platform","Platform",130), ("stok","Stok",80)]:
            self.tree_dusuk.heading(key, text=baslik)
            self.tree_dusuk.column(key, width=gen, minwidth=gen)

        self.tree_dusuk.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree_dusuk.tag_configure("sıfır", foreground=C["error"])
        self.tree_dusuk.tag_configure("az",    foreground=C["warning"])

        # Alt butonlar
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(4, 12))

        ctk.CTkButton(btn_frame, text="↻ Yenile", fg_color=C["card"],
                      text_color=C["text"], command=self.yenile, width=100).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="📄 PDF Rapor İndir", fg_color="#533483",
                      hover_color="#6a45a0", text_color="white", command=self._pdf_rapor,
                      width=160).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text=" DB Yedekle", fg_color=C["accent"],
                      hover_color="#2a7fdf", text_color="white", command=self._db_yedekle,
                      width=130).pack(side="right", padx=6)
        ctk.CTkButton(btn_frame, text="📂 DB Geri Yükle", fg_color=C["warning"],
                      hover_color="#e68a00", text_color="white", command=self._db_geri_yukle,
                      width=140).pack(side="right", padx=6)

    def yenile(self):
        ist = db.istatistikler()
        self._deger_lbls["Toplam Oyun"].configure(text=str(ist["toplam_oyun"]))
        self._deger_lbls["Toplam Stok"].configure(text=str(ist["toplam_stok"]))
        self._deger_lbls["Düşük Stok"].configure(text=str(ist["dusuk_stok"]))
        self._deger_lbls["Toplam Satış"].configure(text=str(ist["toplam_satis"]))
        self._deger_lbls["Toplam Ciro"].configure(text=f"{ist['toplam_ciro']:,.0f} ₺")

        self.tree_dusuk.delete(*self.tree_dusuk.get_children())
        for o in db.tum_oyunlar():
            if o["stok"] <= 2:
                tag = "sıfır" if o["stok"] == 0 else "az"
                self.tree_dusuk.insert("", "end",
                    values=(o["ad"], o["platform"], o["stok"]), tags=(tag,))

    def _pdf_rapor(self):
        """Tüm oyunlar + satışları PDF rapor olarak dışa aktarır."""
        rows = db.tum_oyunlar()
        if not rows:
            messagebox.showinfo("Bilgi", "Veritabanında oyun yok.", parent=self)
            return
        oyunlar = [dict(r) for r in rows]
        satislar_raw = db.tum_satislar()
        satislar = [dict(s) for s in satislar_raw] if satislar_raw else []

        yol = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="oyun_arsiv_rapor.pdf",
            title="PDF Rapor Kaydet")
        if not yol:
            return
        try:
            bk.pdf_rapor_olustur(oyunlar, satislar, yol)
            messagebox.showinfo("Başarılı",
                f"PDF rapor oluşturuldu:\n{yol}\n"
                f"({len(oyunlar)} oyun, {len(satislar)} satış kaydı)", parent=self)
            if sys.platform == "linux":
                subprocess.Popen(["xdg-open", yol])
        except Exception as e:
            messagebox.showerror("Hata", str(e), parent=self)

    def _db_yedekle(self):
        """Veritabanını yedekler."""
        yol = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Veritabanı", "*.db"), ("Tüm Dosyalar", "*.*")],
            initialfile=f"oyunlar_yedek_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.db",
            title="Veritabanı Yedekle")
        if not yol:
            return
        try:
            db.db_yedekle(yol)
            messagebox.showinfo("Başarılı",
                f"Veritabanı yedeklendi:\n{yol}", parent=self)
        except Exception as e:
            messagebox.showerror("Hata", str(e), parent=self)

    def _db_geri_yukle(self):
        """Yedek veritabanını geri yükler."""
        yol = filedialog.askopenfilename(
            filetypes=[("SQLite Veritabanı", "*.db"), ("Tüm Dosyalar", "*.*")],
            title="Yedek Veritabanı Seç")
        if not yol:
            return
        if not messagebox.askyesno("Onayla",
            "Mevcut veriler yedeklenip, seçilen dosyadaki veriler geri yüklenecek.\n"
            "Devam etmek istiyor musunuz?", parent=self):
            return
        try:
            db.db_geri_yukle(yol)
            messagebox.showinfo("Başarılı",
                "Veritabanı başarıyla geri yüklendi!\n"
                "Uygulama verileri güncellendi.", parent=self)
            self.yenile()
        except Exception as e:
            messagebox.showerror("Hata", str(e), parent=self)


# ════════════════════════════════════════════════════════
#  TAKSİT HESAPLAMA SAYFASI
# ════════════════════════════════════════════════════════
class TaksitPage(ctk.CTkFrame):
    RATES = {
        2: 6.41,  3: 8.28,  4: 10.15, 5: 12.01,  6: 13.88,
        7: 15.75, 8: 17.62, 9: 19.49, 10: 21.36, 11: 23.23, 12: 25.10
    }

    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._secili_taksit = None
        self._kdv_price     = 0.0
        self._kdv_amount    = 0.0
        self._price         = 0.0
        self._row_data      = {}   # {taksit_no: (rate, total, monthly)}
        self._olustur()

    # ── UI ──────────────────────────────────────────────
    def _olustur(self):
        # Başlık
        baslik_frame = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        baslik_frame.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(baslik_frame, text="💳  Taksit Hesaplama",
                     font=("Segoe UI", 16, "bold"), text_color=C["accent"]).pack(
                     side="left", padx=16, pady=10)
        ctk.CTkLabel(baslik_frame, text="Vade farkı ve taksit hesaplayıcı",
                     font=("Segoe UI", 10), text_color=C["text2"]).pack(
                     side="left", pady=10)

        # Girdi alanları
        giris = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        giris.pack(fill="x", padx=10, pady=(0, 8))

        ic = ctk.CTkFrame(giris, fg_color="transparent")
        ic.pack(padx=18, pady=14, fill="x")

        def giris_blok(parent, etiket, placeholder, default=""):
            blok = ctk.CTkFrame(parent, fg_color="transparent")
            blok.pack(side="left", fill="x", expand=True, padx=(0, 12))
            ctk.CTkLabel(blok, text=etiket, font=("Segoe UI", 10, "bold"),
                         text_color=C["text2"]).pack(anchor="w", pady=(0, 4))
            e = ctk.CTkEntry(blok, placeholder_text=placeholder,
                             font=("Segoe UI", 14, "bold"), height=40)
            if default:
                e.insert(0, default)
            e.pack(fill="x")
            return e

        self.e_fiyat   = giris_blok(ic, "ÜRÜN FİYATI (KDV Hariç)  ₺", "0")
        self.e_kdv     = giris_blok(ic, "KDV ORANI  %", "%", "8")
        self.e_musteri = giris_blok(ic, "MÜŞTERİ ADI (Opsiyonel)", "Ahmet Yılmaz")

        btn_giris = ctk.CTkFrame(ic, fg_color="transparent")
        btn_giris.pack(side="left", padx=(0, 0), fill="y")
        ctk.CTkLabel(btn_giris, text=" ", font=("Segoe UI", 10)).pack()
        ctk.CTkButton(btn_giris, text="Hesapla", width=110, height=40,
                      fg_color=C["accent"], hover_color="#2a7fdf",
                      text_color="white", font=("Segoe UI", 13, "bold"),
                      command=self._hesapla).pack(pady=(4, 0))

        # Özet bandı
        self.lbl_ozet = ctk.CTkLabel(self, text="👆  Fiyat girin ve Hesapla'ya tıklayın.",
                                      font=("Segoe UI", 11), text_color=C["text2"],
                                      fg_color=C["sidebar"], corner_radius=8)
        self.lbl_ozet.pack(fill="x", padx=10, pady=(0, 6), ipady=8)

        # Taksit tablosu
        tf = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        tf.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        cols = ["taksit", "vade", "toplam", "aylik"]
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                  style="Dark.Treeview", selectmode="browse")
        sutunlar = [
            ("taksit", "Taksit Seçeneği", 160, tk.CENTER),
            ("vade",   "Vade Farkı",       120, tk.CENTER),
            ("toplam", "Toplam Tutar (KDV+Vade)", 230, tk.E),
            ("aylik",  "Aylık Ödeme",       170, tk.E),
        ]
        for key, baslik, gen, anchor in sutunlar:
            self.tree.heading(key, text=baslik)
            self.tree.column(key, width=gen, minwidth=gen, anchor=anchor)

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        vsb.grid(row=0, column=1, sticky="ns", pady=8)
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._satir_secildi)

        # Hint
        self.lbl_hint = ctk.CTkLabel(self, text="",
                                      font=("Segoe UI", 10), text_color=C["text2"])
        self.lbl_hint.pack(padx=14, pady=(0, 4))

        # WhatsApp / Kopyala buton alanı
        self.wa_frame = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=10)
        # (başlangıçta gizli — satır seçince gösterilir)

        # WhatsApp başlık
        wa_baslik = ctk.CTkFrame(self.wa_frame, fg_color="transparent")
        wa_baslik.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(wa_baslik, text="📤  WhatsApp'ta Gönder",
                     font=("Segoe UI", 12, "bold"), text_color="#25d366").pack(side="left")

        # Önizleme metin kutusu
        self.txt_onizleme = ctk.CTkTextbox(self.wa_frame, height=150,
                                            font=("Courier New", 10),
                                            fg_color=C["tree_bg"],
                                            text_color=C["tree_fg"],
                                            corner_radius=8)
        self.txt_onizleme.pack(fill="x", padx=16, pady=(0, 8))

        # Butonlar
        btn_wrap = ctk.CTkFrame(self.wa_frame, fg_color="transparent")
        btn_wrap.pack(fill="x", padx=16, pady=(0, 14))
        self.btn_wa = ctk.CTkButton(
            btn_wrap, text="📲  WhatsApp'ta Aç", width=180,
            fg_color="#25d366", hover_color="#1aa34a",
            text_color="white", font=("Segoe UI", 12, "bold"),
            command=self._whatsapp_ac)
        self.btn_wa.pack(side="left", padx=(0, 10))
        self.btn_kopyala = ctk.CTkButton(
            btn_wrap, text="📋  Kopyala", width=120,
            fg_color=C["card"], hover_color=C["accent"],
            text_color=C["text"], font=("Segoe UI", 12),
            command=self._kopyala)
        self.btn_kopyala.pack(side="left")

    # ── Hesaplama ────────────────────────────────────────
    def _hesapla(self):
        try:
            fiyat = float(self.e_fiyat.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir fiyat giriniz!", parent=self)
            return
        try:
            kdv = float(self.e_kdv.get().strip() or 0)
        except ValueError:
            kdv = 0.0

        if fiyat <= 0:
            messagebox.showwarning("Uyarı", "Sıfırdan büyük bir fiyat giriniz!", parent=self)
            return

        self._price      = fiyat
        kdv_tutar        = fiyat * (kdv / 100)
        self._kdv_amount = kdv_tutar
        self._kdv_price  = fiyat + kdv_tutar
        self._row_data   = {}
        self._secili_taksit = None

        self.lbl_ozet.configure(
            text=f"  Ham Fiyat: {self._fmt(fiyat)}   KDV (%{kdv:.0f}): {self._fmt(kdv_tutar)}   "
                 f"Vade Öncesi Tutar: {self._fmt(self._kdv_price)}",
            text_color=C["accent"])

        self.tree.delete(*self.tree.get_children())
        for i in range(2, 13):
            rate    = self.RATES[i]
            total   = self._kdv_price * (1 + rate / 100)
            monthly = total / i
            self._row_data[i] = (rate, total, monthly)
            self.tree.insert("", "end", iid=str(i),
                values=(f"{i} Taksit", f"%{rate}", self._fmt(total), self._fmt(monthly)))

        self.lbl_hint.configure(text="👆  Bir taksit seçeneğine tıklayın → WhatsApp ile gönderin")
        self.wa_frame.pack_forget()

    def _satir_secildi(self, event=None):
        sel = self.tree.selection()
        if not sel:
            self._secili_taksit = None
            self.wa_frame.pack_forget()
            return
        self._secili_taksit = int(sel[0])
        self._onizleme_guncelle()
        self.wa_frame.pack(fill="x", padx=10, pady=(0, 10), before=self.lbl_hint)

    def _mesaj_olustur(self):
        if self._secili_taksit is None:
            return ""
        t = self._secili_taksit
        rate, total, monthly = self._row_data[t]
        musteri   = self.e_musteri.get().strip()
        selamlama = f"Sayın {musteri},\n\n" if musteri else "Merhaba,\n\n"
        return (
            f"{selamlama}"
            f"🎮 *Oyun Arşiv – Taksit Bilgisi*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Ürün Fiyatı (KDV Hariç): *{self._fmt(self._price)}*\n"
            f"🧾 KDV: *{self._fmt(self._kdv_amount)}*\n"
            f"💰 KDV Dahil Fiyat: *{self._fmt(self._kdv_price)}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Seçilen Taksit: *{t} Ay*\n"
            f"📈 Vade Farkı: *%{rate}*\n"
            f"💳 Aylık Ödeme: *{self._fmt(monthly)}*\n"
            f"🔢 Toplam Tutar: *{self._fmt(total)}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"İyi oyunlar! 🕹️"
        )

    def _onizleme_guncelle(self):
        mesaj = self._mesaj_olustur()
        self.txt_onizleme.configure(state="normal")
        self.txt_onizleme.delete("1.0", "end")
        self.txt_onizleme.insert("1.0", mesaj)
        self.txt_onizleme.configure(state="disabled")

    def _whatsapp_ac(self):
        mesaj = self._mesaj_olustur()
        if not mesaj:
            return
        url = "https://wa.me/?text=" + urllib.parse.quote(mesaj)
        webbrowser.open(url)

    def _kopyala(self):
        mesaj = self._mesaj_olustur()
        if not mesaj:
            return
        self.clipboard_clear()
        self.clipboard_append(mesaj)
        self.btn_kopyala.configure(text="✅  Kopyalandı!", fg_color=C["success"])
        self.after(2500, lambda: self.btn_kopyala.configure(
            text="📋  Kopyala", fg_color=C["card"]))

    @staticmethod
    def _fmt(n):
        return f"{n:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")

    def yenile(self):
        pass  # Taksit sayfası için yenileme gerekmez


# ════════════════════════════════════════════════════════
#  ANA UYGULAMA
# ════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ── Ekrana göre otomatik ölçekleme ──
        # Temel çözünürlük: 1920 genişlik
        ekran_w = self.winfo_screenwidth()
        ekran_h = self.winfo_screenheight()
        # DPI bazlı ölçekleme: 1920×1080 temel, max 2.0 (4K desteği)
        olcek = max(0.80, min(2.0, ekran_w / 1920))
        ctk.set_widget_scaling(olcek)
        ctk.set_window_scaling(olcek)

        self.title("Oyun Arşiv")
        # Pencere boyutunu ekrana oran olarak aç
        pencere_w = min(1300, int(ekran_w * 0.85))
        pencere_h = min(800,  int(ekran_h * 0.85))
        self.geometry(f"{pencere_w}x{pencere_h}")
        self.minsize(900, 600)
        self.configure(fg_color=C["bg"])

        # Uygulama ikonu
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            try:
                icon_img = Image.open(icon_path)
                self._icon_photo = ImageTk.PhotoImage(icon_img)
                self.iconphoto(True, self._icon_photo)
            except Exception:
                pass

        db.tablelari_olustur()
        ttk_style_ayarla()

        # Her açılışta otomatik yedek al (son 5 yedek tutulur)
        try:
            self._otomatik_yedek()
        except Exception:
            pass

        self._sayfalar = {}
        self._aktif_btn = None

        self._ui_olustur()
        self.show_page("oyunlar")
        # Uygulama tamamen yüklendikten sonra güncelleme kontrolü
        self.after(3000, self._guncelleme_kontrol_baslat)

    def _otomatik_yedek(self):
        """Uygulama açılışında otomatik yedek alır, en fazla 5 yedek tutar."""
        import glob
        yedek_klasor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yedekler")
        os.makedirs(yedek_klasor, exist_ok=True)
        if os.path.exists(db.DB_PATH):
            db.db_yedekle()  # tarihli yedek oluşturur
            # Eski yedekleri temizle (son 5 tane tut)
            yedekler = sorted(glob.glob(os.path.join(yedek_klasor, "oyunlar_yedek_*.db")))
            while len(yedekler) > 5:
                os.remove(yedekler.pop(0))

    def _ui_olustur(self):
        # Ana layout: sidebar | içerik
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar ──
        sidebar = ctk.CTkFrame(self, width=220, fg_color=C["sidebar"],
                                corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="🎮 Oyun Arşiv",
                     font=("Segoe UI", 17, "bold"),
                     text_color=C["accent"]).pack(pady=(28, 6), padx=16)
        ctk.CTkLabel(sidebar, text="Video Oyun Yönetimi",
                     font=("Segoe UI", 10), text_color=C["text2"]).pack(pady=(0, 24))

        ttk.Separator(sidebar).pack(fill="x", padx=16)

        self._nav_btns = {}
        navlar = [
            ("oyunlar",  "🎮  Oyunlar"),
            ("stok",     "📦  Stok"),
            ("satislar", "💰  Satışlar"),
            ("rapor",    "📊  Rapor"),
            ("taksit",   "💳  Taksit"),
        ]
        for page, label in navlar:
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w",
                font=("Segoe UI", 13),
                fg_color="transparent", hover_color=C["card"],
                text_color=C["text"],
                corner_radius=8, height=44,
                command=lambda p=page: self.show_page(p))
            btn.pack(fill="x", padx=10, pady=3)
            self._nav_btns[page] = btn

        # Alt bilgiler
        ctk.CTkFrame(sidebar, height=1, fg_color=C["card"]).pack(
            fill="x", padx=16, side="bottom", pady=(0, 8))
        ctk.CTkLabel(sidebar, text=f"v{updater.VERSION}  |  Oyun Arşiv",
                     font=("Segoe UI", 9), text_color=C["text2"]).pack(
                     side="bottom", pady=4)

        # ── Tema toggle butonu ──
        ttk.Separator(sidebar).pack(fill="x", padx=16, side="bottom", pady=(4, 0))
        self.btn_tema = ctk.CTkButton(
            sidebar,
            text="☀️  Açık Mod" if _aktif_tema == "dark" else "🌙  Koyu Mod",
            anchor="w",
            font=("Segoe UI", 12, "bold"),
            fg_color="#2a4a7f" if _aktif_tema == "dark" else "#c5cfe0",
            hover_color=C["accent"],
            text_color=C["text"],
            corner_radius=8, height=40,
            command=self._tema_degistir)
        self.btn_tema.pack(fill="x", padx=10, pady=(4, 10), side="bottom")

        # ── Güncelleme bildirim bloğu (başlangıçta gizli) ──
        self._sidebar = sidebar
        self._guncelle_frame = ctk.CTkFrame(
            sidebar, fg_color="#1a3d1a",
            border_color="#25d366", border_width=1,
            corner_radius=8)
        # pack edilmiyor — güncelleme gelince pack edilecek
        self._lbl_guncelle = ctk.CTkLabel(
            self._guncelle_frame,
            text="", font=("Segoe UI", 10, "bold"),
            text_color="#4ade80", wraplength=170)
        self._lbl_guncelle.pack(padx=10, pady=(8, 2))
        self._btn_guncelle_indir = ctk.CTkButton(
            self._guncelle_frame,
            text="🔄  Güncelle", height=32,
            text_color="white", font=("Segoe UI", 11, "bold"),
            fg_color="#25d366", hover_color="#1aa34a",
            command=self._guncelleme_baslat)
        self._btn_guncelle_indir.pack(fill="x", padx=10, pady=(2, 8))
        self._guncelle_zipurl = ""  # indirilecek URL

        # ── İçerik alanı ──
        self.content = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

    # ── Güncelleme ────────────────────────────────────────────────
    def _guncelleme_kontrol_baslat(self):
        """Arka planda GitHub kontrolü başlatır."""
        updater.guncelleme_kontrol(self._guncelleme_bulundu)

    def _guncelleme_bulundu(self, yeni_surum: str, zipball: str, html_url: str):
        """Arka plandan çağrılır — UI güncellemesini after ile ana thread'e taşı."""
        self._guncelle_zipurl = zipball
        self.after(0, lambda: self._guncelleme_bildirim_goster(yeni_surum, html_url))

    def _guncelleme_bildirim_goster(self, yeni_surum: str, html_url: str):
        self._lbl_guncelle.configure(
            text=f"🌟 v{yeni_surum} mevcut!\nMevcut: v{updater.VERSION}")
        self._guncelle_frame.pack(
            fill="x", padx=10, pady=(4, 0),
            side="bottom", before=self.btn_tema)

    def _guncelleme_baslat(self):
        if not self._guncelle_zipurl:
            return
        self._btn_guncelle_indir.configure(
            text="⏳  İndiriliyor...", state="disabled", fg_color=C["card"])
        updater.guncelleme_indir_ve_uygula(
            zipball_url  = self._guncelle_zipurl,
            ilerleme_cb  = self._guncelleme_ilerleme,
            bitti_cb     = self._guncelleme_bitti,
            hata_cb      = self._guncelleme_hata,
        )

    def _guncelleme_ilerleme(self, yuzde: int):
        self.after(0, lambda: self._btn_guncelle_indir.configure(
            text=f"⏳  İndiriliyor... %{yuzde}"))

    def _guncelleme_bitti(self):
        def _dialog():
            if messagebox.askyesno(
                    "🎉  Güncelleme Hazır!",
                    "Yeni sürüm başarıyla kuruldu.\n"
                    "Değişikliklerin geçerli olması için uygulama yeniden başlatılacak.\n\n"
                    "Hemen yeniden başlat hamak ister misiniz?",
                    parent=self):
                updater.uygulamayi_yeniden_baslat()
            else:
                self._btn_guncelle_indir.configure(
                    text="✅  Kuruldu, yeniden başlat",
                    state="normal", fg_color="#25d366")
        self.after(0, _dialog)

    def _guncelleme_hata(self, mesaj: str):
        def _dialog():
            messagebox.showerror(
                "Güncelleme Hatası",
                f"Güncelleme indirilemedi:\n{mesaj}\n\n"
                f"GitHub sayfasından manuel olarak indirebilirsiniz:\n"
                f"https://github.com/EmreBekcan/oyun-arsiv/releases",
                parent=self)
            self._btn_guncelle_indir.configure(
                text="🔄  Güncelle", state="normal", fg_color="#25d366")
        self.after(0, _dialog)

    # ── Tema değiştirme ───────────────────────────────────────────────
    def _tema_degistir(self):
        global _aktif_tema, C
        _aktif_tema = "light" if _aktif_tema == "dark" else "dark"
        C.update(TEMALAR[_aktif_tema])
        ctk.set_appearance_mode(_aktif_tema)
        _ayar_kaydet(tema=_aktif_tema)   # kalıcı kaydet
        ttk_style_ayarla()

        # Aktif sayfayı hatırla, tüm widget’ları yeniden oluştur
        aktif = self._aktif_btn or "oyunlar"
        for w in self.winfo_children():
            w.destroy()
        self.configure(fg_color=C["bg"])
        self._sayfalar = {}
        self._aktif_btn = None
        self._ui_olustur()
        self.show_page(aktif)

    def show_page(self, page: str):
        # Aktif buton rengi
        for adı, btn in self._nav_btns.items():
            btn.configure(fg_color=C["accent"] if adı == page else "transparent")

        # Sayfayı oluştur (lazy)
        if page not in self._sayfalar:
            cls_map = {
                "oyunlar":  OyunlarPage,
                "stok":     StokPage,
                "satislar": SatislarPage,
                "rapor":    RaporPage,
                "taksit":   TaksitPage,
            }
            self._sayfalar[page] = cls_map[page](self.content)
            self._sayfalar[page].grid(row=0, column=0, sticky="nsew")

        # Diğer sayfaları gizle, aktifi göster
        for adı, frame in self._sayfalar.items():
            if adı == page:
                frame.tkraise()
                if hasattr(frame, "yenile"):
                    frame.yenile()
            
        self._aktif_btn = page


# ════════════════════════════════════════════════════════
#  GİRİŞ NOKTASI
# ════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
