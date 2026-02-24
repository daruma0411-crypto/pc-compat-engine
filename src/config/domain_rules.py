"""
自作PC互換性判定 ドメインルール
=================================
AKGNETが自作PCパーツのスペック・PDFマニュアルから蓄積した、
PC組み立て固有の互換性制約・物理干渉・排他制限の知識ベース。

「スペック数値マッチング」ではなく「PDFの注意書きを推論で検出する」が
PCPartPickerとの本質的差別化ポイント。
"""

# ============================================================
# カテゴリ別 互換性チェックルール
# ============================================================

CATEGORY_RULES = {
    "gpu": {
        "name": "GPU（グラフィックカード）",
        "required_checks": [
            "物理寸法（BigQuery）: カード長(mm)、スロット厚(2slot/3slot/4slot)、高さ(mm)",
            "補助電源（BigQuery）: 6pin/8pin/16pin(PCIe 5.0 12VHPWR)の本数とTDP",
            "PCIeスロット（BigQuery）: PCIe 4.0 x16 / 5.0 x16 の帯域要件",
            "ケース干渉（BigQuery cross）: ケースGPU最大長との比較、サイドフロー型との干渉",
            "電源容量（BigQuery cross）: GPU TDP + CPU TDP + 周辺 ≤ 電源定格 × 0.8",
            "PCIe 5.0補助電源注意（PageIndex）: 12VHPWRコネクタの取り付け角度と溶損事例",
        ],
        "interference_patterns": [
            "ケース内のサイドパネルとの干渉: カード高さ × スロット数で実効幅を確認",
            "マザーボードのM.2スロット封鎖: GPU装着後に下段M.2が取り外し不可になるケースがある",
            "3/4スロット厚GPUとPCIe x1スロットの占有: 他のPCIeデバイスが装着不可になる",
            "PCIe 5.0（12VHPWR）変換アダプタは熱収縮・接触不良リスク: PDFで使用不推奨の明示あり",
        ],
        "search_hints": [
            "GPU長はカード基板長ではなく端子含む『実装長』で比較すること",
            "3スロット占有GPUはPCIe x16スロットの真下のスロットを物理的に塞ぐ",
            "TDPは公称値より実効消費電力（Power Limit 100%時）で判断する",
            "12VHPWRコネクタは16pinで1本あたり最大600W供給可能だが、ケーブルのベンド角に注意が必要",
        ],
    },
    "motherboard": {
        "name": "マザーボード",
        "required_checks": [
            "CPUソケット（BigQuery）: LGA1851/LGA1700/AM5/AM4 ― CPUと完全一致必須",
            "チップセット（BigQuery）: Z/B/H/X 系ごとのオーバークロック可否・PCIeレーン数",
            "フォームファクター（BigQuery）: ATX/mATX/ITX ― ケースの対応規格と照合",
            "M.2スロット排他制限（PageIndex）: 特定M.2使用時のPCIe x16帯域半減・x4スロット無効化",
            "PCIeスロット構成（BigQuery）: x16/x4/x1の本数と帯域共有マトリクス",
            "メモリスロット（BigQuery）: DDR4/DDR5、スロット数、最大容量、XMP/EXPO対応",
            "VRMフェーズ数（PageIndex）: 高TDP CPUでのVRM温度・電力供給能力の注意書き",
        ],
        "interference_patterns": [
            "M.2 M-key スロット2本目使用 → CPU直結PCIe x16が x8動作に降格（Intel Z690/Z790で頻発）",
            "M.2 E-key（WiFiスロット）とPCIe x1スロットの共有バス: 同時使用不可",
            "SATAポートとM.2 SATA共有: M.2にSATA SSD挿入でSATAポート2本が無効化",
            "ATX 2スロットGPU装着でx1スロットが物理封鎖される（ボード上の配置依存）",
            "CPUクーラーバックプレートとmATXボードの干渉: 裏面部品との接触に注意",
        ],
        "search_hints": [
            "M.2/PCIe排他制限はマザーボードのPDFマニュアル『Bandwidth Sharing』節に記載",
            "AM4 CPUはAM5マザーに非対応（ソケット形状・ピン数が異なる）",
            "同一チップセットでもメーカーにより排他制限の実装が異なる場合がある",
            "ITXマザーはM.2スロットが1〜2本のみで、PCIeスロットもx16が1本のみが標準",
        ],
    },
    "case": {
        "name": "PCケース",
        "required_checks": [
            "フォームファクター対応（BigQuery）: ATX/mATX/ITX のマザーボード対応表",
            "GPU最大長（BigQuery）: ケースのGPUクリアランス(mm)とGPU実装長(mm)の比較",
            "CPUクーラー最大高（BigQuery）: ケースの高さ制限(mm)とクーラー全高(mm)の比較",
            "電源規格（BigQuery）: ATX/SFX/SFX-L ― 電源ユニットの規格と照合",
            "ラジエーター搭載（BigQuery）: 簡易/本格水冷ラジエーターの最大サイズ（120/240/360mm）",
            "物理干渉注意書き（PageIndex）: ハイエンドGPU搭載時の電源ケーブル取り回し、ドライブベイ干渉",
        ],
        "interference_patterns": [
            "GPU長制限は『ドライブベイ非搭載時』の値であることが多い: ドライブベイ搭載時は短くなる",
            "フロント240mmラジエーター搭載時にGPUとの隙間が5mm未満になるケースがある",
            "SFX電源+ATXマザーの組み合わせはケースによってはATXブラケットが必要",
            "ITXケースの電源奥行き制限: SFX-Lは130mm/SFXは100mmの制限があるケースが存在する",
        ],
        "search_hints": [
            "ケースのGPU最大長はサイドパネル内側からM/Bバックパネルまでの実測値で判断",
            "mATXケースはATXマザーを搭載できない（穴ピッチが違う）",
            "フルタワーでもCPUクーラー最大高は180mm前後が多い: 高さ170mmの巨大クーラーに注意",
        ],
    },
    "cpu_cooler": {
        "name": "CPUクーラー",
        "required_checks": [
            "ソケット対応（BigQuery）: LGA1851/LGA1700/AM5/AM4 ― CPUソケットと照合",
            "全高（BigQuery）: クーラー全高(mm) ≤ ケースCPUクーラー最大高(mm)",
            "TDP対応（BigQuery）: クーラー定格TDP ≥ CPU TDP（簡易水冷は適用TDP注意）",
            "メモリ干渉（PageIndex）: タワークーラーとメモリスロット1/2本目の干渉",
            "バックプレート干渉（PageIndex）: AM4/AM5付属バックプレートとケース底面の干渉",
            "RAM高さ制限（BigQuery cross）: クーラーの側面クリアランスとメモリヒートシンク高の比較",
        ],
        "interference_patterns": [
            "大型タワークーラー（Noctua NH-D15等）はメモリスロット1〜2番目が物理的に封鎖される",
            "LGA1851（Intel 13/14th Gen）はLGA1700と互換あり: リテンションがほぼ共通",
            "AM4→AM5マウントキットは多くのメーカーが無償提供しているがFANの取り付け方向が変わる",
            "AIO水冷ポンプヘッドの高さがケースCPUクーラー最大高制限と干渉するケースがある",
        ],
        "search_hints": [
            "タワークーラーの「メモリ干渉チェック」はクーラー側面からスロット1番端までの距離(mm)で判断",
            "LGA1700/1851はILM（独自保持機構）とサードパーティLGA1700対応の2タイプがある",
            "簡易水冷の定格TDPは『240mm: 250W対応』等と記載されるがケース内エアフローに大きく依存",
        ],
    },
    "psu": {
        "name": "電源ユニット（PSU）",
        "required_checks": [
            "定格出力（BigQuery cross）: GPU TDP + CPU TDP + 他 ≤ 定格W × 0.80（20%マージン）",
            "規格（BigQuery）: ATX/SFX/SFX-L ― ケースの電源規格と照合",
            "奥行き（BigQuery）: ATX電源の奥行き(mm) ≤ ケースの電源スペース(mm)",
            "12VHPWR対応（BigQuery）: PCIe 5.0 GPU使用時にネイティブ16pinケーブル対応か確認",
            "モジュラー方式（BigQuery）: フルモジュラー/セミモジュラー/非モジュラーとケース配線スペース",
            "80PLUS認証（BigQuery）: Bronze/Gold/Platinum/Titaniumとワット帯のマッチング",
        ],
        "interference_patterns": [
            "ATX電源の奥行きは140mm/160mm/180mm/200mmと幅広い: コンパクトケースは150mm以下を推奨",
            "SFX-L（130mm）はSFXマウントにブラケットなしでは設置不可",
            "PCIe 5.0世代GPU（RTX 4090等）は12VHPWRネイティブ電源でないと変換アダプタが必要で溶損リスク",
            "低価格帯電源はピーク時に表記ワット数を維持できないケースがある（瞬間消費電力に注意）",
        ],
        "search_hints": [
            "必要ワット数の計算: GPU TDP + CPU TDP + MB 80W + RAM 10W/枚 + SSD 5W + FANなどを合算",
            "コンパクトケースでは奥行き140mm以下のATX電源が推奨される場合がある",
            "12VHPWRケーブルのネイティブ対応確認はPDFのスペック表『PCIe 5.0 Ready』記載を参照",
        ],
    },
    "memory": {
        "name": "メモリ（RAM）",
        "required_checks": [
            "DDR世代（BigQuery）: DDR4/DDR5 ― マザーボードのスロット規格と必ず一致（互換なし）",
            "速度（BigQuery）: XMPプロファイル速度(MT/s) ≤ マザーボード最大メモリ速度",
            "容量（BigQuery）: 総容量(GB) ≤ マザーボード最大搭載容量",
            "スロット数（BigQuery）: デュアルチャンネル推奨（A2/B2スロット使用）",
            "ヒートシンク高（BigQuery cross）: メモリ全高(mm) ≤ CPUクーラーの側面クリアランス",
            "ECC/non-ECC（BigQuery）: サーバー向けECCメモリはコンシューマMBで非対応が多い",
        ],
        "interference_patterns": [
            "DDR4とDDR5はスロット形状（ノッチ位置）が異なり物理的に挿さらない",
            "DDR5高速品（6000MT/s超）はAMD Expo/Intel XMP有効化必須: デフォルトは4800MT/sで動作",
            "背高ヒートシンクメモリ（45mm超）は大型タワークーラーのフィン側面と接触するケースがある",
            "Intel 13th Gen以降でDDR5-6400超を使用する場合、SA電圧が高くなりメモリ劣化リスクがある",
        ],
        "search_hints": [
            "マザーボードのQVL（Qualified Vendor List）に掲載された組み合わせが最も安全",
            "AMD Expo対応メモリはIntel XMPにも対応している製品が多い",
            "4枚挿しはデュアルチャンネル維持だがクロックが下がるケースがある",
        ],
    },
}


# ============================================================
# クエリパターン別 検索戦略
# ============================================================

QUERY_PATTERNS = {

    # ----------------------------------------------------------------
    # 最重要: 「この構成で組めるか？」 全構成チェック
    # 建材版のusability_checkに相当するが、PCでは複数パーツの
    # 多対多の干渉マトリクスを全チェックする必要がある
    # ----------------------------------------------------------------
    "build_compatibility": {
        "pattern": "複数パーツを列挙して全体の組み合わせ可否を確認",
        "examples": [
            "RTX 4090 + Z790 + NH-D15 + DDR5-6000で組めるか？",
            "この構成で問題ないか確認して",
            "GPU: xxx, MB: yyy, Case: zzz は互換性ある？",
        ],
        "strategy": (
            "【フェーズ1: スペック収集】BigQuery で各パーツのスペックを並列取得。"
            "GPU(長さ/スロット/TDP/電源コネクタ)、MB(ソケット/フォームファクター/M.2構成)、"
            "ケース(GPU最大長/クーラー最大高/対応MB規格)、クーラー(対応ソケット/全高/サイドクリアランス)、"
            "電源(定格W/規格/奥行き)、メモリ(DDR世代/高さ)を一括取得。"
            "【フェーズ2: 排他制限チェック】PageIndex で MB/ケースPDFの『Bandwidth Sharing』"
            "『Limitations』『Warning』セクションを探索。M.2/PCIe排他、ドライブベイ干渉を確認。"
            "【フェーズ3: 計算チェック】電源容量計算(TDP合計×1.2)、物理クリアランス比較を実行。"
            "【フェーズ4: 統合判定】全チェック結果を OK / WARNING / NG / 要確認 の4段階で報告。"
        ),
        "tools": ["bigquery", "bigquery", "pageindex"],  # BQ並列×2 → PageIndex
        "check_matrix": [
            "CPU ↔ MB: ソケット一致",
            "CPU ↔ CPUクーラー: ソケット一致 + TDP対応",
            "MB ↔ ケース: フォームファクター一致",
            "GPU ↔ ケース: GPU長 ≤ ケースGPU最大長",
            "GPUスロット厚 ↔ MB: 隣接PCIeスロット・M.2スロット封鎖確認",
            "CPUクーラー高さ ↔ ケース: 全高 ≤ ケースCPUクーラー最大高",
            "CPUクーラー ↔ メモリ: サイドクリアランス ≥ メモリ全高",
            "電源 ↔ ケース: 規格一致 + 奥行き確認",
            "電源W ↔ GPU+CPU TDP: 合計TDP×1.2 ≤ 定格W",
            "メモリ ↔ MB: DDR世代一致 + 速度範囲内",
            "MB M.2構成 ↔ 構成要件: 排他制限による使用可スロット確認",
        ],
    },

    # ----------------------------------------------------------------
    # 物理干渉チェック（2パーツ間の寸法比較）
    # ----------------------------------------------------------------
    "physical_interference": {
        "pattern": "2つのパーツ間の物理的な干渉・寸法クリアランスを確認",
        "examples": [
            "NH-D15はこのケースに入るか？",
            "RTX 4090の長さがこのケースに収まるか？",
            "このメモリはNH-D15と干渉しないか？",
        ],
        "strategy": (
            "BigQueryで両パーツの関連寸法を取得。"
            "ケースvsGPU: ケースGPU最大長(mm) ≥ GPU実装長(mm)。"
            "ケースvsクーラー: ケースCPUクーラー最大高(mm) ≥ クーラー全高(mm)。"
            "クーラーvsメモリ: クーラー側面クリアランス(mm) ≥ メモリ全高(mm)。"
            "マージン10mm未満は WARNING として報告。"
            "PDFマニュアルの『Clearance』『Limitation』セクションも PageIndex で確認。"
        ),
        "tools": ["bigquery", "pageindex"],
        "margin_rules": {
            "gpu_case": "マージン < 5mm → NG, 5〜15mm → WARNING, > 15mm → OK",
            "cooler_case": "マージン < 5mm → NG, 5〜10mm → WARNING, > 10mm → OK",
            "cooler_memory": "マージン < 0mm → NG, 0〜5mm → WARNING, > 5mm → OK",
            "psu_case": "マージン < 0mm → NG, ぴったりの場合はケーブル取り回し注意を追記",
        },
    },

    # ----------------------------------------------------------------
    # M.2/PCIe 排他制限チェック（最も見落とされやすいNG原因）
    # ----------------------------------------------------------------
    "m2_pcie_conflict": {
        "pattern": "M.2スロット使用数によるPCIeレーン帯域低下・ポート無効化の確認",
        "examples": [
            "M.2 SSDを2本挿したらGPUに影響するか？",
            "このマザーでM.2を3本使いたい",
            "SATAポートが使えなくなると聞いたが本当か？",
        ],
        "strategy": (
            "PageIndex でマザーボードPDFの『M.2 & SATA Bandwidth Sharing』"
            "または『Limitations』セクションを最優先で探索。"
            "特にチェックすべき排他パターン:"
            "(1) M.2_2スロット使用 → PCIe x16スロットがx8動作に降格;"
            "(2) M.2_1スロット(SATA)使用 → SATAポート5/6番が無効化;"
            "(3) M.2_E-keyスロット(WiFi)使用 → PCIe x1スロット1番が無効化。"
            "BigQueryでMBのM.2スロット仕様テーブルを取得して対照する。"
        ),
        "tools": ["pageindex", "bigquery"],
        "known_patterns": {
            "intel_z790": "M.2スロット3本目以降でCPU直結x16がx8に降格するケースあり",
            "intel_b760": "M.2スロット増設でSATAポート削減（チップセットPCIeレーン上限）",
            "amd_x670e": "CPU側M.2_1とGPU x16は独立レーン: 排他制限が少ない",
            "amd_b650": "チップセット接続M.2がPCIe 4.0のみ: NVMe Gen5 SSDは速度上限あり",
        },
    },

    # ----------------------------------------------------------------
    # 電源容量チェック
    # ----------------------------------------------------------------
    "power_budget": {
        "pattern": "電源容量が構成全体の消費電力をまかなえるか確認",
        "examples": [
            "850W電源でこの構成は足りるか？",
            "RTX 4090 + i9-14900Kに何W電源が必要？",
            "電源容量に余裕があるか確認して",
        ],
        "strategy": (
            "BigQueryで各パーツのTDP/消費電力を取得。"
            "計算式: GPU TDP + CPU TDP + MB消費電力(推定80W) + RAM(10W×枚数) "
            "+ SSD(5W×本数) + FAN(5W×台数) = 総計。"
            "推奨電源: 総計 × 1.25（25%マージン）以上。"
            "特にRTX 4090（450W）+ Core i9-14900K（253W）= 703W → 推奨850W以上。"
            "PageIndexでPDFの『Power Requirement』『System Requirements』セクションも確認。"
        ),
        "tools": ["bigquery", "pageindex"],
        "rules": {
            "minimum_margin": "総TDP × 1.20 以上",
            "recommended_margin": "総TDP × 1.25 以上",
            "high_end_rule": "RTX 4090 / RX 7900 XTX 搭載時は最低850W、推奨1000W",
            "cable_rule": "12VHPWR(16pin)が必要なGPUはネイティブ対応電源を強く推奨",
        },
    },

    # ----------------------------------------------------------------
    # ソケット整合チェック（CPU + MB + クーラーの3点確認）
    # ----------------------------------------------------------------
    "socket_check": {
        "pattern": "CPU・マザーボード・CPUクーラーのソケット互換性を確認",
        "examples": [
            "Ryzen 9 7950XはこのマザーとCPUクーラーに対応しているか？",
            "LGA1700のクーラーをAM5で使えるか？",
            "AM4のCPUをAM5マザーに挿せるか？",
        ],
        "strategy": (
            "BigQueryでCPU/MB/クーラーのソケット情報を取得。"
            "CPU ↔ MB: ソケット完全一致（AM4 ≠ AM5、LGA1700 ≠ LGA1851）。"
            "クーラー ↔ CPU: 対応ソケットリストにCPUのソケットが含まれるか確認。"
            "クーラーマウントキット: AM4→AM5移行品は多くのメーカーが無償提供しているが"
            "PageIndexでメーカーPDFの対応リストを確認する。"
        ),
        "tools": ["bigquery", "pageindex"],
        "socket_map": {
            "LGA1851": "Intel Core Ultra 200S (Arrow Lake)",
            "LGA1700": "Intel 12th/13th/14th Gen (Alder/Raptor Lake)",
            "AM5": "AMD Ryzen 7000/8000/9000 (Zen 4/5)",
            "AM4": "AMD Ryzen 1000〜5000/Athlon (Zen〜Zen 3)",
        },
        "cross_socket_notes": {
            "LGA1700_to_LGA1851": "多くのクーラーがマウント共用可能: ただしメーカー確認必須",
            "AM4_to_AM5": "マウント穴間隔が同一: AM4対応クーラーはAM5キット追加で流用可能が多い",
            "LGA_to_AM": "Intel ↔ AMD間での流用は不可（バックプレート・マウント形状が異なる）",
        },
    },

    # ----------------------------------------------------------------
    # スペック検索（単品スペック調査）
    # ----------------------------------------------------------------
    "spec_lookup": {
        "pattern": "特定パーツのスペックを調べる",
        "examples": [
            "RTX 4080 SuperのTDPは？",
            "NH-D15のAM5対応ソケット一覧",
            "B650MATXマザーのM.2スロット数",
        ],
        "strategy": (
            "BigQuery優先。品番・モデル名でSQLクエリ。"
            "ワイルドカード（RTX 4080*）はLIKE検索。"
            "不明点はPageIndexのPDFスペック表も参照。"
        ),
        "tools": ["bigquery"],
    },

    # ----------------------------------------------------------------
    # DDR世代・メモリ速度チェック
    # ----------------------------------------------------------------
    "memory_compatibility": {
        "pattern": "メモリとマザーボードの互換性確認（DDR世代・速度・スロット）",
        "examples": [
            "DDR5-6000はこのマザーで動くか？",
            "DDR4メモリをDDR5マザーに挿せるか？",
            "このメモリは4枚挿しでデュアルチャンネルになるか？",
        ],
        "strategy": (
            "BigQueryでMBのメモリ対応規格（DDR4/DDR5）と最大速度を取得。"
            "DDR4 ↔ DDR5は物理互換なし（ノッチ位置が異なる）: 即NG判定。"
            "速度チェック: メモリのネイティブ速度 or XMP速度 ≤ MBの最大対応速度。"
            "PageIndexでMBのQVL（Qualified Vendor List）ページを検索し、"
            "対象メモリモデルが掲載されているか確認。"
        ),
        "tools": ["bigquery", "pageindex"],
    },

    # ----------------------------------------------------------------
    # 水冷クーラー搭載可否チェック
    # ----------------------------------------------------------------
    "aio_compatibility": {
        "pattern": "簡易水冷（AIO）のラジエーター搭載可否確認",
        "examples": [
            "360mmラジエーターをこのケースに搭載できるか？",
            "フロントに280mmラジエーターは入るか？",
        ],
        "strategy": (
            "BigQueryでケースのラジエーター対応表（フロント/トップ/リア別の最大サイズ）を取得。"
            "取り付け位置（フロント/トップ/リア）と対応ラジエーターサイズを照合。"
            "PageIndexでケースPDFの『Radiator Support』または『Water Cooling』セクションを検索。"
            "フロント240mmラジエーターとGPU長の干渉チェックも合わせて実施。"
        ),
        "tools": ["bigquery", "pageindex"],
    },

    # ----------------------------------------------------------------
    # PCIe 5.0 / 最新規格の注意事項チェック
    # ----------------------------------------------------------------
    "next_gen_warnings": {
        "pattern": "PCIe 5.0 GPU・NVMe Gen5・DDR5最高速など最新規格の注意事項確認",
        "examples": [
            "PCIe 5.0 GPUの取り付けで注意することは？",
            "NVMe Gen5 SSDはヒートシンクが必要か？",
            "DDR5-8000は実際に動くか？",
        ],
        "strategy": (
            "PageIndex優先。メーカーPDFの『Warning』『Caution』『Note』セクションを重点探索。"
            "既知の注意事項:"
            "(1) 12VHPWR(PCIe 5.0補助電源): ケーブルベンド角 < 35度で溶損リスク;"
            "(2) NVMe Gen5 SSD: 80℃超の発熱 → ケース内ヒートシンク必須;"
            "(3) DDR5-8000超: Intel SA電圧上昇でメモリ寿命低下の可能性;"
            "(4) RTX 4090補助電源変換アダプタ: NVIDIA推奨品以外は非推奨。"
            "BigQueryで対象パーツのスペック確認も並行実施。"
        ),
        "tools": ["pageindex", "bigquery"],
    },

    # ----------------------------------------------------------------
    # トラブルシューティング・FAQ
    # ----------------------------------------------------------------
    "troubleshooting": {
        "pattern": "組み立て後の不具合・既知の問題・回避策を調べる",
        "examples": [
            "起動しない原因を教えて",
            "メモリが認識されない時の対処法",
            "RTX 4090で12VHPWRが溶けた事例はある？",
        ],
        "strategy": (
            "VectorDB優先（過去のユーザー事例・FAQ）。"
            "次にPageIndex（メーカーのトラブルシューティングセクション）。"
            "既知の問題はVectorDBに蓄積されているため、まず意味検索で類似事例を探索。"
        ),
        "tools": ["vector_db", "pageindex"],
    },
}


# ============================================================
# メーカー・品番パターン認識ルール
# ============================================================

PART_NUMBER_PATTERNS = {
    "nvidia_gpu": {
        "manufacturer": "NVIDIA（AIC各社: ASUS/MSI/GIGABYTE/EVGA/Zotac/Palit）",
        "series_map": {
            "RTX 50": "Blackwell (PCIe 5.0, 12VHPWR×2)",
            "RTX 40": "Ada Lovelace (PCIe 4.0/5.0, 12VHPWR×1)",
            "RTX 30": "Ampere (PCIe 4.0, 8pin×1〜3)",
            "RTX 20": "Turing (PCIe 3.0, 8pin×1〜2)",
        },
        "patterns": [
            r"RTX\s*\d{4}(?:\s*Ti|\s*Super|\s*SUPER)?",
            r"GTX\s*\d{4}(?:\s*Ti)?",
            r"RX\s*\d{4}(?:\s*XT|\s*XTX)?",
        ],
        "wildcard_hint": "RTX 4080*でRTX 4080・RTX 4080 Super両方をヒット可能",
    },
    "amd_gpu": {
        "manufacturer": "AMD（AIC各社: ASUS/MSI/GIGABYTE/PowerColor/XFX/Sapphire）",
        "series_map": {
            "RX 9000": "RDNA 4 (PCIe 5.0)",
            "RX 7000": "RDNA 3 (PCIe 4.0, 8pin系)",
            "RX 6000": "RDNA 2 (PCIe 4.0, 8pin系)",
        },
        "patterns": [
            r"RX\s*\d{4}(?:\s*XT|\s*XTX|\s*GRE)?",
        ],
        "wildcard_hint": "RX 7900*でRX 7900 XT / XTX両方をヒット可能",
    },
    "intel_cpu": {
        "manufacturer": "Intel",
        "patterns": [
            r"Core\s+(?:Ultra\s+)?\d{1,2}-\d{4,5}[A-Z]{0,2}",
            r"i[3579]-\d{4,5}[A-Z]{0,2}",
        ],
        "wildcard_hint": "i9-14900*でi9-14900K/KF/KS をまとめてヒット可能",
        "socket_hint": "Core Ultra 200S → LGA1851 / Core 13/14th Gen → LGA1700",
    },
    "amd_cpu": {
        "manufacturer": "AMD",
        "patterns": [
            r"Ryzen\s+[357]\s+\d{4}[A-Z]{0,2}",
            r"Ryzen\s+9\s+\d{4}[A-Z]{0,2}",
            r"Ryzen\s+Threadripper",
        ],
        "wildcard_hint": "Ryzen 9 7950*でRyzen 9 7950X/3D をヒット可能",
        "socket_hint": "Ryzen 7000/8000/9000 → AM5 / Ryzen 5000以前 → AM4",
    },
    "motherboard": {
        "manufacturer": "ASUS/MSI/GIGABYTE/ASRock",
        "patterns": [
            r"[A-Z]\d{3}[A-Z\-]+(?:PRO|PLUS|ULTRA|ELITE|APEX|HERO|FORMULA)?",
            r"MAG\s+[A-Z]\d{3}[A-Z\-]+",
            r"ROG\s+[A-Z]+\s+[A-Z]\d{3}[A-Z\-]+",
        ],
        "wildcard_hint": "Z790*で全Z790マザーをヒット。ROG STRIX Z790-Eは正式名称で検索推奨",
    },
    "psu": {
        "manufacturer": "Corsair/Seasonic/be quiet!/EVGA/Fractal/FSP/Antec",
        "patterns": [
            r"(?:RM|HX|AX|SF|MX|TX)\d{3,4}[xi]?",
            r"Focus\s+G[X]?\s+\d{3,4}",
            r"Ion\s+\+?\s*\d{3,4}",
        ],
        "wildcard_hint": "Corsair RM*でRM750/RM850/RM1000をまとめてヒット可能",
    },
    "cpu_cooler": {
        "manufacturer": "Noctua/be quiet!/Thermalright/Corsair/DeepCool/NZXT/ARCTIC",
        "patterns": [
            r"NH-[A-Z]\d+[A-Z]?(?:\s+SE-AM\d)?",        # Noctua: NH-D15, NH-U12S SE-AM4
            r"Dark\s+Rock\s+(?:Pro\s+)?(?:Elite\s+)?\d*", # be quiet!: Dark Rock Pro 5
            r"Pure\s+Rock\s+\d+",                          # be quiet!: Pure Rock 2
            r"Peerless\s+Assassin\s+\d+",                  # Thermalright: Peerless Assassin 120
            r"Frost\s+Commander\s+\d+",                    # Thermalright: Frost Commander 140
            r"iCUE\s+H\d+i(?:\s+Elite)?",                 # Corsair: iCUE H150i, iCUE H115i Elite
            r"AK[46]\d{2}(?:\s+ZERO)?",                   # DeepCool: AK620, AK400 ZERO
            r"Kraken\s+(?:[XZ]\d+|Elite\s+\d+)",          # NZXT: Kraken X63, Z73, Elite 360
            r"Freezer\s+\d+\s*(?:XT|A35)?",               # ARCTIC: Freezer 34 XT, Freezer A35
        ],
        "wildcard_hint": "NH-D*でNH-D14/D15両方をヒット、iCUE H*でH100i/H115i/H150i全対応",
    },
    "case": {
        "manufacturer": "Fractal Design/NZXT/Corsair/be quiet!/Lian Li/Antec",
        "patterns": [
            r"Define\s+[R]?\d+(?:\s+(?:Nano|Mini|XL))?",  # Fractal: Define 7, Define R6
            r"Meshify\s+[C2]?(?:\s+Compact)?",              # Fractal: Meshify 2, Meshify C
            r"North\s+(?:Charcoal|White|XL)?",              # Fractal: North, North XL
            r"Torrent\s+(?:Compact|Nano|RGB)?",             # Fractal: Torrent, Torrent Compact
            r"(?:NZXT\s+)?H[5-9]\d{2}(?:\s+(?:Elite|Flow|ATX))?",  # NZXT: H510, H710
            r"H[69]\s+(?:Elite|Flow|Mini)?",                # NZXT: H9 Elite, H6 Flow
            r"\b[45]000D(?:\s+AIRFLOW)?(?:\s+RGB)?",        # Corsair: 4000D AIRFLOW, 5000D RGB
            r"Pure\s+Base\s+\d+(?:\s+\w+)?",               # be quiet!: Pure Base 500DX
            r"(?:PC-)?O11\s+(?:Dynamic\s+)?(?:Air\s+)?(?:Evo|XL)?", # Lian Li: O11 Dynamic
            r"P\d{3}(?:\s+(?:Air|Black|White))?",           # Antec: P101 Silent
        ],
        "wildcard_hint": "Define*でFractal Defineシリーズ全般をヒット可能",
    },
    "memory": {
        "manufacturer": "Corsair/G.Skill/Kingston/Crucial/Team Group",
        "patterns": [
            r"Vengeance\s+(?:LPX\s+|DDR5\s+|RGB\s+)?DDR[45]-?\d{4}",  # Corsair Vengeance DDR4-3600
            r"Trident\s+Z[45]?\s*(?:RGB|Neo|Royal|5)?",                  # G.Skill Trident Z5 RGB
            r"Fury\s+(?:Beast|Renegade|Impact)\s+DDR[45]",               # Kingston Fury Beast DDR5
            r"Crucial\s+Pro\s+DDR[45]-?\d{4}",                           # Crucial Pro DDR5-5600
            r"\bDDR[45]-\d{4,5}\b",                                       # 汎用: DDR5-6000
            r"\b\d{2}GB\s+DDR[45]\b",                                    # 容量表記: 32GB DDR5
        ],
        "wildcard_hint": "DDR5-*で全DDR5メモリ速度帯をヒット可能",
    },
}


# ============================================================
# 互換性判定の重要制約パターン（LLMへの知識注入）
# ============================================================

CRITICAL_CONSTRAINTS = {
    "instant_ng": [
        {
            "id": "socket_mismatch",
            "description": "CPU と マザーボードのソケット不一致",
            "severity": "NG",
            "example": "Ryzen 7 7700X (AM5) + B650M (AM5) → OK / + B550 (AM4) → NG",
        },
        {
            "id": "ddr_mismatch",
            "description": "メモリの DDR 世代とマザーボードのスロット規格の不一致",
            "severity": "NG",
            "example": "DDR4-3600 + DDR5マザー → NG（物理的に挿さらない）",
        },
        {
            "id": "form_factor_mismatch",
            "description": "マザーボードのフォームファクターとケースが非対応",
            "severity": "NG",
            "example": "ATX マザー + mATX専用ケース → NG",
        },
        {
            "id": "gpu_too_long",
            "description": "GPU実装長 > ケースGPU最大長（マージン 0mm以下）",
            "severity": "NG",
            "example": "GPU 336mm + ケース最大310mm → NG",
        },
        {
            "id": "cooler_too_tall",
            "description": "CPUクーラー全高 > ケースCPUクーラー最大高",
            "severity": "NG",
            "example": "クーラー 165mm + ケース最大155mm → NG",
        },
        {
            "id": "psu_form_mismatch",
            "description": "電源規格（ATX/SFX/SFX-L）とケース対応電源規格の不一致",
            "severity": "NG",
            "example": "ATX電源 + SFX専用ケース（ブラケットなし）→ NG",
        },
    ],
    "warning": [
        {
            "id": "gpu_case_margin_low",
            "description": "GPU実装長とケースGPU最大長のマージンが 5〜15mm",
            "severity": "WARNING",
            "note": "組み立て時にケーブル取り回しで干渉する可能性あり",
        },
        {
            "id": "m2_pcie_conflict",
            "description": "M.2スロット使用によるPCIeレーン帯域低下または無効化",
            "severity": "WARNING",
            "note": "MBマニュアルの Bandwidth Sharing 表で具体的な影響範囲を確認",
        },
        {
            "id": "memory_cooler_clearance",
            "description": "メモリ全高とCPUクーラー側面クリアランスが 0〜5mm",
            "severity": "WARNING",
            "note": "ロープロファイルメモリへの変更またはクーラー変更を検討",
        },
        {
            "id": "12vhpwr_adapter",
            "description": "PCIe 5.0 GPUに 8pin変換アダプタを使用",
            "severity": "WARNING",
            "note": "メーカー非推奨。ネイティブ 12VHPWR対応電源への変更を強く推奨",
        },
        {
            "id": "power_margin_low",
            "description": "電源定格の使用率が 80〜90%（マージン 10〜20%）",
            "severity": "WARNING",
            "note": "高負荷時の安定動作のため 25%以上のマージン推奨",
        },
        {
            "id": "xmp_speed_exceed",
            "description": "メモリのXMP速度がMBの公式最大速度を超過",
            "severity": "WARNING",
            "note": "動作しない可能性あり。MB側のXMP対応最大速度を確認",
        },
    ],
}


# ============================================================
# BigQuery スキーマヒント（Planner への SQL 生成補助）
# ============================================================

BIGQUERY_SCHEMA_HINTS = {
    "tables": {
        "parts": "製品マスタ (part_id, category, manufacturer, model_name, series, sku)",
        "specs": "スペック (part_id, spec_key, spec_value, spec_unit)",
        "compatibility": "互換性テーブル (source_part_id, target_part_id, relation_type, note)",
        "manual_warnings": "PDFから抽出した注意事項 (part_id, section, severity, content, page_ref)",
    },
    "key_spec_columns": {
        "gpu": ["length_mm", "slot_count", "tdp_w", "pcie_version", "power_connector", "height_mm"],
        "motherboard": ["socket", "chipset", "form_factor", "ddr_gen", "m2_slots_json", "max_memory_speed_mt"],
        "case": ["max_gpu_length_mm", "max_cpu_cooler_height_mm", "psu_form_factor", "mb_form_factor_support"],
        "cpu_cooler": ["socket_support_json", "total_height_mm", "side_clearance_mm", "rated_tdp_w"],
        "psu": ["wattage", "form_factor", "depth_mm", "has_12vhpwr", "modular_type", "efficiency_rating"],
        "memory": ["ddr_gen", "speed_mt", "total_height_mm", "capacity_gb", "xmp_support", "expo_support"],
    },
    "sql_tips": [
        "スペック検索: SELECT spec_value FROM specs WHERE part_id = ? AND spec_key = 'length_mm'",
        "互換性チェック: SELECT * FROM compatibility WHERE source_part_id = ? AND relation_type = 'socket_conflict'",
        "警告取得: SELECT * FROM manual_warnings WHERE part_id = ? AND severity IN ('WARNING', 'NG') ORDER BY severity",
        "全スペック一括: SELECT spec_key, spec_value, spec_unit FROM specs WHERE part_id IN (?) ORDER BY spec_key",
    ],
}


def get_domain_prompt() -> str:
    """Planner に渡すドメインプロンプトを生成"""
    rules_text = []

    rules_text.append("## 自作PCカテゴリ別 互換性チェックルール\n")
    for cat_id, cat in CATEGORY_RULES.items():
        rules_text.append(f"### {cat['name']}")
        rules_text.append("必須確認:")
        for check in cat["required_checks"]:
            rules_text.append(f"  - {check}")
        rules_text.append("干渉パターン（PDFで必ず確認）:")
        for pat in cat["interference_patterns"]:
            rules_text.append(f"  ⚠ {pat}")
        rules_text.append("検索ヒント:")
        for hint in cat["search_hints"]:
            rules_text.append(f"  → {hint}")
        rules_text.append("")

    rules_text.append("## クエリパターン別 検索戦略\n")
    for pat_id, pat in QUERY_PATTERNS.items():
        rules_text.append(f"### [{pat_id}] {pat['pattern']}")
        rules_text.append(f"戦略: {pat['strategy'][:300]}...")
        rules_text.append(f"使用ツール: {', '.join(pat['tools'])}")
        rules_text.append("")

    rules_text.append("## 即NGパターン（1つでも該当したら NG 確定）\n")
    for constraint in CRITICAL_CONSTRAINTS["instant_ng"]:
        rules_text.append(f"- [{constraint['severity']}] {constraint['description']}")
        rules_text.append(f"  例: {constraint['example']}")
    rules_text.append("")

    rules_text.append("## WARNINGパターン（要注意・確認推奨）\n")
    for constraint in CRITICAL_CONSTRAINTS["warning"]:
        rules_text.append(f"- [{constraint['severity']}] {constraint['description']}")
        rules_text.append(f"  注意: {constraint['note']}")
    rules_text.append("")

    rules_text.append("## BigQuery スキーマ参照\n")
    rules_text.append("テーブル:")
    for tbl, desc in BIGQUERY_SCHEMA_HINTS["tables"].items():
        rules_text.append(f"  - {tbl}: {desc}")
    rules_text.append("SQLヒント:")
    for tip in BIGQUERY_SCHEMA_HINTS["sql_tips"]:
        rules_text.append(f"  - {tip}")

    return "\n".join(rules_text)
