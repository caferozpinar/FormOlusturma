#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enterprise Maliyet Motoru — Güvenli formül parser, hesaplama, snapshot."""

import ast
import json
import operator
from typing import Tuple, Optional

from uygulama.altyapi.versiyon_repo import VersiyonRepository
from uygulama.ortak.yardimcilar import logger_olustur, simdi_iso

logger = logger_olustur("maliyet_motoru")

# ═════════════════════════════════════════════
# GÜVENLİ FORMÜL PARSER
# ═════════════════════════════════════════════

# İzin verilen operatörler
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}

# İzin verilen fonksiyonlar
_FUNCS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
}


def guvenli_eval(formul: str, degiskenler: dict) -> float:
    """
    Güvenli expression parser.
    Sadece matematiksel ifadeler, değişkenler ve temel fonksiyonlar.
    exec/eval kullanmaz — AST üzerinden çalışır.
    """
    try:
        tree = ast.parse(formul, mode="eval")
        return _eval_node(tree.body, degiskenler)
    except Exception as e:
        logger.error(f"Formül hatası: '{formul}' → {e}")
        return 0.0


def _eval_node(node, degiskenler: dict) -> float:
    """AST node'unu recursive evaluate eder."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"İzinsiz sabit: {node.value}")

    elif isinstance(node, ast.Name):
        name = node.id
        if name in degiskenler:
            return float(degiskenler[name])
        raise ValueError(f"Tanımsız değişken: {name}")

    elif isinstance(node, ast.BinOp):
        op = _OPS.get(type(node.op))
        if not op:
            raise ValueError(f"İzinsiz operatör: {type(node.op).__name__}")
        sol = _eval_node(node.left, degiskenler)
        sag = _eval_node(node.right, degiskenler)
        if isinstance(node.op, ast.Div) and sag == 0:
            return 0.0
        return op(sol, sag)

    elif isinstance(node, ast.UnaryOp):
        op = _OPS.get(type(node.op))
        if not op:
            raise ValueError(f"İzinsiz unary: {type(node.op).__name__}")
        return op(_eval_node(node.operand, degiskenler))

    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("İzinsiz fonksiyon çağrısı")
        func = _FUNCS.get(node.func.id)
        if not func:
            raise ValueError(f"İzinsiz fonksiyon: {node.func.id}")
        args = [_eval_node(a, degiskenler) for a in node.args]
        # round(x, n) → n int olmalı
        if node.func.id == "round" and len(args) == 2:
            args[1] = int(args[1])
        return float(func(*args))

    elif isinstance(node, ast.IfExp):
        # Ternary: x if condition else y
        test = _eval_node(node.test, degiskenler)
        return _eval_node(node.body if test else node.orelse, degiskenler)

    elif isinstance(node, ast.Compare):
        sol = _eval_node(node.left, degiskenler)
        for op, comparator in zip(node.ops, node.comparators):
            sag = _eval_node(comparator, degiskenler)
            if isinstance(op, ast.Gt): result = sol > sag
            elif isinstance(op, ast.Lt): result = sol < sag
            elif isinstance(op, ast.GtE): result = sol >= sag
            elif isinstance(op, ast.LtE): result = sol <= sag
            elif isinstance(op, ast.Eq): result = sol == sag
            else: raise ValueError(f"İzinsiz karşılaştırma")
            if not result: return 0.0
            sol = sag
        return 1.0

    raise ValueError(f"İzinsiz AST node: {type(node).__name__}")


# ═════════════════════════════════════════════
# MALİYET MOTORU SERVİSİ
# ═════════════════════════════════════════════

class MaliyetMotoru:
    """Enterprise maliyet hesaplama motoru."""

    def __init__(self, versiyon_repo: VersiyonRepository):
        self.repo = versiyon_repo

    def alt_kalem_fiyat_hesapla(self, alt_kalem_versiyon_id: str,
                                  parametre_degerleri: dict = None,
                                  konum_ulke: str = "",
                                  konum_sehir: str = "",
                                  miktar: int = 1) -> dict:
        """
        Alt kalem fiyatını hesaplar.
        1. Aktif maliyet şablonunu al
        2. Şablon parametrelerini değişkenlere map'le
        3. Formülü güvenli eval et
        4. Konum fiyatı ekle
        5. Kâr uygula
        Returns: {birim_fiyat, toplam_fiyat, kar, konum_fiyat, formul, detay}
        """
        sablon = self.repo.aktif_maliyet_sablon(alt_kalem_versiyon_id)
        if not sablon:
            return {"birim_fiyat": 0, "toplam_fiyat": 0, "kar": 0,
                    "konum_fiyat": 0, "formul": "0", "detay": "Şablon yok"}

        # Değişkenleri hazırla
        degiskenler = {}
        for mp in self.repo.maliyet_parametreleri(sablon["id"]):
            kod = mp["degisken_kodu"]
            if parametre_degerleri and kod in parametre_degerleri:
                degiskenler[kod] = float(parametre_degerleri[kod])
            else:
                degiskenler[kod] = mp["varsayilan_deger"]

        # Konum fiyatı
        konum_fiyat = 0.0
        if konum_ulke and konum_sehir:
            konum_fiyat = self.repo.konum_fiyat_getir(konum_ulke, konum_sehir)
        degiskenler["KONUM"] = konum_fiyat

        # Formül hesapla
        formul = sablon["formul_ifadesi"]
        ham_fiyat = guvenli_eval(formul, degiskenler)

        # Kâr uygula
        kar_orani = sablon["kar_orani"]
        birim_fiyat = ham_fiyat * (1 + kar_orani / 100) if kar_orani else ham_fiyat
        toplam_fiyat = birim_fiyat * miktar

        return {
            "birim_fiyat": round(birim_fiyat, 2),
            "toplam_fiyat": round(toplam_fiyat, 2),
            "kar_orani": kar_orani,
            "konum_fiyat": konum_fiyat,
            "formul": formul,
            "degiskenler": degiskenler,
            "ham_fiyat": round(ham_fiyat, 2),
        }

    def proje_snapshot_olustur(self, proje_id: str, belge_id: str,
                                 revizyon_no: int,
                                 urun_id: str, urun_versiyon_id: str,
                                 alt_kalem_id: str, alt_kalem_versiyon_id: str,
                                 parametre_degerleri: dict,
                                 konum_ulke: str, konum_sehir: str,
                                 miktar: int = 1,
                                 opsiyon_mu: bool = False) -> str:
        """
        Hesapla + snapshot kaydet.
        Returns: snapshot_id
        """
        hesap = self.alt_kalem_fiyat_hesapla(
            alt_kalem_versiyon_id, parametre_degerleri,
            konum_ulke, konum_sehir, miktar)

        from datetime import datetime
        snap = {
            "proje_id": proje_id,
            "belge_id": belge_id,
            "revizyon_no": revizyon_no,
            "urun_id": urun_id,
            "urun_versiyon_id": urun_versiyon_id,
            "alt_kalem_id": alt_kalem_id,
            "alt_kalem_versiyon_id": alt_kalem_versiyon_id,
            "parametre_degerleri": parametre_degerleri,
            "formul_ifadesi": hesap["formul"],
            "birim_fiyat": hesap["birim_fiyat"],
            "miktar": miktar,
            "toplam_fiyat": hesap["toplam_fiyat"],
            "kar_orani": hesap["kar_orani"],
            "konum_fiyat": hesap["konum_fiyat"],
            "opsiyon_mu": opsiyon_mu,
            "olusturma_yili": datetime.now().year,
        }
        snap_id = self.repo.snapshot_kaydet(snap)
        logger.info(f"Snapshot: proje={proje_id[:8]}, rev={revizyon_no}, "
                    f"fiyat={hesap['toplam_fiyat']}")
        return snap_id

    def revizyon_toplam(self, proje_id: str, revizyon_no: int) -> dict:
        """Revizyon bazlı toplam hesapla (opsiyonlar hariç)."""
        snaps = self.repo.proje_snapshotlari(proje_id, revizyon_no)
        toplam = 0.0
        opsiyon_toplam = 0.0
        kalemler = []
        for s in snaps:
            if s["opsiyon_mu"]:
                opsiyon_toplam += s["toplam_fiyat"]
            else:
                toplam += s["toplam_fiyat"]
            kalemler.append(s)
        return {
            "toplam": round(toplam, 2),
            "opsiyon_toplam": round(opsiyon_toplam, 2),
            "genel_toplam": round(toplam + opsiyon_toplam, 2),
            "kalem_sayisi": len(kalemler),
        }
