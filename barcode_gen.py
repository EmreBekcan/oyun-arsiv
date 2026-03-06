"""
Oyun Arşiv - Barkod Üretici
Code128 barkod üretimi + PNG kaydı + PDF etiket çıktısı
"""

import os
import io
from pathlib import Path

BARKOD_KLASOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "barkodlar")


def klasor_hazirla():
    Path(BARKOD_KLASOR).mkdir(parents=True, exist_ok=True)


def barkod_olustur_png(barkod_no: str, oyun_adi: str = "") -> str:
    """
    Verilen barkod numarası için PNG dosyası oluşturur.
    Dosya yolunu döndürür.
    """
    import barcode
    from barcode.writer import ImageWriter

    klasor_hazirla()
    dosya_adi = os.path.join(BARKOD_KLASOR, barkod_no)

    writer = ImageWriter()
    writer.set_options({
        "module_width":  0.8,
        "module_height": 15.0,
        "font_size":     8,
        "text_distance": 3.0,
        "quiet_zone":    3.0,
        "dpi":           200,
    })

    code = barcode.get("code128", barkod_no, writer=writer)
    # Altta oyun adını ekle (max 40 karakter)
    alt_yazi = oyun_adi[:40] if oyun_adi else barkod_no
    tam_yol = code.save(dosya_adi, options={"text": alt_yazi})
    return tam_yol


def barkod_img_getir(barkod_no: str, oyun_adi: str = ""):
    """
    Barkod PNG'sini oluşturur ve PIL Image olarak döndürür.
    """
    from PIL import Image
    png_yolu = barkod_olustur_png(barkod_no, oyun_adi)
    return Image.open(png_yolu)


def barkod_bytes_getir(barkod_no: str, oyun_adi: str = "") -> bytes:
    """
    Barkod PNG'sini bytes olarak döndürür (Tkinter PhotoImage için).
    """
    import barcode
    from barcode.writer import ImageWriter
    from PIL import Image

    writer = ImageWriter()
    writer.set_options({
        "module_width":  0.8,
        "module_height": 15.0,
        "font_size":     8,
        "text_distance": 3.0,
        "quiet_zone":    3.0,
        "dpi":           150,
    })

    code = barcode.get("code128", barkod_no, writer=writer)
    alt_yazi = oyun_adi[:40] if oyun_adi else barkod_no

    buf = io.BytesIO()
    code.write(buf, options={"text": alt_yazi})
    buf.seek(0)
    img = Image.open(buf)
    # Yeniden boyutlandır: genişlik sabit 400px
    oran = 400 / img.width
    yeni_yukseklik = int(img.height * oran)
    img = img.resize((400, yeni_yukseklik), Image.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _poppins_kaydet():
    """Poppins fontunu ReportLab'a kaydeder (Türkçe karakter desteği)."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    regular = os.path.join(font_dir, "Poppins-Regular.ttf")
    bold    = os.path.join(font_dir, "Poppins-Bold.ttf")
    try:
        pdfmetrics.registerFont(TTFont("Poppins", regular))
        pdfmetrics.registerFont(TTFont("Poppins-Bold", bold))
        return True
    except Exception:
        return False


def pdf_etiket_olustur(oyunlar: list, dosya_yolu: str = None) -> str:
    """
    Birden fazla oyun için A4 sayfa üzerine barkod etiketleri oluşturur.
    oyunlar: [{"barkod": "OYUN000001", "ad": "...", "platform": "..."}, ...]
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import barcode
    from barcode.writer import ImageWriter

    use_poppins = _poppins_kaydet()
    font_normal = "Poppins" if use_poppins else "Helvetica"
    font_bold   = "Poppins-Bold" if use_poppins else "Helvetica-Bold"

    klasor_hazirla()
    if dosya_yolu is None:
        dosya_yolu = os.path.join(BARKOD_KLASOR, "barkod_etikitler.pdf")

    # Etiket boyutları (3 sütun x 10 satır = 30 etiket/sayfa)
    sayfa_gen, sayfa_yuk = A4  # (595.28, 841.89) pt
    sutun_sayisi  = 3
    satir_sayisi  = 10
    kenar_bosluk  = 8 * mm
    etiket_gen    = (sayfa_gen - 2 * kenar_bosluk) / sutun_sayisi
    etiket_yuk    = (sayfa_yuk - 2 * kenar_bosluk) / satir_sayisi

    c = canvas.Canvas(dosya_yolu, pagesize=A4)
    c.setTitle("Oyun Arşiv - Barkod Etiketleri")

    for i, oyun in enumerate(oyunlar):
        sayfa_indeks = i % (sutun_sayisi * satir_sayisi)
        if sayfa_indeks == 0 and i > 0:
            c.showPage()

        sutun = sayfa_indeks % sutun_sayisi
        satir = sayfa_indeks // sutun_sayisi

        x = kenar_bosluk + sutun * etiket_gen
        y = sayfa_yuk - kenar_bosluk - (satir + 1) * etiket_yuk

        # Barkod görselini oluştur
        writer = ImageWriter()
        writer.set_options({
            "module_width":  0.6,
            "module_height": 10.0,
            "font_size":     6,
            "text_distance": 2.5,
            "quiet_zone":    2.0,
            "dpi":           200,
        })
        code128 = barcode.get("code128", oyun["barkod"], writer=writer)
        barkod_buf = io.BytesIO()
        code128.write(barkod_buf, options={"text": oyun["barkod"]})
        barkod_buf.seek(0)

        img_reader = ImageReader(barkod_buf)
        img_gen = etiket_gen - 4 * mm
        img_yuk = etiket_yuk * 0.55

        c.drawImage(img_reader,
                    x + 2 * mm, y + etiket_yuk * 0.4,
                    width=img_gen, height=img_yuk,
                    preserveAspectRatio=True, anchor="sw")

        # Oyun adı
        c.setFont(font_bold, 7)
        ad_kisalt = oyun["ad"][:28] if len(oyun["ad"]) > 28 else oyun["ad"]
        c.drawString(x + 2 * mm, y + etiket_yuk * 0.28, ad_kisalt)

        # Platform
        c.setFont(font_normal, 6)
        c.drawString(x + 2 * mm, y + etiket_yuk * 0.16, oyun.get("platform", ""))

        # Barkod numarası (alt)
        c.setFont(font_normal, 6)
        c.drawString(x + 2 * mm, y + etiket_yuk * 0.05, oyun["barkod"])

        # Etiket çerçevesi
        c.setStrokeColorRGB(0.85, 0.85, 0.85)
        c.setLineWidth(0.5)
        c.rect(x + 1 * mm, y + 1 * mm, etiket_gen - 2 * mm, etiket_yuk - 2 * mm)

    c.save()
    return dosya_yolu


def pdf_rapor_olustur(oyunlar: list, satislar: list = None, dosya_yolu: str = None) -> str:
    """
    Tüm oyunların detaylı rapor PDF'ini oluşturur.
    oyunlar: [dict(id, ad, platform, tur, yayinci, cikis_yili, fiyat, stok, barkod, notlar), ...]
    satislar: [dict(oyun_adi, platform, miktar, satis_fiyati, satis_tarihi, alici), ...]
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from datetime import datetime

    use_poppins = _poppins_kaydet()
    font_normal = "Poppins" if use_poppins else "Helvetica"
    font_bold   = "Poppins-Bold" if use_poppins else "Helvetica-Bold"

    klasor_hazirla()
    if dosya_yolu is None:
        dosya_yolu = os.path.join(BARKOD_KLASOR, "oyun_rapor.pdf")

    sayfa_gen, sayfa_yuk = A4
    c = canvas.Canvas(dosya_yolu, pagesize=A4)
    c.setTitle("Oyun Arşiv - Tam Rapor")

    kenar = 20 * mm
    y = sayfa_yuk - kenar
    satir_yuk = 16

    def baslik_yaz():
        nonlocal y
        c.setFont(font_bold, 18)
        c.setFillColor(colors.HexColor("#1a1a2e"))
        c.drawString(kenar, y, "Oyun Arşiv - Envantar Raporu")
        y -= 18
        c.setFont(font_normal, 9)
        c.setFillColor(colors.gray)
        c.drawString(kenar, y, f"Oluşturulma: {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  Toplam: {len(oyunlar)} oyun")
        y -= 12
        c.setStrokeColor(colors.HexColor("#4a9fff"))
        c.setLineWidth(1.5)
        c.line(kenar, y, sayfa_gen - kenar, y)
        y -= 20

    def tablo_baslik():
        nonlocal y
        c.setFont(font_bold, 8)
        c.setFillColor(colors.HexColor("#1a1a2e"))
        # Sütun pozisyonları
        c.drawString(kenar,       y, "#")
        c.drawString(kenar + 18,  y, "Oyun Adı")
        c.drawString(kenar + 160, y, "Platform")
        c.drawString(kenar + 240, y, "Tür")
        c.drawString(kenar + 310, y, "Yayıncı")
        c.drawString(kenar + 390, y, "Yıl")
        c.drawString(kenar + 415, y, "Fiyat")
        c.drawString(kenar + 460, y, "Stok")
        c.drawString(kenar + 485, y, "Barkod")
        y -= 4
        c.setStrokeColor(colors.HexColor("#cccccc"))
        c.setLineWidth(0.5)
        c.line(kenar, y, sayfa_gen - kenar, y)
        y -= satir_yuk

    def yeni_sayfa():
        nonlocal y
        c.showPage()
        y = sayfa_yuk - kenar
        tablo_baslik()

    baslik_yaz()
    tablo_baslik()

    for i, o in enumerate(oyunlar):
        if y < kenar + 20:
            yeni_sayfa()

        # Satır arka planı (alternating)
        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#f5f5f5"))
            c.rect(kenar - 2, y - 3, sayfa_gen - 2 * kenar + 4, satir_yuk, fill=1, stroke=0)

        c.setFont(font_normal, 7.5)
        c.setFillColor(colors.black)

        ad = o.get("ad", "")[:30]
        platform = o.get("platform", "")[:15]
        tur = o.get("tur", "-")[:12]
        yayinci = o.get("yayinci", "-")[:16]
        yil = str(o.get("cikis_yili", "-")) if o.get("cikis_yili") else "-"
        fiyat = f"{o.get('fiyat', 0):.0f}₺"
        stok = str(o.get("stok", 0))
        barkod = o.get("barkod", "")

        # Stok rengi
        stok_val = o.get("stok", 0)

        c.drawString(kenar,       y, str(i + 1))
        c.drawString(kenar + 18,  y, ad)
        c.drawString(kenar + 160, y, platform)
        c.drawString(kenar + 240, y, tur)
        c.drawString(kenar + 310, y, yayinci)
        c.drawString(kenar + 390, y, yil)
        c.drawString(kenar + 415, y, fiyat)

        if stok_val == 0:
            c.setFillColor(colors.HexColor("#f44336"))
        elif stok_val <= 2:
            c.setFillColor(colors.HexColor("#ff9800"))
        else:
            c.setFillColor(colors.HexColor("#4caf50"))
        c.drawString(kenar + 460, y, stok)

        c.setFillColor(colors.gray)
        c.setFont(font_normal, 6.5)
        c.drawString(kenar + 485, y, barkod)

        y -= satir_yuk

    # ─── SATIŞ RAPORU ───
    if satislar:
        c.showPage()
        y = sayfa_yuk - kenar
        c.setFont(font_bold, 16)
        c.setFillColor(colors.HexColor("#1a1a2e"))
        c.drawString(kenar, y, "Satış Geçmişi")
        y -= 12
        c.setStrokeColor(colors.HexColor("#4a9fff"))
        c.setLineWidth(1.5)
        c.line(kenar, y, sayfa_gen - kenar, y)
        y -= 20

        # Satış tablo başlığı
        c.setFont(font_bold, 8)
        c.setFillColor(colors.HexColor("#1a1a2e"))
        c.drawString(kenar,       y, "#")
        c.drawString(kenar + 18,  y, "Tarih")
        c.drawString(kenar + 110, y, "Oyun")
        c.drawString(kenar + 280, y, "Platform")
        c.drawString(kenar + 360, y, "Adet")
        c.drawString(kenar + 395, y, "Birim")
        c.drawString(kenar + 440, y, "Toplam")
        c.drawString(kenar + 490, y, "Alıcı")
        y -= 4
        c.setStrokeColor(colors.HexColor("#cccccc"))
        c.line(kenar, y, sayfa_gen - kenar, y)
        y -= satir_yuk

        toplam_ciro = 0.0
        for j, s in enumerate(satislar):
            if y < kenar + 20:
                c.showPage()
                y = sayfa_yuk - kenar

            if j % 2 == 0:
                c.setFillColor(colors.HexColor("#f5f5f5"))
                c.rect(kenar - 2, y - 3, sayfa_gen - 2 * kenar + 4, satir_yuk, fill=1, stroke=0)

            c.setFont(font_normal, 7.5)
            c.setFillColor(colors.black)

            toplam = s.get("miktar", 1) * s.get("satis_fiyati", 0)
            toplam_ciro += toplam

            c.drawString(kenar,       y, str(j + 1))
            c.drawString(kenar + 18,  y, str(s.get("satis_tarihi", ""))[:16])
            c.drawString(kenar + 110, y, str(s.get("oyun_adi", ""))[:30])
            c.drawString(kenar + 280, y, str(s.get("platform", ""))[:15])
            c.drawString(kenar + 360, y, str(s.get("miktar", "")))
            c.drawString(kenar + 395, y, f"{s.get('satis_fiyati', 0):.0f}₺")
            c.setFillColor(colors.HexColor("#4caf50"))
            c.drawString(kenar + 440, y, f"{toplam:.0f}₺")
            c.setFillColor(colors.gray)
            c.drawString(kenar + 490, y, str(s.get("alici", "-"))[:18])
            y -= satir_yuk

        # Ciro toplamı
        y -= 8
        c.setFont(font_bold, 10)
        c.setFillColor(colors.HexColor("#1a1a2e"))
        c.drawString(kenar + 360, y, f"Toplam Ciro: {toplam_ciro:,.0f} ₺")

    c.save()
    return dosya_yolu
