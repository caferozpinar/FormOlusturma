#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enterprise Maliyet Servisi — Güvenli formül, hesaplama, snapshot, versiyon."""

import ast
import operator
import math
import json
from typing import Tuple, Optional
from datetime import datetime

from uygulama.altyapi.enterprise_maliyet_repo import EnterpriseMaliyetRepository
from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("enterprise_maliyet_srv")


# ═══════════════════════════════════════════
# GÜVENLİ FORMÜL PARSER
# ═══════════════════════════════════════════

# İzin verilen operatörler
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}

# İzin verilen fonksiyonlar
_FUNCTIONS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "sqrt": math.sqrt,
}


def _guvenli_eval_node(node, degiskenler: dict):
    """AST node'u güvenli olarak değerlendirir."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"İzinsiz sabit: {node.value}")

    elif isinstance(node, ast.Name):
        if node.id in degiskenler:
            return degiskenler[node.id]
        raise ValueError(f"Tanımsız değişken: {node.id}")

    elif isinstance(node, ast.BinOp):
        op = _OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"İzinsiz operatör: {type(node.op).__name__}")
        sol = _guvenli_eval_node(node.left, degiskenler)
        sag = _guvenli_eval_node(node.right, degiskenler)
        if isinstance(node.op, ast.Div) and sag == 0:
            raise ValueError("Sıfıra bölme hatası")
        return op(sol, sag)

    elif isinstance(node, ast.UnaryOp):
        op = _OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"İzinsiz unary: {type(node.op).__name__}")
        return op(_guvenli_eval_node(node.operand, degiskenler))

    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            fn = _FUNCTIONS.get(node.func.id)
            if fn is None:
                raise ValueError(f"İzinsiz fonksiyon: {node.func.id}")
            args = [_guvenli_eval_node(a, degiskenler) for a in node.args]
            return fn(*args)
        raise ValueError("Karmaşık fonksiyon çağrısı izinsiz")

    elif isinstance(node, ast.Expression):
        return _guvenli_eval_node(node.body, degiskenler)

    else:
        raise ValueError(f"İzinsiz AST node: {type(node).__name__}")


def guvenli_formul_hesapla(formul: str, degiskenler: dict) -> float:
    """
    Güvenli formül değerlendirici.

    İzinli: +, -, *, /, **, %, min(), max(), abs(), round(), ceil(), floor(), sqrt()
    İzinsiz: import, exec, eval, __builtins__, attribute erişimi

    Örnek:
        guvenli_formul_hesapla("A * B + C", {"A": 100, "B": 2.5, "C": 50})
        → 300.0
    """
    # Güvenlik kontrolü
    yasakli = ["import", "exec", "eval", "__", "open", "os.", "sys."]
    formul_lower = formul.lower()
    for y in yasakli:
        if y in formul_lower:
            raise ValueError(f"Güvenlik ihlali: '{y}' yasaklı")

    try:
        tree = ast.parse(formul, mode='eval')
        sonuc = _guvenli_eval_node(tree, degiskenler)
        return round(float(sonuc), 4)
    except (SyntaxError, TypeError) as e:
        raise ValueError(f"Formül hatası: {e}")


# ═══════════════════════════════════════════
# SERVİS
# ═══════════════════════════════════════════

class EnterpriseMaliyetServisi:
    def __init__(self, repo: EnterpriseMaliyetRepository):
        self.repo = repo

    # ── VERSİYON YÖNETİMİ ──

    def yeni_urun_versiyonu(self, urun_id: str) -> Tuple[str, int]:
        return self.repo.urun_versiyon_kopyala(urun_id)

    def yeni_alt_kalem_versiyonu(self, alt_kalem_id: str,
                                   urun_versiyon_id: str) -> Tuple[str, int]:
        return self.repo.alt_kalem_versiyonu_kopyala(
            alt_kalem_id, urun_versiyon_id)

    # ── PARAMETRE TİPLERİ ──

    def tip_listesi(self) -> list[dict]:
        return self.repo.parametre_tipleri()

    # ── ÜRÜN PARAMETRE ──

    def urun_parametre_ekle(self, urun_versiyon_id: str, ad: str,
                             tip_id: str, zorunlu: int = 0,
                             varsayilan: str = "", sira: int = 0) -> str:
        return self.repo.urun_parametre_ekle(
            urun_versiyon_id, ad, tip_id, zorunlu, varsayilan, sira)

    def urun_parametreleri(self, urun_versiyon_id: str) -> list[dict]:
        return self.repo.urun_parametreleri(urun_versiyon_id)

    # ── MALİYET ŞABLON ──

    def sablon_olustur(self, akv_id: str, formul: str,
                        kar: float = 0) -> Tuple[bool, str, Optional[str]]:
        try:
            # Formül syntax kontrolü
            ast.parse(formul, mode='eval')
            sid = self.repo.sablon_olustur(akv_id, formul, True, kar)
            return True, "Şablon oluşturuldu.", sid
        except SyntaxError as e:
            return False, f"Formül hatası: {e}", None

    def sablon_parametresi_ekle(self, sablon_id: str, ad: str,
                                 degisken: str, varsayilan: float = 0) -> str:
        return self.repo.sablon_parametre_ekle(sablon_id, ad, degisken, varsayilan)

    # ── MALİYET HESAPLAMA ──

    def birim_fiyat_hesapla(self, akv_id: str,
                              parametre_degerleri: dict = None,
                              konum_fiyat: float = 0) -> Tuple[bool, str, dict]:
        """
        Alt kalem versiyonu için birim fiyat hesaplar.
        Returns: (ok, mesaj, {birim_fiyat, kar, konum_fiyat, formul, parametreler})
        """
        sablon = self.repo.aktif_sablon(akv_id)
        if not sablon:
            return False, "Aktif maliyet şablonu yok.", {}

        # Parametreleri hazırla
        sablon_params = self.repo.sablon_parametreleri(sablon["id"])
        degiskenler = {}
        for sp in sablon_params:
            kod = sp["degisken_kodu"]
            if parametre_degerleri and kod in parametre_degerleri:
                degiskenler[kod] = float(parametre_degerleri[kod])
            else:
                degiskenler[kod] = float(sp["varsayilan_deger"])

        # Konum fiyatını KF değişkeni olarak ekle
        degiskenler["KF"] = konum_fiyat

        try:
            birim = guvenli_formul_hesapla(sablon["formul_ifadesi"], degiskenler)
        except ValueError as e:
            return False, str(e), {}

        # Kar oranı
        kar = sablon["kar_orani"]
        if kar > 0:
            birim_karli = birim * (1 + kar / 100)
        else:
            birim_karli = birim

        return True, "Hesaplandı.", {
            "birim_fiyat": round(birim_karli, 2),
            "birim_fiyat_karsiz": round(birim, 2),
            "kar_orani": kar,
            "konum_fiyat": konum_fiyat,
            "formul": sablon["formul_ifadesi"],
            "parametreler": degiskenler,
        }

    def toplam_fiyat_hesapla(self, akv_id: str, miktar: int = 1,
                               parametre_degerleri: dict = None,
                               konum_fiyat: float = 0) -> Tuple[bool, str, dict]:
        ok, msg, sonuc = self.birim_fiyat_hesapla(
            akv_id, parametre_degerleri, konum_fiyat)
        if not ok:
            return False, msg, {}
        sonuc["miktar"] = miktar
        sonuc["toplam_fiyat"] = round(sonuc["birim_fiyat"] * miktar, 2)
        return True, msg, sonuc

    # ── SNAPSHOT ──

    def snapshot_olustur(self, proje_id: str, belge_id: str,
                          revizyon_no: int, urun_id: str,
                          urun_versiyon_id: str, alt_kalem_id: str,
                          akv_id: str, parametre_degerleri: dict,
                          miktar: int, konum_fiyat: float,
                          opsiyon_mu: bool = False) -> Tuple[bool, str, Optional[str]]:
        """Hesapla + snapshot kaydet."""
        ok, msg, sonuc = self.toplam_fiyat_hesapla(
            akv_id, miktar, parametre_degerleri, konum_fiyat)
        if not ok:
            return False, msg, None

        sid = self.repo.snapshot_kaydet(
            proje_id=proje_id,
            belge_id=belge_id,
            revizyon_no=revizyon_no,
            urun_id=urun_id,
            urun_versiyon_id=urun_versiyon_id,
            alt_kalem_id=alt_kalem_id,
            alt_kalem_versiyon_id=akv_id,
            parametre_degerleri=sonuc["parametreler"],
            formul_ifadesi=sonuc["formul"],
            birim_fiyat=sonuc["birim_fiyat"],
            miktar=miktar,
            toplam_fiyat=sonuc["toplam_fiyat"],
            kar_orani=sonuc["kar_orani"],
            konum_fiyat=konum_fiyat,
            opsiyon_mu=opsiyon_mu,
            olusturma_yili=datetime.now().year,
        )
        return True, f"Snapshot: ₺{sonuc['toplam_fiyat']:,.2f}", sid

    def proje_snapshots(self, proje_id: str, revizyon: int = None) -> list[dict]:
        return self.repo.proje_snapshots(proje_id, revizyon)

    def proje_toplam(self, proje_id: str, revizyon: int = None) -> dict:
        """Proje toplam maliyet (opsiyonlar hariç)."""
        snaps = self.proje_snapshots(proje_id, revizyon)
        toplam = sum(s["toplam_fiyat"] for s in snaps if not s["opsiyon_mu"])
        opsiyon = sum(s["toplam_fiyat"] for s in snaps if s["opsiyon_mu"])
        return {
            "toplam": round(toplam, 2),
            "opsiyon_toplam": round(opsiyon, 2),
            "genel_toplam": round(toplam + opsiyon, 2),
            "kalem_sayisi": len(snaps),
        }

    # ── KONUM FİYAT ──

    def konum_fiyat(self, ulke: str, sehir: str) -> float:
        return self.repo.konum_fiyat_getir(ulke, sehir)
