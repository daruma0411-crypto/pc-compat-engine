"""
Steam PC スペック HTML パーサー（日英両対応）

Steam の pc_requirements.minimum / recommended は HTML 文字列で返る。
これを構造化 dict に変換する。パース失敗項目は None。
"""
import re
from bs4 import BeautifulSoup

# ラベルパターン（日英両対応）
_LABEL_MAP = [
    ('os',               re.compile(r'^OS$', re.IGNORECASE)),
    ('cpu',              re.compile(r'^(Processor|プロセッサー)$', re.IGNORECASE)),
    ('gpu',              re.compile(r'^(Graphics|グラフィックス)$', re.IGNORECASE)),
    ('ram',              re.compile(r'^(Memory|メモリ[ー]?)$', re.IGNORECASE)),
    ('storage',          re.compile(r'^(Storage|ストレージ)$', re.IGNORECASE)),
    ('directx',          re.compile(r'^DirectX$', re.IGNORECASE)),
    ('additional_notes', re.compile(r'^(Additional Notes|追記事項)$', re.IGNORECASE)),
]

_RAM_GB     = re.compile(r'(\d+)\s*GB', re.IGNORECASE)
_STORAGE_TB = re.compile(r'(\d+)\s*TB', re.IGNORECASE)
_STORAGE_GB = re.compile(r'(\d+)\s*GB', re.IGNORECASE)
_DX_VER     = re.compile(r'(\d+)')
_SSD        = re.compile(r'SSD', re.IGNORECASE)
_HDD        = re.compile(r'HDD', re.IGNORECASE)
_ALT_SEP    = re.compile(r'\s+or\s+|または|／|\s*/\s*', re.IGNORECASE)


def _split_alternatives(text: str) -> list:
    """CPU/GPU の候補を "or" や "／" で分割してリスト化"""
    parts = _ALT_SEP.split(text)
    return [p.strip() for p in parts if p.strip()]


def _classify_label(label: str) -> str | None:
    for key, pattern in _LABEL_MAP:
        if pattern.match(label):
            return key
    return None


def parse_spec_html(html: str) -> dict:
    """
    Steam の pc_requirements HTML 文字列を構造化 dict に変換。

    Returns:
        {
          'os': str | None,
          'cpu': list[str] | None,
          'gpu': list[str] | None,
          'ram_gb': int | None,
          'storage_gb': int | None,
          'storage_type': 'SSD' | 'HDD' | None,
          'directx': str | None,
          'additional_notes': str | None,
        }
    """
    if not html:
        return {}

    soup = BeautifulSoup(html, 'html.parser')
    result = {
        'os': None, 'cpu': None, 'gpu': None,
        'ram_gb': None, 'storage_gb': None, 'storage_type': None,
        'directx': None, 'additional_notes': None,
    }

    for li in soup.find_all('li'):
        strong = li.find('strong')
        if not strong:
            continue

        label = strong.get_text(strip=True).rstrip(':').strip()
        strong.extract()
        value = li.get_text(separator=' ', strip=True)
        if not value:
            continue

        key = _classify_label(label)
        if key == 'os':
            result['os'] = value
        elif key == 'cpu':
            result['cpu'] = _split_alternatives(value)
        elif key == 'gpu':
            result['gpu'] = _split_alternatives(value)
        elif key == 'ram':
            m = _RAM_GB.search(value)
            result['ram_gb'] = int(m.group(1)) if m else None
        elif key == 'storage':
            tb_m = _STORAGE_TB.search(value)
            gb_m = _STORAGE_GB.search(value)
            if tb_m:
                result['storage_gb'] = int(tb_m.group(1)) * 1024
            elif gb_m:
                result['storage_gb'] = int(gb_m.group(1))
            if _SSD.search(value):
                result['storage_type'] = 'SSD'
            elif _HDD.search(value):
                result['storage_type'] = 'HDD'
        elif key == 'directx':
            m = _DX_VER.search(value)
            result['directx'] = m.group(1) if m else value
        elif key == 'additional_notes':
            result['additional_notes'] = value

    return result
