"""
E2Eテスト: 実データ（workspace/data/）を使った互換性診断
=========================================================
PIMRAGEngine のモックには依存せず、products.jsonl を直接読み込んで
7項目の互換性チェックロジックを実行・検証する。

テストケース1（正常構成）:
  CPU:    Ryzen 9 9950X (AM5, DDR5, TDP=230W max_turbo)
  MB:     ASRock X870E Taichi OCF (AM5, DDR5, ATX)
  RAM:    Corsair Vengeance DDR5-6000 32GB (DDR5, h=44mm)
  GPU:    ASUS TUF RTX4090 OC (length=348mm, TDP=450W)
  Case:   NZXT H510 (max_gpu=381mm, max_cooler=165mm, ATX)
  Cooler: Noctua NH-D15 original (height=165mm, side_clearance=62mm)
  PSU:    be quiet! DARK POWER 14 1000W (wattage=1000W)
  期待: WARNING (クーラー高 margin=0mm → WARNING, その他✅)

テストケース2（NGあり構成）:
  CPU:    Intel Core Ultra 9 285K (LGA1851, DDR5, TDP=250W max_turbo)
  MB:     ASRock X870E Taichi OCF (AM5=ソケット不一致, ATX)
  RAM:    Corsair Vengeance DDR5-6000 32GB (DDR5)
  GPU:    ASUS TUF RTX4090 OC (length=348mm, TDP=450W)
  Case:   NZXT H200i (max_gpu=328mm=GPU長超過, Mini-ITX=フォームファクタ不一致)
  Cooler: Noctua NH-D15 original (height=165mm)
  PSU:    be quiet! PURE POWER 12M 650W (650W < 840W推奨=電源不足)
  期待: NG (ソケット❌/GPU長❌/電源❌/フォームファクタ❌)
"""

from __future__ import annotations

import json
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------------ #
# データストア
# ------------------------------------------------------------------ #
DATA_DIR = Path(__file__).parent.parent / "workspace" / "data"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _find(category_dir: str, **kw_specs) -> Optional[dict]:
    """
    workspace/data/<category_dir>/products.jsonl から
    specs フィールドのキーワードで部分マッチ検索する。
    すべての kw_specs が specs に含まれるレコードを返す。
    """
    for rec in _load_jsonl(DATA_DIR / category_dir / "products.jsonl"):
        specs = rec.get("specs", {})
        if all(
            str(specs.get(k, "")).lower() == str(v).lower()
            for k, v in kw_specs.items()
        ):
            return rec
    return None


def _find_by_name(category_dir: str, name_fragment: str) -> Optional[dict]:
    """name フィールドで部分一致検索"""
    for rec in _load_jsonl(DATA_DIR / category_dir / "products.jsonl"):
        if name_fragment.lower() in rec.get("name", "").lower():
            return rec
    return None


# ------------------------------------------------------------------ #
# 判定結果データクラス
# ------------------------------------------------------------------ #
@dataclass
class CheckResult:
    check_name: str
    verdict: str          # "OK" / "WARNING" / "NG"
    reason: str
    actual: str = ""
    expected: str = ""
    margin: Optional[float] = None


@dataclass
class BuildCompatReport:
    case_name: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def overall_verdict(self) -> str:
        verdicts = [c.verdict for c in self.checks]
        if "NG" in verdicts:
            return "NG"
        if "WARNING" in verdicts:
            return "WARNING"
        return "OK"

    def summary(self) -> str:
        lines = [f"\n{'='*60}", f"ケース: {self.case_name}", f"総合判定: {self.overall_verdict}", ""]
        icon = {"OK": "✅", "WARNING": "⚠️", "NG": "❌"}
        for c in self.checks:
            lines.append(f"  {icon[c.verdict]} {c.check_name}: {c.verdict}")
            lines.append(f"     理由: {c.reason}")
            if c.actual or c.expected:
                lines.append(f"     実際: {c.actual}  /  期待: {c.expected}")
            if c.margin is not None:
                lines.append(f"     マージン: {c.margin}mm")
        lines.append("=" * 60)
        return "\n".join(lines)


# ------------------------------------------------------------------ #
# 互換性チェッカー
# ------------------------------------------------------------------ #
class CompatibilityChecker:
    """
    products.jsonl の実データを使って7項目の互換性を判定する。
    PIMRAGEngine には依存しない。
    """

    # ---------- チェック1: CPUソケット ↔ MB ----------
    def check_1_socket(self, cpu: dict, mb: dict) -> CheckResult:
        cpu_socket = cpu["specs"].get("socket", "")
        mb_socket  = mb["specs"].get("socket", "")
        if cpu_socket == mb_socket:
            return CheckResult(
                "ソケット一致(CPU↔MB)", "OK",
                f"{cpu['name']} と {mb['name']} のソケットが一致",
                actual=cpu_socket, expected=mb_socket,
            )
        return CheckResult(
            "ソケット一致(CPU↔MB)", "NG",
            f"ソケット不一致: CPU={cpu_socket}, MB={mb_socket}",
            actual=cpu_socket, expected=mb_socket,
        )

    # ---------- チェック2: RAM DDR世代 ↔ MB ----------
    def check_2_ddr(self, ram: dict, mb: dict) -> CheckResult:
        ram_type = ram["specs"].get("memory_type", "")
        mb_type  = mb["specs"].get("memory_type", "")
        # MB の memory_type はリストの場合もある
        if isinstance(mb_type, list):
            match = ram_type in mb_type
            mb_type_str = "/".join(mb_type)
        else:
            match = ram_type.upper() == mb_type.upper()
            mb_type_str = mb_type

        if match:
            return CheckResult(
                "DDR世代一致(RAM↔MB)", "OK",
                f"DDR世代一致: RAM={ram_type}, MB対応={mb_type_str}",
                actual=ram_type, expected=mb_type_str,
            )
        return CheckResult(
            "DDR世代一致(RAM↔MB)", "NG",
            f"DDR世代不一致: RAM={ram_type}, MB対応={mb_type_str}",
            actual=ram_type, expected=mb_type_str,
        )

    # ---------- チェック3: GPU長 ≤ ケース最大GPU長 ----------
    def check_3_gpu_length(self, gpu: dict, case: dict) -> CheckResult:
        gpu_len  = gpu["specs"].get("length_mm", 0)
        max_len  = case["specs"].get("max_gpu_length_mm", 9999)
        margin   = max_len - gpu_len
        if margin >= 15:
            verdict = "OK"
            reason = f"GPU長 {gpu_len}mm ≤ ケース最大 {max_len}mm (マージン {margin}mm)"
        elif margin >= 5:
            verdict = "WARNING"
            reason = f"GPU長がケース最大に近い (マージン {margin}mm < 15mm)"
        elif margin >= 0:
            verdict = "NG"
            reason = f"GPU長がケース最大に非常に近い (マージン {margin}mm < 5mm)"
        else:
            verdict = "NG"
            reason = f"GPU長超過: {gpu_len}mm > ケース最大 {max_len}mm (超過 {-margin}mm)"
        return CheckResult(
            "GPU長/ケースクリアランス", verdict, reason,
            actual=f"{gpu_len}mm", expected=f"≤{max_len}mm", margin=float(margin),
        )

    # ---------- チェック4: クーラー高 ≤ ケース最大クーラー高 ----------
    def check_4_cooler_height(self, cooler: dict, case: dict) -> CheckResult:
        cooler_h = cooler["specs"].get("height_mm", 0)
        max_h    = case["specs"].get("max_cpu_cooler_height_mm", 9999)
        margin   = max_h - cooler_h
        if margin > 5:
            verdict = "OK"
            reason = f"クーラー高 {cooler_h}mm ≤ ケース最大 {max_h}mm (マージン {margin}mm)"
        elif margin >= 0:
            verdict = "WARNING"
            reason = f"クーラー高がケース最大ギリギリ (マージン {margin}mm ≤ 5mm)"
        else:
            verdict = "NG"
            reason = f"クーラー高超過: {cooler_h}mm > ケース最大 {max_h}mm (超過 {-margin}mm)"
        return CheckResult(
            "クーラー高/ケースクリアランス", verdict, reason,
            actual=f"{cooler_h}mm", expected=f"≤{max_h}mm", margin=float(margin),
        )

    # ---------- チェック5: RAM高さ ≤ クーラー側面クリアランス ----------
    def check_5_ram_clearance(self, ram: dict, cooler: dict) -> CheckResult:
        ram_h      = ram["specs"].get("height_mm")
        clearance  = cooler["specs"].get("side_clearance_mm")
        if ram_h is None:
            return CheckResult("RAM高/クーラー側面クリアランス", "WARNING",
                               "RAMの高さデータなし（確認不可）")
        if clearance is None:
            return CheckResult("RAM高/クーラー側面クリアランス", "WARNING",
                               "クーラーの側面クリアランスデータなし（確認不可）")
        margin = clearance - ram_h
        if margin > 5:
            verdict = "OK"
            reason = f"RAM高 {ram_h}mm ≤ クーラー側面クリアランス {clearance}mm (マージン {margin}mm)"
        elif margin >= 0:
            verdict = "WARNING"
            reason = f"RAMとクーラーのクリアランスがギリギリ (マージン {margin}mm ≤ 5mm)"
        else:
            verdict = "NG"
            reason = f"RAM高超過: {ram_h}mm > クーラー側面クリアランス {clearance}mm (超過 {-margin}mm)"
        return CheckResult(
            "RAM高/クーラー側面クリアランス", verdict, reason,
            actual=f"{ram_h}mm", expected=f"≤{clearance}mm", margin=float(margin),
        )

    # ---------- チェック6: 電源容量 ----------
    def check_6_power(self, cpu: dict, gpu: dict, psu: dict) -> CheckResult:
        # max_turbo_power_w が優先、なければ tdp_w
        cpu_tdp = cpu["specs"].get("max_turbo_power_w") or cpu["specs"].get("tdp_w", 0)
        gpu_tdp = gpu["specs"].get("tdp_w", 0)
        psu_w   = psu["specs"].get("wattage_w", 0)
        total   = cpu_tdp + gpu_tdp
        needed  = int(total * 1.2)   # 20%マージン
        margin  = psu_w - needed
        if margin >= 0:
            verdict = "OK"
            reason  = (f"電源容量十分: {psu_w}W ≥ 推奨{needed}W "
                       f"(CPU {cpu_tdp}W + GPU {gpu_tdp}W = {total}W × 1.2)")
        else:
            verdict = "NG"
            reason  = (f"電源容量不足: {psu_w}W < 推奨{needed}W "
                       f"(CPU {cpu_tdp}W + GPU {gpu_tdp}W = {total}W × 1.2, "
                       f"不足 {-margin}W)")
        return CheckResult(
            "電源容量", verdict, reason,
            actual=f"{psu_w}W", expected=f"≥{needed}W", margin=float(margin),
        )

    # ---------- チェック7: MB/ケース フォームファクタ ----------
    def check_7_form_factor(self, mb: dict, case: dict) -> CheckResult:
        mb_ff   = mb["specs"].get("form_factor", "").upper()
        case_ff = case["specs"].get("form_factor", "").upper()

        # 互換マトリクス: ケースが ATX なら ATX/mATX/ITX を受け入れ
        compat_map = {
            "ATX":      {"ATX", "EATX", "MATX", "MICRO-ATX", "ITX", "MINI-ITX"},
            "MATX":     {"MATX", "MICRO-ATX", "ITX", "MINI-ITX"},
            "MICRO-ATX":{"MATX", "MICRO-ATX", "ITX", "MINI-ITX"},
            "ITX":      {"ITX", "MINI-ITX"},
            "MINI-ITX": {"ITX", "MINI-ITX"},
            "EATX":     {"ATX", "EATX", "MATX", "MICRO-ATX", "ITX", "MINI-ITX"},
        }
        case_accepts = compat_map.get(case_ff, {case_ff})
        if mb_ff in case_accepts:
            return CheckResult(
                "MB/ケース フォームファクタ", "OK",
                f"フォームファクタ対応: MB={mb_ff}, ケース={case_ff}",
                actual=mb_ff, expected=f"ケース{case_ff}対応サイズ",
            )
        return CheckResult(
            "MB/ケース フォームファクタ", "NG",
            f"フォームファクタ非互換: MB={mb_ff} はケース{case_ff}に収まらない",
            actual=mb_ff, expected=f"ケース{case_ff}対応サイズ",
        )

    # ---------- 全チェック実行 ----------
    def run(
        self,
        cpu: dict, mb: dict, ram: dict,
        gpu: dict, case: dict, cooler: dict, psu: dict,
        case_name: str = "",
    ) -> BuildCompatReport:
        report = BuildCompatReport(case_name=case_name)
        report.checks = [
            self.check_1_socket(cpu, mb),
            self.check_2_ddr(ram, mb),
            self.check_3_gpu_length(gpu, case),
            self.check_4_cooler_height(cooler, case),
            self.check_5_ram_clearance(ram, cooler),
            self.check_6_power(cpu, gpu, psu),
            self.check_7_form_factor(mb, case),
        ]
        return report


# ------------------------------------------------------------------ #
# テストクラス
# ------------------------------------------------------------------ #
class TestCompatE2E(unittest.TestCase):
    """実データを使ったE2E互換性診断テスト"""

    @classmethod
    def setUpClass(cls):
        cls.checker = CompatibilityChecker()

        # ── 共通パーツ ──────────────────────────────────────
        cls.cpu_ryzen = _find_by_name("amd_cpu", "9950X")
        cls.cpu_intel = _find_by_name("intel_cpu", "Core Ultra 9 285K")
        cls.mb_x870e  = _find_by_name("asrock_mb", "X870E Taichi OCF")
        cls.ram_ven   = _find_by_name("corsair_ram", "Vengeance DDR5-6000 32GB Kit (2x16GB)")
        cls.gpu_4090  = _find_by_name("asus", "TUF Gaming GeForce RTX 4090")
        cls.case_h510  = _find_by_name("cases", "H510")
        cls.case_h200i = _find_by_name("cases", "H200i")
        # NH-D15 original を id で直接取得（"NH-D15 G2" との部分一致衝突を回避）
        cls.cooler_nhd15 = next(
            (r for r in _load_jsonl(DATA_DIR / "noctua_cooler" / "products.jsonl")
             if r["id"] == "noctua_nh-d15"),
            None,
        )
        cls.psu_dp14_1000 = _find_by_name("bequiet_psu", "DARK POWER 14 1000W")
        cls.psu_pp12m_650 = _find_by_name("bequiet_psu", "PURE POWER 12M 650W")

    # ── データ存在チェック ──────────────────────────────────
    def test_00_data_exists(self):
        """全パーツのデータが products.jsonl に存在すること"""
        parts = {
            "Ryzen 9 9950X":             self.cpu_ryzen,
            "Core Ultra 9 285K":         self.cpu_intel,
            "ASRock X870E Taichi OCF":   self.mb_x870e,
            "Corsair Vengeance DDR5-6000 32GB": self.ram_ven,
            "ASUS TUF RTX4090":          self.gpu_4090,
            "NZXT H510":                 self.case_h510,
            "NZXT H200i":                self.case_h200i,
            "Noctua NH-D15 (original)":  self.cooler_nhd15,
            "be quiet! DARK POWER 14 1000W": self.psu_dp14_1000,
            "be quiet! PURE POWER 12M 650W": self.psu_pp12m_650,
        }
        for name, data in parts.items():
            with self.subTest(part=name):
                self.assertIsNotNone(data, f"データが見つかりません: {name}")

    def test_00b_nh_d15_original_height(self):
        """NH-D15 (original) の高さが 165mm であること (G2=168mm と区別)"""
        self.assertIsNotNone(self.cooler_nhd15)
        h = self.cooler_nhd15["specs"]["height_mm"]
        self.assertEqual(h, 165, f"NH-D15 height: expected 165, got {h}")

    def test_00c_nh_d15_side_clearance(self):
        """NH-D15 (original) に side_clearance_mm フィールドがあること"""
        self.assertIsNotNone(self.cooler_nhd15)
        self.assertIn("side_clearance_mm", self.cooler_nhd15["specs"])
        self.assertEqual(self.cooler_nhd15["specs"]["side_clearance_mm"], 62)

    def test_00d_corsair_vengeance_height(self):
        """Corsair Vengeance DDR5-6000 に height_mm=44 があること"""
        self.assertIsNotNone(self.ram_ven)
        h = self.ram_ven["specs"].get("height_mm")
        self.assertEqual(h, 44)

    # ── テストケース1: 正常構成 ────────────────────────────
    def _run_case1(self) -> BuildCompatReport:
        return self.checker.run(
            cpu=self.cpu_ryzen, mb=self.mb_x870e, ram=self.ram_ven,
            gpu=self.gpu_4090, case=self.case_h510,
            cooler=self.cooler_nhd15, psu=self.psu_dp14_1000,
            case_name="Case1: 正常構成 (Ryzen9 9950X + X870E + H510 + RTX4090 + DP14-1000W)",
        )

    def test_case1_overall_warning(self):
        """テストケース1の総合判定は WARNING (クーラー高margin=0mm)"""
        report = self._run_case1()
        print(report.summary())
        self.assertEqual(
            report.overall_verdict, "WARNING",
            f"総合判定は WARNING 期待だが {report.overall_verdict} だった"
        )

    def test_case1_socket_ok(self):
        """Case1: CPU/MB ソケット一致 (AM5=AM5) → OK"""
        r = self._run_case1()
        check = next(c for c in r.checks if "ソケット" in c.check_name)
        self.assertEqual(check.verdict, "OK", f"ソケットチェック: {check.reason}")

    def test_case1_ddr_ok(self):
        """Case1: DDR世代一致 (DDR5=DDR5) → OK"""
        r = self._run_case1()
        check = next(c for c in r.checks if "DDR" in c.check_name)
        self.assertEqual(check.verdict, "OK", f"DDRチェック: {check.reason}")

    def test_case1_gpu_length_ok(self):
        """Case1: GPU長 348mm ≤ H510最大 381mm (margin=33mm) → OK"""
        r = self._run_case1()
        check = next(c for c in r.checks if "GPU長" in c.check_name)
        self.assertEqual(check.verdict, "OK", f"GPU長チェック: {check.reason}")
        self.assertAlmostEqual(check.margin, 33.0)

    def test_case1_cooler_height_warning(self):
        """Case1: NH-D15(165mm) = H510最大(165mm) → margin=0mm → WARNING"""
        r = self._run_case1()
        check = next(c for c in r.checks if "クーラー高" in c.check_name)
        self.assertEqual(check.verdict, "WARNING",
                         f"クーラー高チェック: expected WARNING, got {check.verdict}\n{check.reason}")
        self.assertAlmostEqual(check.margin, 0.0)

    def test_case1_ram_clearance_ok(self):
        """Case1: RAM高44mm ≤ NH-D15クリアランス62mm (margin=18mm) → OK"""
        r = self._run_case1()
        check = next(c for c in r.checks if "RAM高" in c.check_name)
        self.assertEqual(check.verdict, "OK", f"RAM高チェック: {check.reason}")
        self.assertAlmostEqual(check.margin, 18.0)

    def test_case1_power_ok(self):
        """Case1: 電源容量 1000W ≥ (230+450)×1.2=816W → OK"""
        r = self._run_case1()
        check = next(c for c in r.checks if "電源" in c.check_name)
        self.assertEqual(check.verdict, "OK", f"電源チェック: {check.reason}")
        # margin = 1000 - 816 = 184
        self.assertGreater(check.margin, 0)

    def test_case1_form_factor_ok(self):
        """Case1: MB=ATX, Case=ATX → OK"""
        r = self._run_case1()
        check = next(c for c in r.checks if "フォームファクタ" in c.check_name)
        self.assertEqual(check.verdict, "OK", f"フォームファクタチェック: {check.reason}")

    # ── テストケース2: NGあり構成 ──────────────────────────
    def _run_case2(self) -> BuildCompatReport:
        return self.checker.run(
            cpu=self.cpu_intel, mb=self.mb_x870e, ram=self.ram_ven,
            gpu=self.gpu_4090, case=self.case_h200i,
            cooler=self.cooler_nhd15, psu=self.psu_pp12m_650,
            case_name="Case2: NGあり構成 (Core Ultra 9 285K + X870E(AM5) + H200i + RTX4090 + PP12M-650W)",
        )

    def test_case2_overall_ng(self):
        """テストケース2の総合判定は NG"""
        report = self._run_case2()
        print(report.summary())
        self.assertEqual(
            report.overall_verdict, "NG",
            f"総合判定は NG 期待だが {report.overall_verdict} だった"
        )

    def test_case2_socket_ng(self):
        """Case2: CPU=LGA1851, MB=AM5 → NG"""
        r = self._run_case2()
        check = next(c for c in r.checks if "ソケット" in c.check_name)
        self.assertEqual(check.verdict, "NG", f"ソケットチェック: {check.reason}")

    def test_case2_ddr_ok(self):
        """Case2: DDR世代は一致 (DDR5=DDR5) → OK (ソケット問題とは独立)"""
        r = self._run_case2()
        check = next(c for c in r.checks if "DDR" in c.check_name)
        self.assertEqual(check.verdict, "OK", f"DDRチェック: {check.reason}")

    def test_case2_gpu_length_ng(self):
        """Case2: GPU長348mm > H200i最大328mm → margin=-20mm → NG"""
        r = self._run_case2()
        check = next(c for c in r.checks if "GPU長" in c.check_name)
        self.assertEqual(check.verdict, "NG", f"GPU長チェック: {check.reason}")
        self.assertAlmostEqual(check.margin, -20.0)

    def test_case2_cooler_height_warning(self):
        """Case2: NH-D15(165mm), H200i最大(167mm) → margin=2mm → WARNING"""
        r = self._run_case2()
        check = next(c for c in r.checks if "クーラー高" in c.check_name)
        self.assertIn(check.verdict, ("WARNING", "NG"),
                      f"クーラー高チェック: expected WARNING/NG, got {check.verdict}")
        self.assertAlmostEqual(check.margin, 2.0)

    def test_case2_ram_clearance_ok(self):
        """Case2: RAM高44mm ≤ NH-D15クリアランス62mm → OK"""
        r = self._run_case2()
        check = next(c for c in r.checks if "RAM高" in c.check_name)
        self.assertEqual(check.verdict, "OK", f"RAM高チェック: {check.reason}")

    def test_case2_power_ng(self):
        """Case2: 650W < (250+450)×1.2=840W → NG"""
        r = self._run_case2()
        check = next(c for c in r.checks if "電源" in c.check_name)
        self.assertEqual(check.verdict, "NG", f"電源チェック: {check.reason}")
        self.assertLess(check.margin, 0)

    def test_case2_form_factor_ng(self):
        """Case2: MB=ATX, Case=Mini-ITX → NG"""
        r = self._run_case2()
        check = next(c for c in r.checks if "フォームファクタ" in c.check_name)
        self.assertEqual(check.verdict, "NG",
                         f"フォームファクタチェック: expected NG, got {check.verdict}\n{check.reason}")

    def test_case2_ng_count(self):
        """Case2: NG判定が4件以上あること (Socket/GPU長/電源/フォームファクタ)"""
        r = self._run_case2()
        ng_items = [c for c in r.checks if c.verdict == "NG"]
        self.assertGreaterEqual(
            len(ng_items), 4,
            f"NG件数が4未満: {[(c.check_name, c.verdict) for c in r.checks]}"
        )


# ------------------------------------------------------------------ #
# ヘルパー: NZXT H200i のデータを name "H200i" で検索できるか確認用
# ------------------------------------------------------------------ #
class TestDataSearch(unittest.TestCase):
    """データ検索ヘルパーの動作確認"""

    def test_find_h510(self):
        r = _find_by_name("cases", "H510")
        self.assertIsNotNone(r)
        self.assertEqual(r["specs"]["max_gpu_length_mm"], 381)
        self.assertEqual(r["specs"]["max_cpu_cooler_height_mm"], 165)

    def test_find_h200i(self):
        r = _find_by_name("cases", "H200i")
        self.assertIsNotNone(r)
        self.assertEqual(r["specs"]["max_gpu_length_mm"], 328)
        self.assertIn(r["specs"]["form_factor"].upper(), ("MINI-ITX", "ITX"))

    def test_find_nh_d15_original_not_g2(self):
        """NH-D15 (original) と NH-D15 G2 が name で区別できること"""
        # "NH-D15" で最初にヒットするのは original であること
        # (ファイル順: G2 -> G2 chromax -> NH-D15 -> NH-D15 chromax -> NH-U12A)
        # ただし _find_by_name は部分一致なので G2 もヒットする可能性がある
        # より正確に: 全リストから G2 を除外して取得
        records = _load_jsonl(DATA_DIR / "noctua_cooler" / "products.jsonl")
        nh_d15_originals = [
            r for r in records
            if "nh-d15" in r["id"].lower()
            and "g2" not in r["id"].lower()
            and "u12a" not in r["id"].lower()
        ]
        self.assertGreater(len(nh_d15_originals), 0, "NH-D15 original が見つからない")
        for r in nh_d15_originals:
            self.assertEqual(
                r["specs"]["height_mm"], 165,
                f"{r['name']} の高さは165mm であるべき: {r['specs']['height_mm']}"
            )

    def test_bequiet_psu_wattage(self):
        """be quiet! PSU の wattage_w が正しく設定されていること"""
        dp14 = _find_by_name("bequiet_psu", "DARK POWER 14 1000W")
        pp12m = _find_by_name("bequiet_psu", "PURE POWER 12M 650W")
        self.assertIsNotNone(dp14)
        self.assertIsNotNone(pp12m)
        self.assertEqual(dp14["specs"]["wattage_w"], 1000)
        self.assertEqual(pp12m["specs"]["wattage_w"], 650)


if __name__ == "__main__":
    unittest.main(verbosity=2)
