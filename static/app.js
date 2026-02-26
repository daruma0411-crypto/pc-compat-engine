  // ─── 定数 ──────────────────────────────────────────────────────────────
  const VERDICT_MAP = {
    OK:      { label: '互換性OK',  sub: 'すべてのチェックを通過しました',            icon: '✅', cls: 'OK'      },
    WARNING: { label: '要注意',    sub: '一部に互換性リスクがあります',               icon: '⚠️', cls: 'WARNING' },
    NG:      { label: '非互換',    sub: '組み立て不可能な組み合わせが含まれています', icon: '❌', cls: 'NG'      },
    UNKNOWN: { label: '判定不能',  sub: 'スペック情報が不足しています',               icon: '❓', cls: 'UNKNOWN' },
  };
  const STATUS_LABEL = { OK: 'OK', WARNING: 'WARN', NG: 'NG', UNKNOWN: '?' };

  // ─── 状態管理 ──────────────────────────────────────────────────────────
  let history = [];
  let sending = false;
  let lastDiagnosis = null;
  let gameMode = false;
  let historyFirstSaved = false;
  let confirmedParts = [];  // [{name: string, category: string, source: 'user_specified'|'ai_accepted'|'ai_pending'}]
  let budgetYen = null;     // ユーザーが指定した予算（数値）

  // ─── localStorage 履歴 ─────────────────────────────────────────────────
  const HISTORY_KEY = 'pc_compat_history';
  const MAX_HISTORY = 20;

  function loadStoredHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
    catch { return []; }
  }

  function saveToHistory(title, mode) {
    if (historyFirstSaved) return;
    historyFirstSaved = true;
    const items = loadStoredHistory();
    const shortTitle = title.slice(0, 40);
    // 直近エントリと同じ内容なら重複保存しない
    if (items.length && items[0].title === shortTitle && items[0].mode === mode) return;
    items.unshift({
      id: Date.now(),
      title: shortTitle,
      date: new Date().toLocaleDateString('ja-JP', { month: 'numeric', day: 'numeric' }),
      mode,
    });
    localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, MAX_HISTORY)));
  }

  function renderDrawer() {
    const list = document.getElementById('drawer-list');
    const items = loadStoredHistory();
    if (!items.length) {
      list.innerHTML = '<div class="drawer-empty">まだ履歴がありません</div>';
      return;
    }
    const rows = items.map(it =>
      '<div class="drawer-item">' +
        '<span class="drawer-item-icon">' + (it.mode === 'game' ? '🎮' : '🔧') + '</span>' +
        '<span class="drawer-item-title">' + escHtml(it.title) + '</span>' +
        '<span class="drawer-item-date">'  + escHtml(it.date)  + '</span>' +
      '</div>'
    ).join('');
    list.innerHTML = '<div class="drawer-section-title">最近の履歴</div>' + rows;
  }

  function toggleDrawer() {
    const overlay = document.getElementById('drawer-overlay');
    overlay.classList.toggle('open');
    if (overlay.classList.contains('open')) renderDrawer();
  }

  function closeDrawer(e) {
    if (e.target === e.currentTarget) toggleDrawer();
  }

  function newChat() {
    toggleDrawer();
    setTimeout(() => location.reload(), 200);
  }

  // ─── 初期メッセージ ─────────────────────────────────────────────────────
  window.addEventListener('DOMContentLoaded', () => {
    const cardsHtml =
      '<div class="mode-cards">' +
        '<div class="mode-card" onclick="selectMode(\'game\')">' +
          '<span class="mode-card-icon">🎮</span>ゲームを快適に遊びたい' +
        '</div>' +
        '<div class="mode-card" onclick="selectMode(\'compat\')">' +
          '<span class="mode-card-icon">🔧</span>パーツの互換性を確認' +
        '</div>' +
      '</div>';
    appendAIBubble('まず何をしたいか教えてください', cardsHtml);
    adjustHeight();
  });

  function selectMode(mode) {
    confirmedParts = [];  // モード切替時: 確定パーツ（全状態）をリセット
    document.querySelectorAll('.mode-card').forEach(c => {
      c.style.pointerEvents = 'none';
      c.style.opacity = '0.4';
    });
    if (mode === 'game') {
      gameMode = true;
      document.getElementById('chat-input').placeholder = '例: モンハンワイルズを60fpsで遊びたい。予算15万';
      appendAIBubble('🎮 どのゲームを、どんな目標でプレイしたいですか？\n予算も教えていただけると、より正確な構成を提案できます。\n\n例: モンハンワイルズを60fpsで遊びたい。予算15万円');
    } else {
      gameMode = false;
      document.getElementById('chat-input').placeholder = '例: RTX 4070をLancool 216に入れたい';
      appendAIBubble('どんな組み合わせを確認したいですか？\n例: RTX 4070をLancool 216に入れたい');
    }
    updateModeIndicator();
  }

  function switchMode() {
    gameMode = !gameMode;
    if (!gameMode) {
      // 手動切り替え（引き渡しボタン経由でない）→ confirmedParts をリセット
      // ※ transferToCompatCheck() 経由の場合は先に confirmedParts が上書きされているため問題なし
      confirmedParts = [];
    }
    updateModeIndicator();
    if (gameMode) {
      document.getElementById('chat-input').placeholder = '例: モンハンワイルズを60fpsで遊びたい。予算15万';
      appendAIBubble('🎮 ゲームモードに切り替えました。\nどのゲームを、どんな目標でプレイしたいですか？予算も教えてください。');
    } else {
      document.getElementById('chat-input').placeholder = '例: RTX 4070をLancool 216に入れたい';
      appendAIBubble('🔧 互換チェックモードに切り替えました。\nどんな組み合わせを確認したいですか？');
    }
  }

  // ─── ゲーム推奨構成 → 互換チェックへの引き渡し ───────────────────────────
  function transferToCompatCheck(build) {
    // ユーザーが「この構成で互換チェック」ボタンを押した = 推奨構成の承認とみなす
    // → ai_accepted として登録（変更提案なし、ケースや追加パーツのみ補完対象）
    confirmedParts = build.map(b => ({ name: b.name, category: (b.category || '').toLowerCase(), source: 'ai_accepted' }));
    // ゲームモードを解除（switchMode より先に confirmedParts をセットするため手動でフラグ変更）
    gameMode = false;
    updateModeIndicator();
    document.getElementById('chat-input').placeholder = '例: RTX 4070をLancool 216に入れたい';
    const partNames = build.map(b => b.name).join('、');
    appendAIBubble(
      '🔧 推奨構成を引き継ぎました。\n' +
      '確定パーツ: ' + partNames + '\n\n' +
      'ケースや追加パーツを入力してください。\n例: Lancool 216に入れたい'
    );
    scrollBottom();
  }

  function updateModeIndicator() {
    const btn = document.getElementById('btn-mode-switch');
    if (!btn) return;
    btn.style.display = (gameMode !== null && gameMode !== undefined) ? '' : 'none';
    if (gameMode) {
      btn.textContent = '🔧 互換チェックへ';
      btn.title = '互換チェックモードに切り替え';
    } else {
      btn.textContent = '🎮 ゲームモードへ';
      btn.title = 'ゲームモードに切り替え';
    }
  }

  // ─── イベント ──────────────────────────────────────────────────────────
  document.getElementById('btn-send').addEventListener('click', sendMessage);
  document.getElementById('chat-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  document.getElementById('chat-input').addEventListener('input', adjustHeight);

  // ─── メッセージ送信 ────────────────────────────────────────────────────
  async function sendMessage() {
    if (sending) return;
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    // ── ai_pending → ai_accepted 昇格（ユーザーが次のメッセージを送った = 前の提案に異議なし）
    confirmedParts = confirmedParts.map(p =>
      p.source === 'ai_pending' ? { ...p, source: 'ai_accepted' } : p
    );

    // 最初のユーザーメッセージを localStorage に保存
    saveToHistory(msg, gameMode ? 'game' : 'compat');

    appendUserBubble(msg);
    history.push({ role: 'user', content: msg });
    input.value = '';
    adjustHeight();
    setSending(true);
    const typingEl = appendTyping();

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 65000);

    try {
      const endpoint = gameMode ? '/api/recommend' : '/api/chat';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // バックエンドには名前の配列で渡す（後方互換性を維持）
        body: JSON.stringify({ message: msg, history: history.slice(-10), confirmed_parts: confirmedParts.map(p => p.name) }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'HTTP ' + res.status);
      }
      const data = await res.json();
      typingEl.remove();
      history.push({ role: 'assistant', content: data.reply || '' });

      if (data.type === 'recommendation' || data.type === 'suggestion') {
        // confirmed=true パーツ → ai_accepted（ユーザー指定として扱う）
        // confirmed=false パーツ → ai_pending（次のメッセージ送信時に昇格）
        const newParts = (data.recommended_build || []).map(b => ({
          name: b.name,
          category: (b.category || '').toLowerCase(),
          source: b.confirmed ? 'ai_accepted' : 'ai_pending',
        }));
        if (newParts.length > 0) {
          // 既存の user_specified は保持し、AI提案パーツを追加・更新
          const userSpecified = confirmedParts.filter(p => p.source === 'user_specified');
          const merged = [...userSpecified];
          for (const np of newParts) {
            if (!merged.some(p => p.name === np.name)) merged.push(np);
          }
          confirmedParts = merged;
        }
        appendRecommendationMessage(data);
      } else if (data.type === 'diagnosis') {
        lastDiagnosis = { parts: data.parts, diagnosis: data.diagnosis };
        // 診断時: バックエンドが返した user_specified_parts を source: 'user_specified' で登録
        // parts_with_category を使ってcategoryも付与
        const partsWithCat = {};
        for (const pc of (data.parts_with_category || [])) {
          partsWithCat[pc.name] = pc.category || '';
        }
        const userSpecifiedNames = data.user_specified_parts || data.parts || [];
        for (const name of userSpecifiedNames) {
          if (!confirmedParts.some(p => p.name === name)) {
            confirmedParts.push({ name, category: partsWithCat[name] || '', source: 'user_specified' });
          }
        }
        appendDiagnosisMessage(data);
      } else {
        appendAIBubble(data.reply || '少し詳しく教えてください。');
      }
    } catch (e) {
      clearTimeout(timer);
      typingEl.remove();
      if (e.name === 'AbortError') {
        appendAIBubble('⏱️ サーバーが起動中のため時間がかかっています。\nもう一度送信してください（2回目以降は速くなります）。');
      } else {
        appendAIBubble('⚠️ エラーが発生しました: ' + e.message);
      }
    } finally {
      setSending(false);
    }
  }

  // ─── チャット要素の追加 ────────────────────────────────────────────────
  function appendUserBubble(text) {
    const wrap = mkEl('div', 'msg user');
    wrap.innerHTML =
      '<div class="msg-avatar">👤</div>' +
      '<div class="msg-bubble">' + escHtml(text) + '</div>';
    chat().appendChild(wrap);
    scrollBottom();
  }

  function appendAIBubble(text, extraHtml) {
    const wrap = mkEl('div', 'msg ai');
    const inner = mkEl('div');
    const bubble = mkEl('div', 'msg-bubble');
    bubble.innerHTML = text.replace(/\n/g, '<br>');
    if (extraHtml) bubble.insertAdjacentHTML('beforeend', extraHtml);
    inner.appendChild(bubble);
    wrap.innerHTML = '<div class="msg-avatar">🤖</div>';
    wrap.appendChild(inner);
    chat().appendChild(wrap);
    scrollBottom();
    return wrap;
  }

  function appendTyping() {
    const wrap = mkEl('div', 'msg ai');
    wrap.innerHTML =
      '<div class="msg-avatar">🤖</div>' +
      '<div class="msg-bubble">' +
      '<div class="typing-indicator"><span></span><span></span><span></span></div>' +
      '</div>';
    chat().appendChild(wrap);
    scrollBottom();
    return wrap;
  }

  // ─── 診断結果メッセージ ────────────────────────────────────────────────
  function appendDiagnosisMessage(data) {
    const { reply, parts, diagnosis } = data;
    const verdict = diagnosis.verdict || 'UNKNOWN';
    const checks  = diagnosis.checks  || [];
    const summary = diagnosis.summary || '';
    const vm = VERDICT_MAP[verdict] || VERDICT_MAP.UNKNOWN;

    const checksHtml = checks.map(c => {
      const st = c.status || 'UNKNOWN';
      return '<div class="check-item">' +
        '<span class="check-badge badge-' + st + '">' + (STATUS_LABEL[st] || st) + '</span>' +
        '<div>' +
        '<div class="check-name">'   + escHtml(c.item   || '') + '</div>' +
        '<div class="check-detail">' + escHtml(c.detail || '') + '</div>' +
        '</div>' +
        '</div>';
    }).join('');

    // GPU/ケースに直接関係するチェックがNG/WARNINGの場合のみ代替案を表示
    const gpuNgWarn = checks.some(c =>
      (c.status === 'NG' || c.status === 'WARNING') &&
      /gpu|GPU|グラフィック|干渉マージン/i.test(c.item)
    );
    const caseNgWarn = checks.some(c =>
      (c.status === 'NG' || c.status === 'WARNING') &&
      /ケース|case|フォームファクター/i.test(c.item)
    );

    const diagHtml =
      '<div class="diag-card">' +
        '<div class="verdict-banner ' + vm.cls + '">' +
          '<span class="verdict-icon">' + vm.icon + '</span>' +
          '<div class="verdict-text">' +
            '<h2 class="' + vm.cls + '">' + vm.label + '</h2>' +
            '<p>' + escHtml(summary || vm.sub) + '</p>' +
          '</div>' +
        '</div>' +
        '<div class="checks-list">' + checksHtml + '</div>' +
      '</div>';

    appendAIBubble(
      escHtml(reply || parts.length + '件のパーツを診断しました。'),
      diagHtml
    );

    if (gpuNgWarn) fetchAlternatives('gpu');
    if (caseNgWarn) fetchAlternatives('case');
  }

  // ─── 代替品取得 ────────────────────────────────────────────────────────
  async function fetchAlternatives(category) {
    if (!lastDiagnosis) return;
    const { parts } = lastDiagnosis;

    const gpuName  = parts.find(p => /rtx|gtx|rx\s|arc\s|radeon|geforce/i.test(p))
                  || parts[0] || '';
    const caseName = parts.find(p =>
                       /lancool|lian.?li|nzxt|fractal|cooler.?master|corsair|phanteks|be.quiet|silencio|meshify|define|h[0-9]/i.test(p))
                  || parts[1] || '';

    const params = new URLSearchParams({ category });
    if (category === 'gpu'  && caseName) params.set('case_name', caseName);
    if (category === 'case' && gpuName)  params.set('gpu_name', gpuName);

    const typingEl = appendTyping();
    try {
      const res = await fetch('/api/alternatives?' + params.toString());
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      typingEl.remove();
      renderAlternatives(category, data.alternatives || []);
    } catch (e) {
      typingEl.remove();
      appendAIBubble('⚠️ 代替品の取得に失敗しました: ' + e.message);
    }
  }

  function renderAlternatives(category, items) {
    const label = category === 'gpu' ? 'GPU変更案' : 'ケース変更案';
    if (!items.length) {
      appendAIBubble('該当する' + (category === 'gpu' ? 'GPU' : 'ケース') + 'が見つかりませんでした。');
      return;
    }
    const cardsHtml = items.map(it => {
      const specs    = it.specs || {};
      const specStr  = buildSpecStr(category, specs);
      const amazonUrl  = it.amazon_url  || buildAmazonUrl(it.name);
      const rakutenUrl = it.rakuten_url || buildRakutenUrl(it.name);
      return '<div class="alt-product">' +
        '<div class="alt-name">'  + escHtml(it.name || '') + '</div>' +
        '<div class="alt-specs">' + escHtml(specStr)       + '</div>' +
        '<div class="alt-links">' +
          '<a class="buy-btn buy-btn-amazon"  href="' + escHtml(amazonUrl)  + '" target="_blank" rel="noopener">🛒 Amazon</a>' +
          '<a class="buy-btn buy-btn-rakuten" href="' + escHtml(rakutenUrl) + '" target="_blank" rel="noopener">🛍 楽天</a>' +
        '</div>' +
        '</div>';
    }).join('');

    const altWrap = appendAIBubble(
      '💡 代わりにこれはどうですか？ ' + label + '（' + items.length + '件）',
      '<div class="alt-grid">' + cardsHtml + '</div>'
    );
    setTimeout(() => {
      if (altWrap) altWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 150);
  }

  function buildSpecStr(category, specs) {
    const parts = [];
    if (category === 'gpu') {
      if (specs.length_mm)       parts.push(specs.length_mm + 'mm');
      if (specs.tdp_w)           parts.push(specs.tdp_w + 'W');
      if (specs.power_connector) parts.push(specs.power_connector);
    } else {
      if (specs.max_gpu_length_mm) parts.push('GPU最大 ' + specs.max_gpu_length_mm + 'mm');
      if (specs.form_factor)       parts.push(specs.form_factor);
    }
    return parts.join(' / ');
  }

  // ─── カードサイズ・アイコンヘルパー ──────────────────────────────────
  function getBuildItemSizeClass(category) {
    const cat = (category || '').toUpperCase();
    if (['GPU', 'CPU', 'CASE'].includes(cat)) return 'build-item--lg';
    if (['RAM', 'MB'].includes(cat)) return 'build-item--md';
    if (cat === 'PSU') return 'build-item--sm';
    return '';
  }

  function getCategoryIcon(category) {
    const icons = { GPU: '🎮', CPU: '⚡', RAM: '💾', MB: '🔌', PSU: '🔋', CASE: '🖥️' };
    return icons[(category || '').toUpperCase()] || '📦';
  }

  // ─── 構成サマリーカード ─────────────────────────────────────────────────
  const CATEGORY_ORDER = ['GPU', 'CPU', 'RAM', 'MB', 'PSU', 'CASE'];

  // 日本語カテゴリ名 → 英語正規化（バックエンドが日本語で返す場合に対応）
  function normalizeCat(cat) {
    const map = {
      'ケース': 'CASE', '電源': 'PSU', 'マザーボード': 'MB',
      'CPUクーラー': 'COOLER', 'cpuクーラー': 'COOLER',
      'MOTHERBOARD': 'MB', 'POWER_SUPPLY': 'PSU',
    };
    const trimmed = (cat || '').trim();
    return map[trimmed] || map[trimmed.toUpperCase()] || trimmed.toUpperCase();
  }

  function renderSummaryCard(build, gameName, budget) {
    // 全カテゴリを常に表示（未選択はグレーアウト）
    const catMap = {};
    for (const item of build) {
      const cat = normalizeCat(item.category);
      catMap[cat] = item;
    }

    const rowsHtml = CATEGORY_ORDER.map(cat => {
      const item = catMap[cat];
      const hasItem = !!item;
      let priceStr = '—';
      if (hasItem) {
        if (item.price_min || item.price_low) {
          priceStr = '¥' + Number(item.price_min || item.price_low).toLocaleString();
        } else if (item.price_range && item.price_range !== '') {
          priceStr = item.price_range;
        } else if (item.name) {
          priceStr = '価格調査中';
        }
      }
      const statusIcon = hasItem ? '✅' : '⚠️';
      return '<div class="summary-row">' +
        '<span class="summary-cat">' + cat + '</span>' +
        '<span class="summary-name' + (hasItem ? '' : ' summary-name--empty') + '">' +
          escHtml(hasItem ? (item.name || '') : '（未選択）') +
        '</span>' +
        '<span class="summary-price">' + escHtml(priceStr) + '</span>' +
        '<span class="summary-status">' + statusIcon + '</span>' +
      '</div>';
    }).join('');

    // 合計金額計算（price_min 優先、なければ price_low）
    const totalMin = build.reduce((sum, it) => sum + (it.price_min || it.price_low || 0), 0);
    const confirmedCount = CATEGORY_ORDER.filter(c => catMap[c]).length;
    const totalStr = totalMin > 0 ? '¥' + totalMin.toLocaleString() : '—';

    // 予算差額
    let budgetLine = '';
    if (budget && totalMin > 0) {
      const diff = totalMin - budget;
      if (diff > 5000) {
        budgetLine = '<div class="summary-budget-warn">⚠️ 予算を約¥' + diff.toLocaleString() + ' 超過しています</div>';
      } else if (diff < -5000) {
        budgetLine = '<div class="summary-budget-ok">✅ 予算内（余裕 ¥' + Math.abs(diff).toLocaleString() + '）</div>';
      } else {
        budgetLine = '<div class="summary-budget-ok">✅ ほぼ予算通り</div>';
      }
    }

    const html = '<div class="summary-card">' +
      '<div class="summary-title">📋 構成サマリー</div>' +
      '<div class="summary-rows">' + rowsHtml + '</div>' +
      '<div class="summary-footer">' +
        '<span class="summary-total-label">合計: ' + escHtml(totalStr) + '</span>' +
        (budget ? '<span class="summary-budget-label">予算: ¥' + Number(budget).toLocaleString() + '</span>' : '') +
        '<span class="summary-count">' + confirmedCount + '/6 パーツ確定</span>' +
      '</div>' +
      budgetLine +
    '</div>';

    const cardWrap = mkEl('div', 'build-card-wrap');
    cardWrap.innerHTML = html;
    chat().appendChild(cardWrap);
    scrollBottom();
  }

  // ─── ゲームモード 推奨構成メッセージ ──────────────────────────────────
  function appendRecommendationMessage(data) {
    const game  = data.game  || {};
    const build = data.recommended_build || [];
    const total = data.total_estimate || '';
    const tip   = data.tip   || '';
    const reply = data.reply || '';

    // 予算を更新（バックエンドが返した budget_yen を優先）
    if (data.budget_yen) budgetYen = data.budget_yen;

    // 構成サマリーカードを先に表示
    if (build && build.length > 0) {
      renderSummaryCard(build, game.name || '', budgetYen);
    }

    const itemsHtml = build.map(item => {
      const amazonUrl  = item.amazon_url  || buildAmazonUrl(item.name || '');
      const rakutenUrl = item.rakuten_url || buildRakutenUrl(item.name || '');
      return '<div class="build-item ' + getBuildItemSizeClass(item.category) + '">' +
        '<div class="build-item-header">' +
          '<span class="build-category" data-cat="' + escHtml((item.category || '').toUpperCase()) + '">' + escHtml(item.category || '') + '</span>' +
          (item.image_url
            ? '<img class="build-thumb" src="' + escHtml(item.image_url) + '" alt="" loading="lazy" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">' +
              '<div class="build-thumb-icon" style="display:none">' + getCategoryIcon(item.category) + '</div>'
            : '<div class="build-thumb-icon">' + getCategoryIcon(item.category) + '</div>') +
          '<span class="build-name">'     + escHtml(item.name     || '') + '</span>' +
        '</div>' +
        '<div class="build-reason">' + escHtml(item.reason     || '') + '</div>' +
        '<div class="build-links">' +
          '<a class="buy-btn buy-btn-amazon"  href="' + escHtml(amazonUrl)  + '" target="_blank" rel="noopener">🛒 Amazon</a>' +
          '<a class="buy-btn buy-btn-rakuten" href="' + escHtml(rakutenUrl) + '" target="_blank" rel="noopener">🛍 楽天</a>' +
        '</div>' +
        '</div>';
    }).join('');

    const totalHtml = total
      ? '<div class="build-total">💰 予算目安: ' + escHtml(total) + '<span class="build-total-note">※実勢価格はAmazon/楽天でご確認ください</span></div>'
      : '';
    const tipHtml = tip
      ? '<div class="build-tip">💡 ' + escHtml(tip) + '</div>'
      : '';

    const scores    = data.radar_scores;
    const reqScores = data.game_req_scores || null;
    const radarId = 'radar-' + Date.now();
    const radarHtml = (scores && gameMode)
      ? '<div class="radar-wrap">' +
          '<div class="radar-title">性能バランス</div>' +
          '<canvas id="' + radarId + '" width="260" height="260"></canvas>' +
        '</div>'
      : '';

    // ゲームモード時のみ「互換チェックへ引き継ぐ」ボタンを表示
    const transferBtnId = 'btn-transfer-' + Date.now();
    const transferBtnHtml = gameMode
      ? '<button class="btn-transfer-compat" id="' + transferBtnId + '">🔧 この構成で互換チェックを始める</button>'
      : '';

    const cardHtml =
      '<div class="build-row">' +
        '<div class="build-card">' +
          '<div class="build-game-title">' + (game.appid === null && game.name === '推奨構成' ? '🔧 ' : '🎮 ') + escHtml(game.name || 'ゲーム') + (game.appid === null && game.name === '推奨構成' ? '' : ' 推奨構成') + '</div>' +
          '<div class="build-items">' + itemsHtml + '</div>' +
          totalHtml + tipHtml +
          transferBtnHtml +
        '</div>' +
        radarHtml +
      '</div>';

    appendAIBubble(reply || '');
    const cardWrap = mkEl('div', 'build-card-wrap');
    cardWrap.innerHTML = cardHtml;
    chat().appendChild(cardWrap);
    scrollBottom();
    setTimeout(() => {
      if (scores) renderRadarChart(radarId, scores, reqScores, game.name || '');
      // 引き渡しボタンにイベントを設定（build をクロージャで保持）
      if (gameMode) {
        const btn = document.getElementById(transferBtnId);
        if (btn) btn.addEventListener('click', () => transferToCompatCheck(build));
      }
      cardWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 150);
  }

  // ─── レーダーチャート描画 ────────────────────────────────────────────────
  const _radarInstances = {};
  function renderRadarChart(canvasId, buildScores, reqScores, gameName) {
    if (!buildScores || typeof Chart === 'undefined') return;
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    if (_radarInstances[canvasId]) {
      _radarInstances[canvasId].destroy();
    }

    const toData = s => [s.cpu, s.gpu, s.vram, s.ram, s.value == null ? null : s.value];
    const datasets = [{
      label: '提案構成',
      data: toData(buildScores),
      backgroundColor: 'rgba(158,207,255,0.18)',
      borderColor: '#9ECFFF',
      borderWidth: 2,
      pointBackgroundColor: '#9ECFFF',
      pointRadius: 3,
    }];

    if (reqScores) {
      datasets.push({
        label: (gameName ? gameName + ' 推奨' : 'ゲーム推奨'),
        data: toData(reqScores),
        backgroundColor: 'transparent',
        borderColor: '#FFB347',
        borderWidth: 2,
        borderDash: [5, 4],
        pointBackgroundColor: '#FFB347',
        pointRadius: 3,
      });
    }

    _radarInstances[canvasId] = new Chart(canvas, {
      type: 'radar',
      data: {
        labels: ['CPU', 'GPU', 'VRAM', 'RAM', 'コスパ'],
        datasets,
      },
      options: {
        responsive: false,
        scales: {
          r: {
            min: 0, max: 10, stepSize: 2,
            ticks: { display: false },
            grid: { color: 'rgba(96,105,117,0.4)' },
            angleLines: { color: 'rgba(96,105,117,0.4)' },
            pointLabels: {
              color: '#BBC2CA',
              font: { size: 11, family: 'Inter, sans-serif' },
            },
          },
        },
        plugins: {
          legend: {
            display: !!reqScores,
            position: 'bottom',
            labels: {
              color: '#BBC2CA',
              font: { size: 10, family: 'Inter, sans-serif' },
              boxWidth: 12,
              padding: 8,
            },
          },
        },
      },
    });
  }

  function buildAmazonUrl(name) {
    return 'https://www.amazon.co.jp/s?k=' + encodeURIComponent(name) + '&tag=' + AMAZON_TAG;
  }
  function buildRakutenUrl(name) {
    const search = 'https://search.rakuten.co.jp/search/mall/' + encodeURIComponent(name) + '/';
    if (RAKUTEN_A_ID && !RAKUTEN_A_ID.startsWith('__')) {
      return 'https://hb.afl.rakuten.co.jp/hgc/' + RAKUTEN_A_ID + '/' + RAKUTEN_L_ID +
             '/?pc=' + encodeURIComponent(search);
    }
    return search;
  }

  // ─── ユーティリティ ────────────────────────────────────────────────────
  function chat() { return document.getElementById('chat-area'); }
  function mkEl(tag, cls) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    return el;
  }
  function scrollBottom() {
    const c = chat();
    setTimeout(() => { c.scrollTop = c.scrollHeight; }, 40);
  }
  function setSending(on) {
    sending = on;
    document.getElementById('btn-send').disabled  = on;
    document.getElementById('chat-input').disabled = on;
  }
  function escHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function adjustHeight() {
    const ta = document.getElementById('chat-input');
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
  }

  // ─── 注目ゲームセクション折りたたみ ─────────────────────────────────────
  function toggleFeaturedGames() {
    // デスクトップ幅では無効
    if (window.innerWidth >= 1024) return;
    const section = document.getElementById('featured-games');
    section.classList.toggle('collapsed');
  }