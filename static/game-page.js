const GPU_SCORES = {"GTX 1050 Ti": 8, "GTX 1060": 12, "GTX 1070": 18, "GTX 1070 Ti": 20, "GTX 1080": 24, "GTX 1080 Ti": 28, "RTX 2060": 30, "RTX 2060 Super": 34, "RTX 2070": 38, "RTX 2070 Super": 42, "RTX 2080": 46, "RTX 2080 Super": 50, "RTX 2080 Ti": 56, "RTX 3050": 32, "RTX 3060": 40, "RTX 3060 Ti": 48, "RTX 3070": 56, "RTX 3070 Ti": 60, "RTX 3080": 68, "RTX 3080 Ti": 74, "RTX 3090": 80, "RTX 4050": 36, "RTX 4060": 50, "RTX 4060 Ti": 58, "RTX 4070": 72, "RTX 4070 Super": 78, "RTX 4070 Ti": 84, "RTX 4080": 92, "RTX 4090": 100, "RTX 5060": 55, "RTX 5070": 80, "RTX 5080": 95, "RTX 5090": 120, "RX 580": 18, "RX 590": 20, "RX 5700": 36, "RX 5700 XT": 42, "RX 6600": 44, "RX 6700 XT": 60, "RX 6800": 72, "RX 6800 XT": 80, "RX 6900 XT": 88, "RX 7600": 52, "RX 7700 XT": 68, "RX 7800 XT": 76, "RX 7900 XTX": 96, "RX 9070": 82, "RX 9070 XT": 90};
const REC_SCORE = 38;
const REC_RAM = 32;

function getGpuScore(inputGpu) {
  const lower = inputGpu.toLowerCase();
  // 完全一致
  for (const [name, score] of Object.entries(GPU_SCORES)) {
    if (name.toLowerCase() === lower) return { name, score };
  }
  // 部分一致（長い名前優先）
  let best = null;
  for (const [name, score] of Object.entries(GPU_SCORES)) {
    if (lower.includes(name.toLowerCase()) || name.toLowerCase().includes(lower)) {
      if (!best || name.length > best.name.length) best = { name, score };
    }
  }
  return best;
}

function runSpecCheck() {
  const gpuInput = document.getElementById('sc-gpu').value.trim();
  const ram = parseInt(document.getElementById('sc-ram').value) || 8;
  const resultDiv = document.getElementById('sc-result');

  if (!gpuInput) {
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<p class="calc-warn">⚠️ GPUを入力してください</p>';
    return;
  }

  const gpuData = getGpuScore(gpuInput);
  if (!gpuData) {
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `<p class="calc-warn">⚠️ "${gpuInput}" のデータが見つかりません。モデル名を確認してください（例: RTX 3060）</p>`;
    return;
  }

  const ratio = gpuData.score / REC_SCORE;
  const ramOk = ram >= REC_RAM;
  let verdict, verdictColor, fps, advice;

  if (ratio >= 1.2 && ramOk) {
    verdict = '✅ 快適に動作します'; verdictColor = '#2e7d32';
    fps = Math.round(90 * ratio); advice = '高設定・1080pで' + Math.min(fps, 240) + 'fps以上が期待できます。';
  } else if (ratio >= 0.8) {
    verdict = '⚠️ 動作しますが設定次第'; verdictColor = '#F57F17';
    fps = Math.round(60 * ratio); advice = '1080p中設定で' + Math.min(fps, 120) + 'fps前後が目安です。';
  } else {
    verdict = '❌ スペック不足の可能性'; verdictColor = '#c62828';
    fps = Math.round(40 * ratio); advice = '低設定・30fps前後になる可能性があります。GPUのアップグレードを推奨します。';
  }

  const ramWarn = !ramOk ? `<p class="calc-warn" style="margin-top:8px;">⚠️ RAM ${ram}GBは推奨(${REC_RAM}GB)を下回っています</p>` : '';

  resultDiv.style.display = 'block';
  resultDiv.innerHTML = `
    <div class="calc-verdict" style="border-color:${verdictColor};">
      <p class="calc-verdict-text" style="color:${verdictColor};">${verdict}</p>
      <p>検出GPU: <strong>${gpuData.name}</strong>（性能スコア: ${gpuData.score}/100）</p>
      <p>推奨スペック比: <strong>${Math.round(ratio*100)}%</strong></p>
      <p class="calc-perf">🎮 ${advice}</p>
      ${ramWarn}
      <div class="consult-cta">
        <a href="https://pc-jisaku.com/?game=Palworld&gpu=${encodeURIComponent(gpuData.name)}&ram=${ram}" class="consult-button">💬 この診断結果についてAIに相談する →</a>
        <p class="consult-note">より詳しいアドバイスをAIが提供します</p>
      </div>
    </div>`;
  // sessionStorageにコンテキスト保存
  try {
    sessionStorage.setItem('diagnosisContext', JSON.stringify({
      game: 'Palworld', gpu: gpuData.name, ram: ram, score: gpuData.score, ratio: Math.round(ratio*100), verdict: verdict, timestamp: Date.now()
    }));
  } catch(e) {}
  resultDiv.scrollIntoView({behavior: 'smooth', block: 'center'});
}

// GA4: 購入クリックトラッキング
document.addEventListener('click', function(e) {
  var link = e.target.closest('.buy-amz, .buy-rak, .btn-buy-amazon');
  if (link && typeof gtag === 'function') {
    gtag('event', 'purchase_click', {
      link_type: link.classList.contains('buy-rak') ? 'rakuten' : 'amazon',
      link_url: link.href,
      page_path: location.pathname,
      value: 30, currency: 'JPY'
    });
  }
});

// お気に入り機能
var FAV_KEY = 'pccompat_favs';
var GAME_SLUG = 'palworld';
var GAME_NAME = 'Palworld';

function getFavs() {
  try { return JSON.parse(localStorage.getItem(FAV_KEY)) || []; } catch(e) { return []; }
}
function saveFavs(favs) {
  try { localStorage.setItem(FAV_KEY, JSON.stringify(favs.slice(0, 20))); } catch(e) {}
}
function isFav() {
  return getFavs().some(function(f) { return f.slug === GAME_SLUG; });
}
function updateFavBtn() {
  var btn = document.getElementById('btn-fav');
  if (!btn) return;
  if (isFav()) {
    btn.textContent = '⭐ お気に入り済み';
    btn.classList.add('btn-fav-active');
  } else {
    btn.textContent = '⭐ お気に入りに追加';
    btn.classList.remove('btn-fav-active');
  }
}
function toggleFavorite() {
  var favs = getFavs();
  var idx = favs.findIndex(function(f) { return f.slug === GAME_SLUG; });
  if (idx >= 0) {
    favs.splice(idx, 1);
  } else {
    favs.unshift({ slug: GAME_SLUG, name: GAME_NAME });
    if (typeof gtag === 'function') {
      gtag('event', 'add_to_favorites', { game_name: GAME_NAME, page_path: location.pathname });
    }
  }
  saveFavs(favs);
  updateFavBtn();
}
updateFavBtn();