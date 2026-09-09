import React, { useEffect, useMemo, useState } from "react";
import { ACCOUNT, SIGNALS, CAVEATS } from "./data/serenitySignals.js";
import {
  NISA, RISK_PRESETS, yen, themeScores, nisaRoom, buySuggestions, sellSuggestions,
} from "./lib/agent.js";

// ---- design tokens ----
const BG = "#fafaf7";
const CARD = "#ffffff";
const INK = "#1a1a1a";
const SUB = "#555";
const MUTED = "#8a8a84";
const BORDER = "#e4e3da";
const ACCENT = "#2c5fb3"; // 単一色 (数量・メーター用)
const ACCENT_SOFT = "#dbe6f6";
const GOOD = "#1e7f4f";
const WARN = "#a05a00";
const BAD = "#b3362c";

const card = {
  background: CARD, border: `1px solid ${BORDER}`, borderRadius: 12,
  padding: 20, marginBottom: 16,
};
const h2 = { fontSize: 15, fontWeight: 800, margin: "0 0 4px", color: INK };
const capStyle = { fontSize: 11, color: MUTED, margin: "0 0 14px" };
const inputStyle = {
  width: "100%", padding: "10px 12px", borderRadius: 8, border: `1px solid ${BORDER}`,
  background: BG, color: INK, fontSize: 13, outline: "none", boxSizing: "border-box",
};

const load = (k, fallback) => {
  try {
    const v = JSON.parse(localStorage.getItem(k));
    return v == null ? fallback : v;
  } catch { return fallback; }
};

const DEFAULT_PROFILE = {
  risk: "mid", monthlyBudget: 100000,
  usedTsumitate: 0, usedGrowth: 0, lifetimeUsed: 0, lifetimeGrowthUsed: 0,
};

// ---- 小物コンポーネント ----
function Meter({ label, used, max }) {
  const pct = Math.min(100, (used / max) * 100);
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 5 }}>
        <span style={{ color: SUB, fontWeight: 600 }}>{label}</span>
        <span style={{ color: INK, fontVariantNumeric: "tabular-nums" }}>
          {yen(used)} <span style={{ color: MUTED }}>/ {yen(max)}（残り {yen(max - used)}）</span>
        </span>
      </div>
      <div style={{ height: 8, background: ACCENT_SOFT, borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: ACCENT, borderRadius: 4 }} />
      </div>
    </div>
  );
}

function Tag({ level, children }) {
  const color = level === "action" ? GOOD : level === "warn" ? WARN : SUB;
  const mark = level === "action" ? "▶" : level === "warn" ? "⚠" : "ℹ";
  return (
    <div style={{ display: "flex", gap: 8, fontSize: 12.5, color: SUB, lineHeight: 1.6, marginTop: 6 }}>
      <span style={{ color, flexShrink: 0 }}>{mark}</span>
      <span>{children}</span>
    </div>
  );
}

function ScoreBar({ theme, score, max, tickers }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
        <span style={{ fontWeight: 700, color: INK }}>{theme}</span>
        <span style={{ color: MUTED }}>{tickers.join(" · ")}</span>
      </div>
      <div style={{ height: 8, background: "#efeee6", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${Math.max(2, (score / max) * 100)}%`, height: "100%", background: ACCENT, borderRadius: 4 }} />
      </div>
    </div>
  );
}

// ---- タブ ----
function Dashboard({ profile, holdings }) {
  const scores = useMemo(() => themeScores(), []);
  const maxScore = scores[0]?.score || 1;
  const buys = useMemo(() => buySuggestions(profile), [profile]);
  const sells = useMemo(() => sellSuggestions(holdings), [holdings]);
  const room = nisaRoom(profile);

  return (
    <>
      <div style={card}>
        <h2 style={h2}>NISA 枠の消化状況（{new Date().getFullYear()}年）</h2>
        <p style={capStyle}>新NISA: つみたて枠 年120万・成長枠 年240万・生涯1,800万（うち成長枠1,200万）</p>
        <Meter label="つみたて投資枠" used={profile.usedTsumitate} max={NISA.TSUMITATE_ANNUAL} />
        <Meter label="成長投資枠" used={profile.usedGrowth} max={NISA.GROWTH_ANNUAL} />
        <Meter label="生涯非課税限度額（簿価）" used={profile.lifetimeUsed} max={NISA.LIFETIME} />
      </div>

      <div style={card}>
        <h2 style={h2}>Serenity テーマ・ヒートスコア</h2>
        <p style={capStyle}>確信度 × 鮮度（6ヶ月半減）で集計した、直近の言及の集中度</p>
        {scores.map((s) => (
          <ScoreBar key={s.theme} theme={s.theme} score={s.score} max={maxScore} tickers={s.tickers} />
        ))}
      </div>

      <div style={card}>
        <h2 style={h2}>エージェントの買い提案</h2>
        <p style={capStyle}>
          リスク設定「{RISK_PRESETS[profile.risk].label}」/ 月予算 {yen(profile.monthlyBudget)} / 成長枠残り {yen(room.growthLeft)}
        </p>
        {buys.map((b, i) => (
          <div key={i} style={{ borderTop: i ? `1px solid ${BORDER}` : "none", padding: "12px 0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span style={{ fontSize: 13, fontWeight: 800, color: INK }}>
                {b.kind === "core" ? "コア積立" : b.kind === "satellite" ? "テーマ・サテライト" : b.kind === "single" ? "個別株サテライト" : "お知らせ"}
                <span style={{ fontWeight: 600, color: MUTED, marginLeft: 8, fontSize: 11 }}>{b.account}</span>
              </span>
              {b.amount > 0 && (
                <span style={{ fontSize: 13, fontWeight: 700, color: ACCENT, fontVariantNumeric: "tabular-nums" }}>
                  {yen(b.amount)}<span style={{ fontSize: 10, color: MUTED }}> /{b.unit}</span>
                </span>
              )}
            </div>
            <div style={{ fontSize: 12.5, color: SUB, lineHeight: 1.7, margin: "6px 0" }}>{b.reason}</div>
            {b.items.map((f, j) => (
              <div key={j} style={{ fontSize: 12, color: INK, padding: "3px 0 3px 12px", borderLeft: `2px solid ${ACCENT_SOFT}` }}>
                {f.name} <span style={{ color: MUTED }}>（{f.type}）</span>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div style={card}>
        <h2 style={h2}>売却・見直しアラート</h2>
        <p style={capStyle}>保有ポートフォリオへのルールベース診断（利確 / 損切り / 集中度 / NISA制度）</p>
        {sells.length === 0 ? (
          <div style={{ fontSize: 12.5, color: MUTED }}>
            アラートはありません。「ポートフォリオ」タブで保有銘柄を登録すると診断されます。
          </div>
        ) : sells.map((s, i) => (
          <div key={i} style={{ borderTop: i ? `1px solid ${BORDER}` : "none", padding: "12px 0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
              <span style={{ fontWeight: 800, color: INK }}>
                {s.holding.name}
                {s.holding.ticker ? <span style={{ color: MUTED, fontWeight: 600 }}> {s.holding.ticker}</span> : null}
              </span>
              <span style={{ fontWeight: 700, color: s.gain >= 0 ? GOOD : BAD, fontVariantNumeric: "tabular-nums" }}>
                {s.gain >= 0 ? "+" : ""}{Math.round(s.gain * 100)}%
              </span>
            </div>
            {s.tags.map((t, j) => <Tag key={j} level={t.level}>{t.text}</Tag>)}
          </div>
        ))}
      </div>
    </>
  );
}

function Signals() {
  const [q, setQ] = useState("");
  const list = SIGNALS.filter(
    (s) => !q || `${s.ticker} ${s.name} ${s.theme} ${s.thesis}`.toLowerCase().includes(q.toLowerCase())
  ).sort((a, b) => b.date.localeCompare(a.date));

  return (
    <>
      <div style={{ ...card, padding: 14 }}>
        <div style={{ fontSize: 12.5, color: SUB, lineHeight: 1.7 }}>
          <b>{ACCOUNT.name}（{ACCOUNT.handle}）</b> — {ACCOUNT.alias}・フォロワー {ACCOUNT.followers}<br />
          {ACCOUNT.profile}
        </div>
      </div>
      <input
        style={{ ...inputStyle, marginBottom: 14 }}
        placeholder="ティッカー・テーマ・キーワードで検索"
        value={q} onChange={(e) => setQ(e.target.value)}
      />
      {list.map((s) => (
        <div key={s.id} style={{ ...card, padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 6 }}>
            <span style={{ fontSize: 14, fontWeight: 800, color: INK }}>
              {s.ticker} <span style={{ fontWeight: 600, color: SUB }}>{s.name}</span>
              <span style={{ fontSize: 10.5, color: MUTED, marginLeft: 8 }}>{s.market}</span>
            </span>
            <span style={{ fontSize: 11.5, color: MUTED }}>{s.date} 言及</span>
          </div>
          <div style={{ margin: "8px 0", display: "flex", gap: 6, flexWrap: "wrap" }}>
            <span style={{ fontSize: 10.5, fontWeight: 700, color: s.direction === "bull" ? GOOD : BAD, border: `1px solid ${BORDER}`, borderRadius: 20, padding: "2px 10px" }}>
              {s.direction === "bull" ? "強気" : "弱気"}
            </span>
            <span style={{ fontSize: 10.5, color: SUB, border: `1px solid ${BORDER}`, borderRadius: 20, padding: "2px 10px" }}>{s.theme}</span>
            <span style={{ fontSize: 10.5, color: SUB, border: `1px solid ${BORDER}`, borderRadius: 20, padding: "2px 10px" }}>確信度 {"●".repeat(s.conviction)}{"○".repeat(5 - s.conviction)}</span>
          </div>
          <div style={{ fontSize: 12.5, color: SUB, lineHeight: 1.8 }}>{s.thesis}</div>
          <div style={{ fontSize: 11.5, color: MUTED, marginTop: 8 }}>
            {s.performance !== "—" && <>言及後パフォーマンス: <b style={{ color: INK }}>{s.performance}</b> ・ </>}
            出典: {s.source}
          </div>
        </div>
      ))}
    </>
  );
}

function Portfolio({ holdings, setHoldings }) {
  const empty = { name: "", ticker: "", account: "growth", cost: "", value: "", serenity: false };
  const [form, setForm] = useState(empty);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const add = () => {
    if (!form.name || !form.cost || !form.value) return;
    setHoldings([...holdings, { ...form, ticker: form.ticker.toUpperCase(), cost: +form.cost, value: +form.value, id: Date.now() }]);
    setForm(empty);
  };
  const accountLabel = { tsumitate: "つみたて枠", growth: "成長枠", taxable: "特定/一般" };

  return (
    <>
      <div style={card}>
        <h2 style={h2}>保有銘柄を追加</h2>
        <p style={capStyle}>投資信託・ETF・個別株を登録すると、ダッシュボードで売却診断されます（データはこの端末にのみ保存）</p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <input style={inputStyle} placeholder="銘柄名（例: eMAXIS Slim 全世界株式）" value={form.name} onChange={set("name")} />
          <input style={inputStyle} placeholder="ティッカー（任意・例: SIVE）" value={form.ticker} onChange={set("ticker")} />
          <input style={inputStyle} type="number" placeholder="取得額 (円)" value={form.cost} onChange={set("cost")} />
          <input style={inputStyle} type="number" placeholder="現在評価額 (円)" value={form.value} onChange={set("value")} />
          <select style={inputStyle} value={form.account} onChange={set("account")}>
            <option value="tsumitate">つみたて投資枠</option>
            <option value="growth">成長投資枠</option>
            <option value="taxable">特定/一般口座</option>
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, color: SUB }}>
            <input type="checkbox" checked={form.serenity} onChange={set("serenity")} />
            Serenity シグナルを根拠に購入
          </label>
        </div>
        <button
          onClick={add}
          style={{ marginTop: 12, width: "100%", padding: 13, borderRadius: 8, border: "none", background: INK, color: "#fff", fontWeight: 800, fontSize: 13, cursor: "pointer" }}
        >
          追加する
        </button>
      </div>

      <div style={card}>
        <h2 style={h2}>保有一覧</h2>
        {holdings.length === 0 && <div style={{ fontSize: 12.5, color: MUTED }}>まだ登録がありません。</div>}
        {holdings.map((h) => {
          const gain = h.cost > 0 ? (h.value - h.cost) / h.cost : 0;
          return (
            <div key={h.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: `1px solid ${BORDER}` }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: INK }}>
                  {h.name} {h.ticker && <span style={{ color: MUTED, fontWeight: 600 }}>{h.ticker}</span>}
                </div>
                <div style={{ fontSize: 11, color: MUTED }}>
                  {accountLabel[h.account]}・取得 {yen(h.cost)} → 評価 {yen(h.value)}
                  {h.serenity ? "・Serenity起点" : ""}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: gain >= 0 ? GOOD : BAD, fontVariantNumeric: "tabular-nums" }}>
                  {gain >= 0 ? "+" : ""}{Math.round(gain * 100)}%
                </span>
                <button
                  onClick={() => setHoldings(holdings.filter((x) => x.id !== h.id))}
                  style={{ border: `1px solid ${BORDER}`, background: "transparent", color: MUTED, borderRadius: 6, padding: "4px 10px", fontSize: 11, cursor: "pointer" }}
                >
                  削除
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

function Settings({ profile, setProfile }) {
  const set = (k, num = true) => (e) =>
    setProfile({ ...profile, [k]: num ? +e.target.value || 0 : e.target.value });
  const Field = ({ label, children }) => (
    <label style={{ display: "block", marginBottom: 14 }}>
      <div style={{ fontSize: 11, color: MUTED, letterSpacing: 1, marginBottom: 6 }}>{label}</div>
      {children}
    </label>
  );
  return (
    <div style={card}>
      <h2 style={h2}>プロファイル設定</h2>
      <p style={capStyle}>提案ロジックの前提になります。NISA消化額は証券会社の画面の値を入力してください。</p>
      <Field label="リスク許容度">
        <select style={inputStyle} value={profile.risk} onChange={set("risk", false)}>
          {Object.entries(RISK_PRESETS).map(([k, v]) => (
            <option key={k} value={k}>{v.label}（コア{v.core * 100}% / テーマ{v.theme * 100}% / 個別株{v.single * 100}%）</option>
          ))}
        </select>
      </Field>
      <Field label="毎月の投資可能額 (円)">
        <input style={inputStyle} type="number" value={profile.monthlyBudget} onChange={set("monthlyBudget")} />
      </Field>
      <Field label="今年のつみたて投資枠 使用額 (円)">
        <input style={inputStyle} type="number" value={profile.usedTsumitate} onChange={set("usedTsumitate")} />
      </Field>
      <Field label="今年の成長投資枠 使用額 (円)">
        <input style={inputStyle} type="number" value={profile.usedGrowth} onChange={set("usedGrowth")} />
      </Field>
      <Field label="生涯非課税限度額 使用済み額・簿価 (円)">
        <input style={inputStyle} type="number" value={profile.lifetimeUsed} onChange={set("lifetimeUsed")} />
      </Field>
      <Field label="うち成長投資枠での使用額 (円)">
        <input style={inputStyle} type="number" value={profile.lifetimeGrowthUsed} onChange={set("lifetimeGrowthUsed")} />
      </Field>
    </div>
  );
}

// ---- ルート ----
export default function App() {
  const [tab, setTab] = useState("dash");
  const [profile, setProfile] = useState(() => ({ ...DEFAULT_PROFILE, ...load("ama_profile", {}) }));
  const [holdings, setHoldings] = useState(() => load("ama_holdings", []));
  useEffect(() => { try { localStorage.setItem("ama_profile", JSON.stringify(profile)); } catch {} }, [profile]);
  useEffect(() => { try { localStorage.setItem("ama_holdings", JSON.stringify(holdings)); } catch {} }, [holdings]);

  const tabs = [
    ["dash", "ダッシュボード"],
    ["signals", "Serenityシグナル"],
    ["portfolio", "ポートフォリオ"],
    ["settings", "設定"],
  ];

  return (
    <div style={{ minHeight: "100vh", background: BG, color: INK, fontFamily: "'Hiragino Sans','Noto Sans JP',sans-serif" }}>
      <div style={{ maxWidth: 640, margin: "0 auto", padding: "28px 16px 60px" }}>
        <header style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 10, color: MUTED, letterSpacing: 3 }}>SERENITY SIGNAL × 新NISA</div>
          <h1 style={{ fontSize: 21, fontWeight: 900, margin: "6px 0 4px" }}>資産運用アシストエージェント</h1>
          <div style={{ fontSize: 11.5, color: MUTED }}>
            {ACCOUNT.handle} の公開株予想を分析し、NISA・投資信託の売買判断をサポートします
          </div>
        </header>

        <nav style={{ display: "flex", gap: 6, marginBottom: 18, overflowX: "auto" }}>
          {tabs.map(([k, label]) => (
            <button
              key={k} onClick={() => setTab(k)}
              style={{
                padding: "8px 14px", borderRadius: 20, fontSize: 12, fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap",
                border: `1px solid ${tab === k ? INK : BORDER}`,
                background: tab === k ? INK : "transparent",
                color: tab === k ? "#fff" : SUB,
              }}
            >
              {label}
            </button>
          ))}
        </nav>

        {tab === "dash" && <Dashboard profile={profile} holdings={holdings} />}
        {tab === "signals" && <Signals />}
        {tab === "portfolio" && <Portfolio holdings={holdings} setHoldings={setHoldings} />}
        {tab === "settings" && <Settings profile={profile} setProfile={setProfile} />}

        <div style={{ ...card, background: "#fdf6ec", borderColor: "#ecd9b8" }}>
          <h2 style={{ ...h2, color: WARN }}>⚠ 必ずお読みください</h2>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {CAVEATS.map((c, i) => (
              <li key={i} style={{ fontSize: 11.5, color: SUB, lineHeight: 1.8, marginBottom: 4 }}>{c}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
