#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teklif/Keşif Yönetim Sayfası.
Seviye 1 — Liste: arama + durum filtre + teklif/keşif listesi
Seviye 2 — Detay: kalem tablosu + parametre girişi + fiyat hesaplama
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, QLineEdit,
    QStackedWidget, QScrollArea, QMessageBox, QSplitter,
    QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from uygulama.ortak.yardimcilar import logger_olustur

logger = logger_olustur("teklif_sayfa")


def _setup_tbl(t, rh=28):
    t.verticalHeader().setDefaultSectionSize(rh)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setAlternatingRowColors(True)
    t.setStyleSheet(
        "QTableWidget { gridline-color:#E0E0E0; border:1px solid #ddd; }"
        "QTableWidget::item { padding:0px 2px; }"
        "QTableWidget::item:selected { background:#BBDEFB; color:#000; }"
        "QComboBox { font-size:10px; padding:0px 2px; }"
        "QSpinBox { font-size:10px; padding:0px; }")


# ═══════════════════════════════════════
# ANA KONTEYNER
# ═══════════════════════════════════════

class TeklifSayfasi(QWidget):
    go_back = pyqtSignal()

    def __init__(self, teklif_srv=None, em_repo=None, belge_srv=None, parent=None):
        super().__init__(parent)
        self.srv = teklif_srv
        self.em_repo = em_repo
        self.belge_srv = belge_srv
        self._pid = None
        lo = QVBoxLayout(self); lo.setContentsMargins(0,0,0,0)
        self.stack = QStackedWidget()
        self.liste = _ListeW(self.srv)
        self.detay = _DetayW(self.srv, self.em_repo, belge_srv=self.belge_srv)
        self.stack.addWidget(self.liste)
        self.stack.addWidget(self.detay)
        lo.addWidget(self.stack)
        self.liste.teklif_ac.connect(self._ac)
        self.detay.geri.connect(self._don)

    def yukle(self, pid):
        self._pid = pid
        self.liste.yukle(pid)
        self.stack.setCurrentIndex(0)

    def _ac(self, tid):
        self.detay.yukle(tid)
        self.stack.setCurrentIndex(1)

    def _don(self):
        if self._pid:
            self.liste.yukle(self._pid)
        self.stack.setCurrentIndex(0)


# ═══════════════════════════════════════
# SEVİYE 1 — LİSTE
# ═══════════════════════════════════════

class _ListeW(QWidget):
    teklif_ac = pyqtSignal(str)

    def __init__(self, srv=None, parent=None):
        super().__init__(parent)
        self.srv = srv
        self._pid = None
        self._data = []
        self._build()

    def _build(self):
        lo = QVBoxLayout(self); lo.setContentsMargins(16,10,16,10); lo.setSpacing(8)

        # ── Başlık + oluşturma ──
        r1 = QHBoxLayout()
        lbl = QLabel("Teklifler / Keşifler")
        lbl.setStyleSheet("font-size:14px; font-weight:bold;")
        r1.addWidget(lbl); r1.addStretch()
        r1.addWidget(QLabel("Para:"))
        self.para_cmb = QComboBox(); self.para_cmb.setFixedSize(150,28)
        from uygulama.altyapi.teklif_repo import PARA_BIRIMLERI
        for kod,sembol,ad in PARA_BIRIMLERI:
            self.para_cmb.addItem(f"{sembol} {ad}", kod)
        r1.addWidget(self.para_cmb); r1.addSpacing(8)
        for txt,tur,obj in [("+ Yeni Teklif","TEKLİF","primary"),("+ Yeni Keşif","KEŞİF",None)]:
            b = QPushButton(txt); b.setFixedHeight(28)
            if obj: b.setObjectName(obj)
            b.clicked.connect(lambda _,t=tur: self._olustur(t))
            r1.addWidget(b)
        lo.addLayout(r1)

        # ── Arama + Filtre ──
        r2 = QHBoxLayout()
        self.arama = QLineEdit(); self.arama.setPlaceholderText("Ara...")
        self.arama.setFixedHeight(28); self.arama.textChanged.connect(self._filtrele)
        r2.addWidget(self.arama)
        r2.addWidget(QLabel("Durum:"))
        self.durum_cmb = QComboBox(); self.durum_cmb.setFixedSize(130,28)
        self.durum_cmb.addItem("Tümü", "")
        for d in ["TASLAK","GONDERILDI","ONAYLANDI","REDDEDILDI","KAPANDI"]:
            self.durum_cmb.addItem(d, d)
        self.durum_cmb.currentIndexChanged.connect(self._filtrele)
        r2.addWidget(self.durum_cmb)
        lo.addLayout(r2)

        # ── Tablo ──
        self.tbl = QTableWidget(); _setup_tbl(self.tbl, 32)
        self.tbl.setColumnCount(6)
        self.tbl.setHorizontalHeaderLabels(["Tür","Başlık","Rev.","Para","Toplam","Durum"])
        self.tbl.setColumnWidth(0,60)
        self.tbl.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        self.tbl.setColumnWidth(2,40); self.tbl.setColumnWidth(3,45)
        self.tbl.setColumnWidth(4,110); self.tbl.setColumnWidth(5,90)
        self.tbl.doubleClicked.connect(self._dbl)
        lo.addWidget(self.tbl)

        # ── Alt butonlar ──
        r3 = QHBoxLayout()
        for txt,slot,obj in [
            ("Aç",self._secili_ac,None),
            ("Revizyon",self._revizyon,None),
            ("Durum Değiştir",self._durum_degistir,None),
            ("Sil",self._sil,"danger"),
        ]:
            b = QPushButton(txt); b.setFixedHeight(26)
            if obj: b.setObjectName(obj)
            b.clicked.connect(slot); r3.addWidget(b)
        r3.addStretch()
        lo.addLayout(r3)

    def yukle(self, pid):
        self._pid = pid; self._filtrele()

    def _filtrele(self):
        if not self._pid or not self.srv: return
        arama = self.arama.text().strip()
        durum = self.durum_cmb.currentData() or ""
        self._data = self.srv.proje_teklifleri_filtreli(self._pid, arama, durum)
        self._tabloyu_doldur()

    def _tabloyu_doldur(self):
        renk = {"TASLAK":"#757575","GONDERILDI":"#1565C0",
                "ONAYLANDI":"#2E7D32","REDDEDILDI":"#C62828","KAPANDI":"#795548"}
        self.tbl.setRowCount(len(self._data))
        for i,t in enumerate(self._data):
            s = self.srv.para_birimi_sembol(t["para_birimi"])
            self.tbl.setItem(i,0,QTableWidgetItem(t["tur"]))
            self.tbl.setItem(i,1,QTableWidgetItem(t["baslik"]))
            self.tbl.setItem(i,2,QTableWidgetItem(str(t["revizyon_no"])))
            self.tbl.setItem(i,3,QTableWidgetItem(s))
            it = QTableWidgetItem(f"{s}{t['toplam_fiyat']:,.2f}")
            it.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
            self.tbl.setItem(i,4,it)
            d = QTableWidgetItem(t["durum"])
            d.setForeground(QColor(renk.get(t["durum"],"#333")))
            self.tbl.setItem(i,5,d)

    def _sel(self):
        r = self.tbl.currentRow()
        return self._data[r] if 0<=r<len(self._data) else None

    def _dbl(self):
        t=self._sel()
        if t: self.teklif_ac.emit(t["id"])

    def _secili_ac(self):
        t=self._sel()
        if t: self.teklif_ac.emit(t["id"])

    def _olustur(self, tur):
        if not self._pid or not self.srv: return
        para = self.para_cmb.currentData() or "TRY"
        ok,msg,tid = self.srv.teklif_olustur(self._pid, tur, para)
        if ok: self._filtrele(); self.teklif_ac.emit(tid)
        else: QMessageBox.warning(self,"Hata",msg)

    def _revizyon(self):
        t=self._sel()
        if not t: return
        ok,msg,tid = self.srv.revizyon_olustur(t["id"])
        if ok: self._filtrele(); self.teklif_ac.emit(tid)
        else: QMessageBox.warning(self,"Hata",msg)

    def _durum_degistir(self):
        t=self._sel()
        if not t: return
        durumlar = ["TASLAK","GONDERILDI","ONAYLANDI","REDDEDILDI","KAPANDI"]
        cmb = QComboBox()
        for d in durumlar: cmb.addItem(d)
        idx = durumlar.index(t["durum"]) if t["durum"] in durumlar else 0
        cmb.setCurrentIndex(idx)
        from PyQt5.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        dlg = QDialog(self); dlg.setWindowTitle("Durum Değiştir")
        fl = QFormLayout(dlg); fl.addRow("Yeni durum:", cmb)
        bb = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        fl.addRow(bb)
        if dlg.exec_():
            self.srv.durum_degistir(t["id"], cmb.currentText())
            self._filtrele()

    def _sil(self):
        t=self._sel()
        if not t: return
        if QMessageBox.question(self,"Sil",f"'{t['baslik']}' silinsin mi?",
                QMessageBox.Yes|QMessageBox.No)==QMessageBox.Yes:
            self.srv.sil(t["id"]); self._filtrele()


# ═══════════════════════════════════════
# SEVİYE 2 — DETAY
# ═══════════════════════════════════════

class _DetayW(QWidget):
    geri = pyqtSignal()

    def __init__(self, srv=None, em_repo=None, belge_srv=None, parent=None):
        super().__init__(parent)
        self.srv = srv; self.em_repo = em_repo; self.belge_srv = belge_srv
        self._tid = None; self._teklif = None; self._kalemler = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,8,16,8); root.setSpacing(0)

        # ── HEADER ──
        hdr = QHBoxLayout(); hdr.setSpacing(8)
        bg = QPushButton("← Geri"); bg.setFixedSize(90,28); bg.clicked.connect(self.geri.emit)
        hdr.addWidget(bg)
        self.lbl_baslik = QLabel(); self.lbl_baslik.setStyleSheet("font-size:14px;font-weight:bold;")
        hdr.addWidget(self.lbl_baslik)
        self.lbl_durum = QLabel(); self.lbl_durum.setStyleSheet(
            "font-size:11px;padding:2px 8px;border-radius:3px;background:#E3F2FD;color:#1565C0;")
        hdr.addWidget(self.lbl_durum)
        hdr.addStretch()

        # KDV oranı girişi
        hdr.addWidget(QLabel("KDV:"))
        self.kdv_spin = QDoubleSpinBox()
        self.kdv_spin.setRange(0, 100); self.kdv_spin.setDecimals(1)
        self.kdv_spin.setValue(20); self.kdv_spin.setSuffix(" %")
        self.kdv_spin.setFixedSize(70, 24)
        self.kdv_spin.valueChanged.connect(self._kdv_degisti)
        hdr.addWidget(self.kdv_spin)
        hdr.addSpacing(8)

        # Toplam paneli: Ara toplam / KDV / Genel toplam
        tp = QVBoxLayout(); tp.setSpacing(1)
        self.lbl_ara = QLabel("Ara Toplam: —")
        self.lbl_ara.setStyleSheet("font-size:11px;color:#555;")
        self.lbl_ara.setAlignment(Qt.AlignRight)
        self.lbl_kdv = QLabel("KDV: —")
        self.lbl_kdv.setStyleSheet("font-size:11px;color:#555;")
        self.lbl_kdv.setAlignment(Qt.AlignRight)
        self.lbl_toplam = QLabel("Genel Toplam: —")
        self.lbl_toplam.setStyleSheet(
            "font-size:13px;font-weight:bold;color:#2E7D32;")
        self.lbl_toplam.setAlignment(Qt.AlignRight)
        tp.addWidget(self.lbl_ara)
        tp.addWidget(self.lbl_kdv)
        tp.addWidget(self.lbl_toplam)
        hdr.addLayout(tp)
        root.addLayout(hdr); root.addSpacing(6)

        sp = QSplitter(Qt.Vertical); sp.setHandleWidth(5)

        # ─ ÜST: Kalem tablosu ─
        ust = QWidget(); ul = QVBoxLayout(ust); ul.setContentsMargins(0,0,0,0); ul.setSpacing(4)
        ub = QHBoxLayout()
        ub.addWidget(QLabel("Ürün ve Alt Kalemler"))
        ub.addStretch()
        b_belge = QPushButton("📄 Belge Oluştur")
        b_belge.setFixedSize(120, 28)
        b_belge.clicked.connect(self._belge_olustur)
        ub.addWidget(b_belge)
        b_bac = QPushButton("📂 Belgeyi Aç")
        b_bac.setFixedSize(100, 28)
        b_bac.clicked.connect(self._belge_ac)
        ub.addWidget(b_bac)
        bh = QPushButton("Fiyatları Hesapla"); bh.setObjectName("primary")
        bh.setFixedSize(130,28); bh.clicked.connect(self._hesapla)
        ub.addWidget(bh)
        ul.addLayout(ub)

        self.ktbl = QTableWidget(); _setup_tbl(self.ktbl, 28)
        self.ktbl.setColumnCount(6)
        self.ktbl.setHorizontalHeaderLabels(
            ["No","Ürün / Alt Kalem","Durum","Adet","Birim Fiyat","Toplam Fiyat"])
        self.ktbl.setColumnWidth(0,30)
        self.ktbl.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        self.ktbl.setColumnWidth(2,70)
        self.ktbl.setColumnWidth(3,46)
        self.ktbl.setColumnWidth(4,90); self.ktbl.setColumnWidth(5,90)
        self.ktbl.clicked.connect(self._kalem_tikla)
        ul.addWidget(self.ktbl)
        sp.addWidget(ust)

        # ─ ALT: Parametreler ─
        alt = QWidget(); al = QVBoxLayout(alt); al.setContentsMargins(0,2,0,0); al.setSpacing(4)
        self.lbl_p = QLabel("Bir kalem seçerek parametrelerini görüntüleyin")
        self.lbl_p.setStyleSheet("font-weight:bold;color:#444;padding:2px 0;")
        al.addWidget(self.lbl_p)
        sc = QScrollArea(); sc.setWidgetResizable(True)
        sc.setStyleSheet("QScrollArea{border:1px solid #ddd;border-radius:3px;background:#FAFAFA;}")
        sc.setMinimumHeight(70)
        self.pw = QWidget()
        self.pg = QGridLayout(self.pw)
        self.pg.setContentsMargins(10,8,10,8)
        self.pg.setHorizontalSpacing(10); self.pg.setVerticalSpacing(8)
        self.pg.setColumnMinimumWidth(0,110); self.pg.setColumnMinimumWidth(2,110)
        self.pg.setColumnStretch(1,1); self.pg.setColumnStretch(3,1)
        sc.setWidget(self.pw)
        al.addWidget(sc)
        sp.addWidget(alt)
        sp.setSizes([300,180]); sp.setStretchFactor(0,3); sp.setStretchFactor(1,2)
        root.addWidget(sp)

    # ── Veri ──

    def yukle(self, tid):
        self._tid = tid
        self._teklif = self.srv.getir(tid) if self.srv else None
        if not self._teklif: return
        self.lbl_baslik.setText(self._teklif["baslik"])
        self.lbl_durum.setText(self._teklif["durum"])
        self._toplam_goster(); self._kalem_yukle(); self._param_temizle()

    def _toplam_goster(self):
        if not self._teklif: return
        s = self.srv.para_birimi_sembol(self._teklif["para_birimi"])
        ara = self._teklif.get("toplam_fiyat", 0)
        kdv_o = self._teklif.get("kdv_orani", 20)
        kdv_t = self._teklif.get("kdv_tutari", 0)
        gtop = self._teklif.get("kdv_dahil_toplam", 0)
        self.lbl_ara.setText(f"Ara Toplam: {s}{ara:,.2f}")
        self.lbl_kdv.setText(f"KDV (%{kdv_o:g}): {s}{kdv_t:,.2f}")
        self.lbl_toplam.setText(f"Genel Toplam: {s}{gtop:,.2f}")
        self.kdv_spin.blockSignals(True)
        self.kdv_spin.setValue(kdv_o)
        self.kdv_spin.blockSignals(False)

    def _kalem_yukle(self):
        if not self.srv: return
        self._kalemler = self.srv.zenginlestirilmis_kalemler(self._tid)
        s = self.srv.para_birimi_sembol(self._teklif["para_birimi"]) if self._teklif else "₺"

        # Alt kalem numaralama: DAHIL → 1,2,3 / OPSIYON → ## / HARIC → —
        ak_no = 1
        ak_nums = {}
        for k in self._kalemler:
            if k["tip"] != "urun" and k.get("alt_kalem_id"):
                durum = k.get("dahil_durumu", "DAHIL")
                if durum == "DAHIL":
                    ak_nums[k["id"]] = str(ak_no); ak_no += 1
                elif durum == "OPSIYON":
                    ak_nums[k["id"]] = "##"
                else:
                    ak_nums[k["id"]] = "—"

        self.ktbl.setRowCount(len(self._kalemler))
        for i, k in enumerate(self._kalemler):
            is_u = k["tip"] == "urun"
            durum = k.get("dahil_durumu", "DAHIL")

            # Kolon 0: No
            no_txt = ak_nums.get(k["id"], "") if not is_u else ""
            no_it = QTableWidgetItem(no_txt)
            no_it.setTextAlignment(Qt.AlignCenter)
            if no_txt == "##":
                no_it.setForeground(QColor("#FF8F00"))
            self.ktbl.setItem(i, 0, no_it)

            # Kolon 1: İsim
            if is_u:
                it = QTableWidgetItem(f"  {k['urun_kod']} — {k['urun_ad']}")
                f = it.font(); f.setBold(True); it.setFont(f)
                it.setBackground(QColor(235, 242, 250))
            else:
                it = QTableWidgetItem(f"      {k['alt_kalem_ad']}")
                if durum == "HARIC":
                    it.setForeground(QColor("#BDBDBD"))
                elif durum == "OPSIYON":
                    it.setForeground(QColor("#FF8F00"))
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.ktbl.setItem(i, 1, it)

            # Kolon 2: Durum ComboBox (alt kalem) veya boş (ürün)
            if not is_u:
                dcmb = QComboBox()
                dcmb.setFixedHeight(22)
                dcmb.setMaximumWidth(66)
                dcmb.setStyleSheet("QComboBox{font-size:9px;padding:0px 1px;}")
                for d in ["DAHIL", "OPSIYON", "HARIC"]:
                    dcmb.addItem(d)
                idx = ["DAHIL", "OPSIYON", "HARIC"].index(durum) if durum in ["DAHIL", "OPSIYON", "HARIC"] else 0
                dcmb.setCurrentIndex(idx)
                dcmb.currentTextChanged.connect(
                    lambda d, kid=k["id"]: self._durum_degis(kid, d))
                self.ktbl.setCellWidget(i, 2, dcmb)
            else:
                self.ktbl.setItem(i, 2, QTableWidgetItem(""))

            # Kolon 3: Adet
            if not is_u and durum != "HARIC":
                sp = QSpinBox(); sp.setRange(1, 9999); sp.setValue(k["miktar"])
                sp.setFixedHeight(22); sp.setMaximumWidth(42)
                sp.setAlignment(Qt.AlignCenter)
                sp.setButtonSymbols(QSpinBox.NoButtons)
                sp.setStyleSheet("QSpinBox{font-size:10px;padding:0px;}")
                sp.valueChanged.connect(lambda v, kid=k["id"]: self._miktar(kid, v))
                self.ktbl.setCellWidget(i, 3, sp)
            else:
                self.ktbl.setItem(i, 3, QTableWidgetItem(""))

            # Kolon 4-5: Fiyatlar
            if not is_u and durum != "HARIC" and k["birim_fiyat"]:
                for c, v in [(4, k["birim_fiyat"]), (5, k["toplam_fiyat"])]:
                    fi = QTableWidgetItem(f"{s}{v:,.2f}")
                    fi.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if durum == "OPSIYON":
                        fi.setForeground(QColor("#FF8F00"))
                    self.ktbl.setItem(i, c, fi)
            else:
                for c in (4, 5):
                    ei = QTableWidgetItem("—" if not is_u else "")
                    ei.setTextAlignment(Qt.AlignCenter)
                    if not is_u: ei.setForeground(QColor("#BDBDBD"))
                    self.ktbl.setItem(i, c, ei)

    # ── Parametreler ──

    def _kalem_tikla(self):
        r=self.ktbl.currentRow()
        if 0<=r<len(self._kalemler): self._param_goster(self._kalemler[r])

    def _param_goster(self, kalem):
        self._param_temizle()
        if kalem["tip"]=="urun":
            self.lbl_p.setText(f"Parametreler — {kalem['urun_kod']}  {kalem['urun_ad']}")
        else:
            self.lbl_p.setText(f"Parametreler — {kalem['alt_kalem_ad']}")
        if not self.srv: return
        vals = self.srv.parametre_degerleri(kalem["id"])
        # Özel parametreleri filtrele (__ ile başlayanlar gizle)
        vals = [v for v in vals if not v["parametre_adi"].startswith("__")]
        if not vals:
            l=QLabel("Bu kalemde parametre tanımlı değil.")
            l.setStyleSheet("color:#999;font-style:italic;padding:8px;")
            self.pg.addWidget(l,0,0,1,4); return

        # Para birimi override
        para_sembol = "₺"
        if self._teklif:
            para_sembol = self.srv.para_birimi_sembol(self._teklif["para_birimi"])

        row,col = 0,0
        for d in vals:
            info = self._pinfo(d["parametre_id"])
            tip = info.get("tip_kodu","string") if info else "string"
            birim = info.get("birim","") if info else ""

            lbl = QLabel(f"{d['parametre_adi']}:")
            lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
            lbl.setStyleSheet("color:#333; padding-right:4px;")
            w = self._mkw(kalem["id"],d["parametre_id"],d["parametre_adi"],
                          d["deger"],tip,info,birim,para_sembol)
            w.setFixedHeight(26)
            self.pg.addWidget(lbl, row, col*2)
            self.pg.addWidget(w, row, col*2+1)
            col += 1
            if col >= 2: col=0; row+=1

    def _pinfo(self, pid):
        if not self.em_repo: return None
        for tbl,alias in [("urun_parametreler","up"),("alt_kalem_parametreler","akp")]:
            r = self.em_repo.db.getir_tek(
                f"SELECT {alias}.*, pt.kod as tip_kodu, pt.gorunen_ad "
                f"FROM {tbl} {alias} LEFT JOIN parametre_tipler pt ON {alias}.tip_id=pt.id "
                f"WHERE {alias}.id=?", (pid,))
            if r: return dict(r)
        return None

    def _mkw(self, kid, pid, padi, val, tip, info, birim, para_sembol):
        def save(v): 
            if self.srv: self.srv.parametre_kaydet(kid,pid,padi,str(v))

        if tip=="int":
            w=QSpinBox(); w.setRange(0,999999)
            try: w.setValue(int(float(val)))
            except: pass
            if birim: w.setSuffix(f" {birim}")
            w.valueChanged.connect(save); return w

        if tip in ("float","para","olcu_birimi","yuzde"):
            w=QDoubleSpinBox(); w.setDecimals(2); w.setRange(0,99999999)
            try: w.setValue(float(val))
            except: pass
            if tip=="para":
                w.setPrefix(f"{para_sembol} ")  # Teklif para birimi override!
            elif tip=="yuzde":
                w.setSuffix(" %"); w.setRange(0,100)
            elif tip=="olcu_birimi":
                if birim:
                    w.setSuffix(f" {birim}")
                else:
                    w.setSuffix(" m²")
            elif birim:
                w.setSuffix(f" {birim}")
            w.valueChanged.connect(save); return w

        if tip=="boolean":
            w=QCheckBox("Evet")
            w.setChecked(str(val).lower() in ("1","true","evet"))
            w.stateChanged.connect(lambda s:save("1" if s else "0")); return w

        if tip=="dropdown":
            w=QComboBox()
            if self.em_repo:
                for dd in self.em_repo.dropdown_degerleri(pid): w.addItem(dd["deger"])
            if val:
                ix=w.findText(str(val))
                if ix>=0: w.setCurrentIndex(ix)
            w.currentTextChanged.connect(save); return w

        w=QLineEdit(str(val) if val else "")
        w.setPlaceholderText("Değer girin")
        w.editingFinished.connect(lambda:save(w.text())); return w

    # ── Eylemler ──

    def _secim(self, kid, st):
        if self.srv: self.srv.kalem_secim_degistir(kid, st==2)

    def _durum_degis(self, kid, durum):
        if self.srv:
            self.srv.kalem_dahil_durumu_degistir(kid, durum)
            self._kalem_yukle()

    def _kdv_degisti(self, val):
        if self.srv and self._tid:
            self.srv.kdv_orani_degistir(self._tid, val)
            self._teklif = self.srv.getir(self._tid)
            self._toplam_goster()

    def _miktar(self, kid, v):
        if self.srv: self.srv.kalem_miktar_degistir(kid, v)

    def _hesapla(self):
        if not self._tid or not self.srv: return
        kf = 0
        if self._teklif and self.srv.em_srv and self.srv.proje_srv:
            p = self.srv.proje_srv.getir(self._teklif["proje_id"])
            if p: kf = self.srv.em_srv.konum_fiyat(
                getattr(p,'ulke','') or '', getattr(p,'konum','') or '')
        ok, msg, sonuc = self.srv.teklif_hesapla(self._tid, kf)
        self._teklif = self.srv.getir(self._tid)
        self._toplam_goster(); self._kalem_yukle()
        if not ok: QMessageBox.warning(self, "Hesaplama", msg)

    def _param_temizle(self):
        while self.pg.count():
            it=self.pg.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        self.lbl_p.setText("Bir kalem seçerek parametrelerini görüntüleyin")

    # ── Belge İşlemleri ──

    def _belge_olustur(self):
        if not self._tid or not self.belge_srv:
            QMessageBox.information(self, "Bilgi", "Belge servisi yapılandırılmamış.")
            return
        # Belge türü seçimi
        turleri = self.belge_srv.repo.belge_turleri()
        if not turleri:
            QMessageBox.warning(self, "Hata", "Belge türü tanımlı değil.\nAdmin → Belge Şablonları'ndan tanımlayın.")
            return
        from PyQt5.QtWidgets import QInputDialog
        secenekler = [f"{t['kod']} — {t['ad']}" for t in turleri]
        secim, ok = QInputDialog.getItem(self, "Belge Türü", "Oluşturulacak belge türünü seçin:", secenekler, 0, False)
        if not ok:
            return
        idx = secenekler.index(secim)
        tur_kodu = turleri[idx]["kod"]

        # Hedef klasör seç
        from PyQt5.QtWidgets import QFileDialog
        hedef = QFileDialog.getExistingDirectory(self, "Kayıt Klasörü Seçin")
        if not hedef:
            return

        ok, msg, dosya_yolu = self.belge_srv.belge_olustur(self._tid, tur_kodu, hedef)
        if ok:
            QMessageBox.information(self, "Başarılı", msg)
            # Dosyayı aç
            import os, subprocess, sys
            if sys.platform == 'win32':
                os.startfile(dosya_yolu)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', dosya_yolu])
            else:
                subprocess.Popen(['xdg-open', dosya_yolu])
        else:
            QMessageBox.warning(self, "Hata", msg)

    def _belge_ac(self):
        if not self._tid or not self.belge_srv:
            return
        kayitlar = self.belge_srv.repo.uretim_kayitlari(self._tid)
        if not kayitlar:
            QMessageBox.information(self, "Bilgi", "Bu teklif için henüz belge oluşturulmamış.")
            return
        import os
        if len(kayitlar) == 1:
            yol = kayitlar[0]["dosya_yolu"]
        else:
            from PyQt5.QtWidgets import QInputDialog
            secenekler = [f"{k['dosya_adi']}  ({k['olusturma_tarihi'][:16]})" for k in kayitlar]
            secim, ok = QInputDialog.getItem(self, "Belge Seç", "Açılacak belgeyi seçin:", secenekler, 0, False)
            if not ok:
                return
            idx = secenekler.index(secim)
            yol = kayitlar[idx]["dosya_yolu"]

        if not os.path.exists(yol):
            QMessageBox.warning(self, "Hata", f"Dosya bulunamadı:\n{yol}")
            return
        import subprocess, sys
        if sys.platform == 'win32':
            os.startfile(yol)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', yol])
        else:
            subprocess.Popen(['xdg-open', yol])
