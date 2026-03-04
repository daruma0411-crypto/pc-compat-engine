#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CSS/JSの簡易ミニファイ"""
import re
from pathlib import Path

def minify_css(css):
    css = re.sub(r'/\*[\s\S]*?\*/', '', css)
    css = re.sub(r'\s+', ' ', css)
    css = re.sub(r'\s*([{};:,])\s*', r'\1', css)
    return css.strip()

def minify_js(js):
    js = re.sub(r'//.*?$', '', js, flags=re.MULTILINE)
    js = re.sub(r'/\*[\s\S]*?\*/', '', js)
    js = re.sub(r'\n\s*\n', '\n', js)
    return js

base = Path(__file__).resolve().parent.parent / 'static'

# CSS
css_path = base / 'style.css'
if css_path.exists():
    original = css_path.read_text(encoding='utf-8')
    minified = minify_css(original)
    (base / 'style.min.css').write_text(minified, encoding='utf-8')
    print(f"CSS: {len(original)} -> {len(minified)} bytes ({100 - len(minified) / len(original) * 100:.1f}% reduction)")

# JS files
for js_path in sorted(base.glob('*.js')):
    if js_path.stem.endswith('.min'):
        continue
    original = js_path.read_text(encoding='utf-8')
    minified = minify_js(original)
    out_path = base / f"{js_path.stem}.min.js"
    out_path.write_text(minified, encoding='utf-8')
    print(f"{js_path.name}: {len(original)} -> {len(minified)} bytes ({100 - len(minified) / len(original) * 100:.1f}% reduction)")
