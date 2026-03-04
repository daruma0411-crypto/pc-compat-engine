/* ================================================================
   直帰率対策: Exit Intent Modal + Scroll 50% CTA
   ================================================================ */

// Exit Intent Detection
let exitIntentShown = false;

document.addEventListener('mouseleave', function(e) {
  if (e.clientY <= 0 && !exitIntentShown && !sessionStorage.getItem('exitIntentShown')) {
    showExitIntentModal();
    exitIntentShown = true;
    sessionStorage.setItem('exitIntentShown', 'true');
  }
});

function showExitIntentModal() {
  var modal = document.createElement('div');
  modal.className = 'exit-intent-modal';
  modal.innerHTML =
    '<div class="exit-modal-overlay" onclick="closeExitIntent()"></div>' +
    '<div class="exit-modal-content">' +
      '<button class="exit-modal-close" onclick="closeExitIntent()">&times;</button>' +
      '<h2>ちょっと待って！</h2>' +
      '<p>あなたのPCでゲームが動くか、<br>30秒で無料診断できます</p>' +
      '<a href="/" class="exit-modal-cta">今すぐ診断する →</a>' +
      '<div class="exit-modal-games">' +
        '<span>人気:</span> ' +
        '<a href="/game/monster-hunter-wilds">モンハンワイルズ</a> · ' +
        '<a href="/game/elden-ring">エルデンリング</a> · ' +
        '<a href="/game/palworld">パルワールド</a>' +
      '</div>' +
    '</div>';
  document.body.appendChild(modal);
  setTimeout(function() { modal.classList.add('show'); }, 10);
}

function closeExitIntent() {
  var modal = document.querySelector('.exit-intent-modal');
  if (modal) {
    modal.classList.remove('show');
    setTimeout(function() { modal.remove(); }, 300);
  }
}

// Scroll 50% CTA
var scrollCtaShown = false;

window.addEventListener('scroll', function() {
  var docHeight = document.documentElement.scrollHeight - window.innerHeight;
  if (docHeight <= 0) return;
  var scrollPercent = (window.scrollY / docHeight) * 100;

  if (scrollPercent > 50 && !scrollCtaShown && !sessionStorage.getItem('scrollCtaShown')) {
    showScrollCta();
    scrollCtaShown = true;
    sessionStorage.setItem('scrollCtaShown', 'true');
  }
});

function showScrollCta() {
  var cta = document.createElement('div');
  cta.className = 'scroll-cta';
  cta.innerHTML =
    '<div class="scroll-cta-content">' +
      '<span class="scroll-cta-text">💡 あなたのPCスペックを診断してみませんか？</span>' +
      '<a href="/" class="scroll-cta-button">今すぐ診断 →</a>' +
      '<button class="scroll-cta-close" onclick="closeScrollCta()">&times;</button>' +
    '</div>';
  document.body.appendChild(cta);
  setTimeout(function() { cta.classList.add('show'); }, 10);
}

function closeScrollCta() {
  var cta = document.querySelector('.scroll-cta');
  if (cta) {
    cta.classList.remove('show');
    setTimeout(function() { cta.remove(); }, 300);
  }
}
