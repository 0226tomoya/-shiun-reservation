"""スマホで確認・修正依頼を送るページ（claude.ai の Artifact）を作る。

    python3 mobile_review.py EVENTS.json VIDEOS.json OUT.html

EVENTS.json: review_page.py が書き出す A24_review_events.json（チャプターと #番号）
VIDEOS.json: {"version": "v23", "parts": [{"url": "...", "t0": 0, "t1": 258.9}, ...], "marks": [{"t": 879.6, "name": "..."}]}
修正依頼はページの db（collection "fixes"）に入り、Claude が ArtifactData で読んで対応状況を書き戻す。
"""
import json
import sys
from html import escape


def main():
    ev_path, vid_path, out = sys.argv[1:4]
    ev = json.load(open(ev_path, encoding='utf-8'))
    vids = json.load(open(vid_path, encoding='utf-8'))
    data = {
        'version': vids['version'],
        'total': ev['total'],
        'parts': vids['parts'],
        'marks': vids.get('marks', []),
        'chapters': ev['chapters'],
        'events': [[e['n'], e['t0'], e['t1'], e['kind'], e['text']] for e in ev['events']],
    }
    page = TEMPLATE.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/')) \
                   .replace('__VER__', escape(vids['version']))
    open(out, 'w', encoding='utf-8').write(page)
    print('->', out, f'{len(page) / 1024:.0f}KB')


TEMPLATE = r"""<title>A24 編集チェック</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@400;500;700&family=Cormorant+Garamond:wght@500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* 縦 1 列（スマホ）: 上に動画を固定、その下に「修正を送る」と 3 つの表（依頼・目次・#番号）。広い画面では動画と表を左右に */
:root {
  --bg: #e9e8e1;        /* 身長別比較の枠のグレージュに寄せた地 */
  --panel: #f6f5f0;
  --ink: #2f332a;       /* shiun のテロップのオリーブ墨 */
  --ink-2: #5d6255;
  --line: #d3d1c6;
  --accent: #54594a;    /* テロップ色そのもの */
  --accent-ink: #f6f5f0;
  --mark: #b88a1e;      /* 確認動画の黄色い時刻 */
  --open: #a3472f;
  --wip: #a87618;
  --done: #4f7b4c;
  --f-disp: "Cormorant Garamond", "Times New Roman", serif;
  --f-body: "Zen Kaku Gothic New", "Hiragino Sans", "Noto Sans JP", system-ui, sans-serif;
  --f-num: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #1c1d19; --panel: #25271f; --ink: #e8e7df; --ink-2: #aeb0a4; --line: #3a3d33;
  --accent: #c9ccb8; --accent-ink: #1c1d19; --mark: #e2b84a; --open: #e98d73; --wip: #e3b34f; --done: #8fc18a; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #1c1d19; --panel: #25271f; --ink: #e8e7df; --ink-2: #aeb0a4; --line: #3a3d33;
  --accent: #c9ccb8; --accent-ink: #1c1d19; --mark: #e2b84a; --open: #e98d73; --wip: #e3b34f; --done: #8fc18a; color-scheme: dark }

* { box-sizing: border-box }
body { background: var(--bg); color: var(--ink); font: 15px/1.6 var(--f-body); margin: 0 }
.wrap { max-width: 1180px; margin: 0 auto; padding-inline: 16px; padding-block: 10px 40px; display: grid; gap: 14px }
@media (min-width: 900px) { .wrap { grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); align-items: start } .side { max-height: calc(100vh - 40px); overflow: auto } }

header.top { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; flex-wrap: wrap }
header.top h1 { font: 600 24px/1.1 var(--f-disp); letter-spacing: .02em; margin: 0; text-wrap: balance }
header.top .ver { font: 500 12px var(--f-num); color: var(--ink-2); letter-spacing: .06em }

.player { position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; background: var(--bg); padding-block: 6px 8px; display: grid; gap: 8px }
.screen { position: relative; width: 100%; max-width: 100%; aspect-ratio: 16 / 9; background: #000; border-radius: 6px; overflow: hidden }
.screen video { width: 100%; height: 100%; display: block; background: #000 }
.screen .empty { position: absolute; inset: 0; display: grid; place-items: center; color: #cfd0c6; font-size: 13px; padding: 16px; text-align: center }
.clock { display: flex; align-items: center; gap: 10px; flex-wrap: wrap }
.clock .now { font: 500 26px/1 var(--f-num); font-variant-numeric: tabular-nums; color: var(--ink); letter-spacing: .02em }
.clock .where { font-size: 12px; color: var(--ink-2); min-width: 0; flex: 1 }
.nudge { display: flex; gap: 6px }
.nudge button { font: 500 12px var(--f-num); padding: 6px 8px; border-radius: 5px; border: 1px solid var(--line); background: var(--panel); color: var(--ink) }
.parts { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 2px; scrollbar-width: none }
.parts::-webkit-scrollbar { display: none }
.parts button { flex: 0 0 auto; font: 500 12px var(--f-num); font-variant-numeric: tabular-nums; padding: 6px 9px; border-radius: 999px; border: 1px solid var(--line); background: transparent; color: var(--ink-2) }
.parts button[aria-current="true"] { background: var(--accent); color: var(--accent-ink); border-color: var(--accent) }

.send { width: 100%; font: 700 16px var(--f-body); letter-spacing: .04em; padding: 14px; border: 0; border-radius: 8px; background: var(--accent); color: var(--accent-ink) }
.send small { font: 500 13px var(--f-num); opacity: .85; margin-left: 6px }

form.fix { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px; display: grid; gap: 12px }
form.fix .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: end }
form.fix label { font-size: 12px; color: var(--ink-2); display: grid; gap: 4px; min-width: 0 }
form.fix input, form.fix textarea { font: 16px var(--f-body); color: var(--ink); background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 9px 10px; width: 100% }
form.fix input.t { font-family: var(--f-num); width: 8.5em }
form.fix input.n { font-family: var(--f-num); width: 6em }
form.fix textarea { min-height: 96px; resize: vertical }
.cats { display: flex; gap: 6px; flex-wrap: wrap }
.cats button { font: 500 13px var(--f-body); padding: 6px 11px; border-radius: 999px; border: 1px solid var(--line); background: transparent; color: var(--ink) }
.cats button[aria-pressed="true"] { background: var(--ink); color: var(--bg); border-color: var(--ink) }
.near { font-size: 12px; color: var(--ink-2) }
.near b { font-family: var(--f-num); font-weight: 500; color: var(--ink) }
.actions { display: flex; gap: 8px; justify-content: flex-end }
.actions button { font: 700 14px var(--f-body); padding: 10px 16px; border-radius: 6px; border: 1px solid var(--line); background: transparent; color: var(--ink) }
.actions .go { background: var(--accent); color: var(--accent-ink); border-color: var(--accent) }
.note { font-size: 13px; color: var(--ink-2) }
.toast { font-size: 13px; padding: 8px 10px; border-radius: 6px; background: var(--panel); border: 1px solid var(--line) }

.tabs { display: flex; gap: 0; border-bottom: 1px solid var(--line) }
.tabs button { flex: 1; font: 500 14px var(--f-body); padding: 10px 6px; background: transparent; border: 0; border-bottom: 2px solid transparent; color: var(--ink-2) }
.tabs button[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--ink) }
.tabs .cnt { font: 500 11px var(--f-num); margin-left: 4px }
ul.list { list-style: none; margin: 0; padding: 0 }
ul.list li { border-bottom: 1px solid var(--line) }
.item { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 4px 12px; padding: 11px 2px; width: 100%; text-align: left; background: transparent; border: 0; color: inherit; font: inherit }
.item .tc { font: 500 13px var(--f-num); font-variant-numeric: tabular-nums; color: var(--ink); padding-top: 1px }
.item .tc small { display: block; color: var(--ink-2); font-size: 11px }
.item .body { min-width: 0; overflow-wrap: anywhere }
.item .kind { font-size: 11px; letter-spacing: .06em; color: var(--ink-2) }
.item .txt { font-size: 14px }
.chap { font: 600 19px/1.2 var(--f-disp); letter-spacing: .02em; padding: 16px 2px 4px; color: var(--ink) }
.chap span { font: 500 12px var(--f-num); color: var(--ink-2); margin-left: 8px }
.k-字幕 .kind { color: var(--open) }
.k-身長別比較 .kind, .mk .kind { color: var(--mark) }
.search { width: 100%; font: 16px var(--f-body); color: var(--ink); background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 9px 10px; margin-block: 10px }

.fx { padding: 12px 2px; display: grid; gap: 6px }
.fx .head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap }
.fx .tc { font: 500 13px var(--f-num); color: var(--ink); background: transparent; border: 0; padding: 0; text-decoration: underline; text-underline-offset: 3px }
.pill { font-size: 11px; font-weight: 700; letter-spacing: .06em; padding: 2px 8px; border-radius: 999px; border: 1px solid currentColor }
.pill.open { color: var(--open) } .pill.wip { color: var(--wip) } .pill.done { color: var(--done) }
.fx .cat { font-size: 12px; color: var(--ink-2) }
.fx .txt { white-space: pre-wrap; overflow-wrap: anywhere }
.fx .reply { font-size: 13px; color: var(--ink-2); border-left: 2px solid var(--line); padding-left: 10px; white-space: pre-wrap }
.fx .del { margin-left: auto; font-size: 12px; background: transparent; border: 0; color: var(--ink-2); text-decoration: underline }
.empty-state { padding: 18px 4px; color: var(--ink-2); font-size: 14px }
button { cursor: pointer }
button:focus-visible, input:focus-visible, textarea:focus-visible { outline: 2px solid var(--mark); outline-offset: 2px }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important } }
</style>

<div class="wrap">
  <div class="main">
    <header class="top">
      <h1>A24 shiun 26FW Winter 1st</h1>
      <span class="ver" id="ver">__VER__ ・ 確認動画</span>
    </header>
    <section class="player" aria-label="確認動画">
      <div class="screen">
        <video id="v" playsinline controls preload="metadata"></video>
        <div class="empty" id="noVideo" hidden>動画を読み込み中です。表示されない場合は、少し待ってから開き直してください。</div>
      </div>
      <div class="clock">
        <span class="now" id="now">0:00.0</span>
        <span class="where" id="where">OP</span>
        <span class="nudge"><button type="button" data-d="-5">−5秒</button><button type="button" data-d="-1">−1秒</button><button type="button" data-d="1">+1秒</button></span>
      </div>
      <div class="parts" id="parts" role="tablist" aria-label="動画のパート"></div>
    </section>

    <button class="send" type="button" id="openForm">この時刻で修正を送る<small id="openAt">0:00.0</small></button>

    <form class="fix" id="form" hidden>
      <div class="row">
        <label for="fT">時刻（全編）<input class="t" id="fT" inputmode="decimal" autocomplete="off"></label>
        <label for="fN">#番号（任意）<input class="n" id="fN" inputmode="numeric" autocomplete="off"></label>
      </div>
      <div class="near" id="near"></div>
      <div class="cats" id="cats" role="group" aria-label="種類"></div>
      <label for="fText">内容<textarea id="fText" placeholder="例: この字幕をもう少し早く出す／インサートを別の場面に"></textarea></label>
      <div class="actions"><button type="button" id="cancel">やめる</button><button type="submit" class="go" id="submit">送る</button></div>
      <div class="note" id="formNote"></div>
    </form>
    <div class="toast" id="toast" hidden></div>
  </div>

  <div class="side">
    <div class="tabs" role="tablist">
      <button type="button" role="tab" id="tab-fix" aria-selected="true">修正依頼<span class="cnt" id="cntFix"></span></button>
      <button type="button" role="tab" id="tab-toc" aria-selected="false">目次</button>
      <button type="button" role="tab" id="tab-ev" aria-selected="false">#番号</button>
    </div>
    <section id="pane-fix" role="tabpanel" aria-labelledby="tab-fix">
      <ul class="list" id="fixList"></ul>
      <div class="empty-state" id="fixEmpty">まだ修正依頼はありません。動画を止めて「この時刻で修正を送る」から送ると、ここに並び、Claude が対応すると「対応済み」に変わります。</div>
    </section>
    <section id="pane-toc" role="tabpanel" aria-labelledby="tab-toc" hidden><ul class="list" id="toc"></ul></section>
    <section id="pane-ev" role="tabpanel" aria-labelledby="tab-ev" hidden>
      <input class="search" id="q" type="search" placeholder="#番号・言葉で探す（例: 42、字幕、ローファー）" autocomplete="off">
      <ul class="list" id="evList"></ul>
    </section>
  </div>
</div>

<script>
const D = __DATA__;
const $ = (id) => document.getElementById(id);
const v = $('v');
const CATS = ['テロップ', 'インサート', '画角・構図', 'カット・長さ', '音', 'その他'];
let part = -1, cat = 'テロップ', db = null, fixes = [];

function fmt(t) { t = Math.max(0, t); const m = Math.floor(t / 60), s = t - m * 60; return m + ':' + (s < 10 ? '0' : '') + s.toFixed(1); }
function parseT(s) {
  s = String(s).trim(); if (!s) return null;
  const m = s.match(/^(\d+)[:：](\d+(?:\.\d+)?)$/); if (m) return +m[1] * 60 + +m[2];
  return isFinite(+s) ? +s : null;
}
function chapterAt(t) { const c = D.chapters.find(c => c.t0 <= t && t < c.t1) || D.chapters[D.chapters.length - 1]; return c ? c.name : ''; }
function markAt(t) { const m = D.marks.find(m => m.t <= t && t < m.t + (m.d || 48)); return m ? m.name : ''; }
function globalTime() { return part < 0 ? 0 : D.parts[part].t0 + (v.currentTime || 0); }
function nearestEvents(t) {
  return D.events.filter(e => e[3] !== 'BGM' && e[1] <= t + 0.05 && t < e[2] + 0.05).sort((a, b) => (b[1] - a[1])).slice(0, 4);
}

// ---- 動画 ----
function load(k, local, play) {
  if (!D.parts[k] || !D.parts[k].url) { $('noVideo').hidden = false; return; }
  $('noVideo').hidden = true;
  const want = local || 0;
  if (part !== k) {
    part = k;
    v.src = D.parts[k].url;
    v.addEventListener('loadedmetadata', function once() { v.removeEventListener('loadedmetadata', once); v.currentTime = want; if (play) v.play().catch(() => {}); });
  } else { v.currentTime = want; if (play) v.play().catch(() => {}); }
  document.querySelectorAll('#parts button').forEach((b, i) => b.setAttribute('aria-current', String(i === k)));
  tick();
}
function seek(t, play) {
  t = Math.min(Math.max(0, t), D.total - 0.05);
  let k = D.parts.findIndex(p => p.t0 <= t && t < p.t1); if (k < 0) k = D.parts.length - 1;
  load(k, t - D.parts[k].t0, play);
  if (window.matchMedia('(max-width: 899px)').matches) window.scrollTo({ top: 0, behavior: 'smooth' });
}
function tick() {
  const t = globalTime();
  $('now').textContent = fmt(t);
  $('openAt').textContent = fmt(t);
  const mk = markAt(t);
  $('where').textContent = chapterAt(t) + (mk ? ' ・ ' + mk : '');
}
v.addEventListener('timeupdate', tick);
v.addEventListener('seeked', tick);
v.addEventListener('ended', () => { if (part < D.parts.length - 1) load(part + 1, 0, true); });
document.querySelectorAll('.nudge button').forEach(b => b.addEventListener('click', () => seek(globalTime() + +b.dataset.d, false)));
D.parts.forEach((p, i) => {
  const b = document.createElement('button'); b.type = 'button'; b.setAttribute('role', 'tab');
  b.textContent = (i + 1) + '  ' + fmt(p.t0).replace(/\.\d$/, '');
  b.addEventListener('click', () => load(i, 0, false));
  $('parts').appendChild(b);
});

// ---- 修正を送る ----
CATS.forEach(c => {
  const b = document.createElement('button'); b.type = 'button'; b.textContent = c; b.setAttribute('aria-pressed', String(c === cat));
  b.addEventListener('click', () => { cat = c; document.querySelectorAll('#cats button').forEach(x => x.setAttribute('aria-pressed', String(x.textContent === c))); });
  $('cats').appendChild(b);
});
function showNear() {
  const t = parseT($('fT').value); if (t == null) { $('near').textContent = ''; return; }
  const ns = nearestEvents(t);
  $('near').innerHTML = '';
  if (!ns.length) { $('near').textContent = 'この時刻はトークのみ（' + chapterAt(t) + '）'; return; }
  $('near').append('この時刻にあるもの: ');
  ns.forEach((e, i) => {
    const b = document.createElement('b'); b.textContent = '#' + e[0];
    $('near').append(b, ' ' + e[3] + (e[4] ? '「' + e[4].slice(0, 24) + (e[4].length > 24 ? '…' : '') + '」' : '') + (i < ns.length - 1 ? '、' : ''));
  });
  if (!$('fN').value && ns.length) $('fN').placeholder = String(ns[0][0]);
}
$('openForm').addEventListener('click', () => {
  v.pause();
  $('fT').value = fmt(globalTime()); $('fN').value = ''; $('fN').placeholder = '';
  $('form').hidden = false; $('formNote').textContent = db ? '' : '保存の準備中です。送れない場合は、内容をコピーしてチャットに送ってください。';
  showNear(); $('fText').focus();
});
$('fT').addEventListener('input', showNear);
$('cancel').addEventListener('click', () => { $('form').hidden = true; });
$('form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const t = parseT($('fT').value), text = $('fText').value.trim();
  if (t == null) { $('formNote').textContent = '時刻は「12:34.5」の形で入れてください。'; return; }
  if (!text) { $('formNote').textContent = '内容を書いてください。'; return; }
  const n = parseInt($('fN').value || $('fN').placeholder || '', 10);
  if (!db) { $('formNote').textContent = '保存できませんでした。お手数ですが「' + fmt(t) + ' ' + text + '」をチャットに送ってください。'; return; }
  $('submit').disabled = true;
  const body = { t: Math.round(t * 10) / 10, n: isFinite(n) ? n : null, cat, text, status: 'open', reply: '', version: D.version, created: new Date().toISOString() };
  try {
    const u = window.claude && window.claude.use ? await window.claude.use('user') : null; const id = u ? await u.id() : null; if (id) body.author = id;
  } catch (_) {}
  try {
    await db.collection('fixes').add(body);
    $('form').hidden = true; $('fText').value = '';
    flash('送りました（' + fmt(t) + '）。Claude が対応すると状態が変わります。');
    select('fix');
  } catch (err) {
    $('formNote').textContent = err && err.code === 'quota_exceeded' ? '保存できる数の上限です。対応済みのものを消してから送ってください。'
      : '送れませんでした。もう一度押すか、「' + fmt(t) + ' ' + text + '」をチャットに送ってください。';
  } finally { $('submit').disabled = false; }
});
function flash(s) { const el = $('toast'); el.textContent = s; el.hidden = false; clearTimeout(flash.h); flash.h = setTimeout(() => el.hidden = true, 5000); }

// ---- 修正依頼の一覧 ----
const ST = { open: ['未対応', 'open'], wip: ['対応中', 'wip'], done: ['対応済み', 'done'] };
let armed = null;
function renderFixes() {
  const ul = $('fixList'); ul.innerHTML = '';
  const open = fixes.filter(f => f.d.status !== 'done').length;
  $('cntFix').textContent = fixes.length ? (open + '/' + fixes.length) : '';
  $('fixEmpty').hidden = fixes.length > 0;
  fixes.forEach(({ id, d }) => {
    const li = document.createElement('li'); const box = document.createElement('div'); box.className = 'fx';
    const head = document.createElement('div'); head.className = 'head';
    const tc = document.createElement('button'); tc.type = 'button'; tc.className = 'tc'; tc.textContent = fmt(+d.t || 0) + (d.n ? '  #' + d.n : '');
    tc.addEventListener('click', () => seek(+d.t || 0, false));
    const st = ST[d.status] || ST.open; const pill = document.createElement('span'); pill.className = 'pill ' + st[1]; pill.textContent = st[0];
    const c = document.createElement('span'); c.className = 'cat'; c.textContent = (d.cat || '') + (d.version ? ' ・ ' + d.version : '');
    const del = document.createElement('button'); del.type = 'button'; del.className = 'del';
    del.textContent = armed === id ? 'もう一度押すと消えます' : '消す';
    del.addEventListener('click', async () => {
      if (armed !== id) { armed = id; renderFixes(); return; }
      armed = null; try { await db.collection('fixes').doc(id).delete(); } catch (_) { flash('消せませんでした。'); }
    });
    head.append(tc, pill, c, del);
    const tx = document.createElement('div'); tx.className = 'txt'; tx.textContent = d.text || '';
    box.append(head, tx);
    if (d.reply) { const r = document.createElement('div'); r.className = 'reply'; r.textContent = 'Claude: ' + d.reply; box.append(r); }
    li.append(box); ul.append(li);
  });
}

// ---- 目次・#番号 ----
function item(tc, sub, kind, txt, cls, t) {
  const li = document.createElement('li'); const b = document.createElement('button'); b.type = 'button'; b.className = 'item ' + (cls || '');
  const a = document.createElement('span'); a.className = 'tc'; a.textContent = tc; if (sub) { const s = document.createElement('small'); s.textContent = sub; a.append(s); }
  const body = document.createElement('span'); body.className = 'body';
  const k = document.createElement('div'); k.className = 'kind'; k.textContent = kind;
  const x = document.createElement('div'); x.className = 'txt'; x.textContent = txt;
  body.append(k, x); b.append(a, body); b.addEventListener('click', () => seek(t, true)); li.append(b); return li;
}
D.chapters.forEach(c => {
  const h = document.createElement('li'); h.className = 'chap'; h.textContent = c.name; const s = document.createElement('span'); s.textContent = fmt(c.t0).replace(/\.\d$/, '') + '〜'; h.append(s);
  $('toc').append(h);
  $('toc').append(item(fmt(c.t0), '', 'チャプター', c.name + ' の頭', '', c.t0 + 0.05));
  D.marks.filter(m => c.t0 <= m.t && m.t < c.t1).forEach(m => $('toc').append(item(fmt(m.t), '', m.kind || '見どころ', m.name, 'mk', m.t + 0.05)));
});
function renderEvents() {
  const q = $('q').value.trim(); const ul = $('evList'); ul.innerHTML = '';
  const num = /^#?\d+$/.test(q) ? parseInt(q.replace('#', ''), 10) : null;
  let last = null;
  D.events.filter(e => e[3] !== 'BGM' && (!q || (num != null ? e[0] === num : (e[3] + e[4]).includes(q)))).forEach(e => {
    const ch = chapterAt(e[1]);
    if (ch !== last) { const h = document.createElement('li'); h.className = 'chap'; h.textContent = ch; ul.append(h); last = ch; }
    ul.append(item('#' + e[0], fmt(e[1]), e[3], e[4] || '—', 'k-' + e[3], e[1] + 0.05));
  });
}
$('q').addEventListener('input', renderEvents);
function select(name) {
  ['fix', 'toc', 'ev'].forEach(n => { $('tab-' + n).setAttribute('aria-selected', String(n === name)); $('pane-' + n).hidden = n !== name; });
}
['fix', 'toc', 'ev'].forEach(n => $('tab-' + n).addEventListener('click', () => select(n)));

renderEvents(); renderFixes(); load(0, 0, false);

// ---- 保存（db）----
(async () => {
  try { db = window.claude && window.claude.use ? await window.claude.use('db') : null; } catch (_) { db = null; }
  if (!db) { $('fixEmpty').textContent = 'この画面では修正依頼を保存できません。チャットに「分:秒」と内容を送ってください。'; return; }
  db.collection('fixes').orderBy('created', 'desc').onSnapshot(s => { fixes = s.docs.map(x => ({ id: x.id, d: x.data() || {} })); renderFixes(); },
    () => { $('fixEmpty').textContent = '一覧を読み込めませんでした。開き直してください。'; });
})();
</script>
"""

if __name__ == '__main__':
    main()
