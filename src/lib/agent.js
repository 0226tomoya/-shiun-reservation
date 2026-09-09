// 資産運用アシストエージェント — 提案ロジック
// Serenity シグナル × 新NISA 制度 × ユーザープロファイルから
// ルールベースの売買サポート提案を生成する。

import { SIGNALS, THEME_FUNDS, themeGroup } from "../data/serenitySignals.js";

// ---- 新NISA (2024〜) 制度定数 (単位: 円) ----
export const NISA = {
  TSUMITATE_ANNUAL: 1_200_000, // つみたて投資枠 年間上限
  GROWTH_ANNUAL: 2_400_000, // 成長投資枠 年間上限
  LIFETIME: 18_000_000, // 生涯非課税限度額 (簿価ベース)
  GROWTH_LIFETIME: 12_000_000, // うち成長投資枠の上限
};

export const RISK_PRESETS = {
  low: { label: "安定重視", core: 0.9, theme: 0.1, single: 0 },
  mid: { label: "バランス", core: 0.75, theme: 0.2, single: 0.05 },
  high: { label: "積極", core: 0.55, theme: 0.3, single: 0.15 },
};

export const yen = (n) =>
  "¥" + Math.round(n).toLocaleString("ja-JP");

// ---- テーマスコア: conviction × 鮮度 (6ヶ月半減) ----
export function themeScores(now = new Date()) {
  const scores = {};
  for (const s of SIGNALS) {
    const months =
      (now - new Date(s.date)) / (1000 * 60 * 60 * 24 * 30.44);
    const recency = Math.pow(0.5, Math.max(0, months) / 6);
    const g = themeGroup(s.theme);
    if (!scores[g]) scores[g] = { score: 0, tickers: [] };
    scores[g].score += s.conviction * recency * (s.direction === "bull" ? 1 : -1);
    scores[g].tickers.push(s.ticker);
  }
  return Object.entries(scores)
    .map(([theme, v]) => ({ theme, score: v.score, tickers: [...new Set(v.tickers)] }))
    .sort((a, b) => b.score - a.score);
}

// ---- NISA 枠の残高計算 ----
export function nisaRoom(profile) {
  const tsumitateLeft = Math.max(0, NISA.TSUMITATE_ANNUAL - profile.usedTsumitate);
  const growthLeft = Math.max(0, NISA.GROWTH_ANNUAL - profile.usedGrowth);
  const lifetimeLeft = Math.max(0, NISA.LIFETIME - profile.lifetimeUsed);
  const growthLifetimeLeft = Math.max(0, NISA.GROWTH_LIFETIME - profile.lifetimeGrowthUsed);
  return { tsumitateLeft, growthLeft, lifetimeLeft, growthLifetimeLeft };
}

// ---- 買い提案 ----
export function buySuggestions(profile) {
  const risk = RISK_PRESETS[profile.risk] || RISK_PRESETS.mid;
  const room = nisaRoom(profile);
  const monthsLeft = Math.max(1, 12 - new Date().getMonth()); // 今年の残り月数
  const out = [];

  // 1. コア: つみたて投資枠でインデックス積立
  const coreBudget = profile.monthlyBudget * risk.core;
  const tsumitateMonthly = Math.min(coreBudget, room.tsumitateLeft / monthsLeft);
  if (tsumitateMonthly > 0) {
    out.push({
      kind: "core",
      account: "つみたて投資枠",
      amount: tsumitateMonthly,
      unit: "月額",
      items: THEME_FUNDS["コア"],
      reason:
        "資産形成の土台は低コストの全世界/米国インデックスの定額積立。Serenity シグナルの成否に関わらず継続を推奨。",
    });
  } else if (room.tsumitateLeft <= 0) {
    out.push({
      kind: "info",
      account: "つみたて投資枠",
      amount: 0,
      unit: "",
      items: [],
      reason: "今年のつみたて投資枠は使い切っています。来年1月に枠が復活します。",
    });
  }

  // 2. サテライト: 成長投資枠でテーマ投信/ETF (Serenity 上位テーマ)
  const scores = themeScores();
  const themeBudget = profile.monthlyBudget * risk.theme;
  const growthMonthly = Math.min(themeBudget, room.growthLeft / monthsLeft, room.growthLifetimeLeft / monthsLeft);
  if (growthMonthly > 0 && risk.theme > 0) {
    const top = scores.slice(0, 2);
    for (const t of top) {
      const funds = THEME_FUNDS[t.theme] || [];
      if (!funds.length) continue;
      out.push({
        kind: "satellite",
        account: "成長投資枠",
        amount: (growthMonthly / top.length),
        unit: "月額",
        items: funds,
        reason: `Serenity の直近シグナルが最も集中しているテーマ「${t.theme}」(関連言及: ${t.tickers.join(", ")})。個別株より投信/ETFで面を取る方が下振れが緩やか。`,
      });
    }
  }

  // 3. 個別株サテライト (積極のみ・上限厳守)
  if (risk.single > 0 && room.growthLeft > 0) {
    const singleBudget = profile.monthlyBudget * risk.single;
    out.push({
      kind: "single",
      account: "成長投資枠",
      amount: singleBudget,
      unit: "月額上限",
      items: SIGNALS.filter((s) => s.conviction >= 4 && s.direction === "bull")
        .slice(0, 4)
        .map((s) => ({ name: `${s.ticker} ${s.name}`, type: "個別株", account: "growth" })),
      reason:
        "Serenity 高確信銘柄への直接投資。すでに数倍化した銘柄が多く高値掴みリスク大。1銘柄あたり総資産の5%以内・言及直後の急騰への飛び乗りは避けること。",
    });
  }

  return out;
}

// ---- 売り/見直し提案 (保有ポートフォリオに対して) ----
export function sellSuggestions(holdings) {
  const out = [];
  const total = holdings.reduce((a, h) => a + h.value, 0) || 1;
  const bullTickers = new Set(
    SIGNALS.filter((s) => s.direction === "bull").map((s) => s.ticker)
  );

  for (const h of holdings) {
    const gain = h.cost > 0 ? (h.value - h.cost) / h.cost : 0;
    const weight = h.value / total;
    const tags = [];

    if (gain >= 1.0) {
      tags.push({
        level: "action",
        text: `+${Math.round(gain * 100)}% と急騰。Serenity 言及銘柄は転載による過熱を含むため、25〜50% の段階利確を検討 (NISA内なら利益は非課税)。`,
      });
    } else if (gain <= -0.2) {
      tags.push({
        level: "warn",
        text: `${Math.round(gain * 100)}% の含み損。NISA口座は損益通算・繰越控除ができないため、テーゼが崩れたなら早めの見直しが合理的。`,
      });
    }
    if (weight >= 0.2) {
      tags.push({
        level: "warn",
        text: `ポートフォリオの ${Math.round(weight * 100)}% に集中。1銘柄20%超は分散を推奨。`,
      });
    }
    if (h.ticker && !bullTickers.has(h.ticker) && h.serenity) {
      tags.push({
        level: "info",
        text: "直近の Serenity 投稿では言及が確認できません。テーゼ継続かを一次情報で確認してください。",
      });
    }
    if (h.account !== "taxable" && gain >= 1.0) {
      tags.push({
        level: "info",
        text: "NISA枠は売却しても翌年まで復活しません (簿価ベースで翌年復活)。年内の枠再利用はできない点に注意。",
      });
    }
    if (tags.length) out.push({ holding: h, gain, weight, tags });
  }
  return out.sort((a, b) => Math.abs(b.gain) - Math.abs(a.gain));
}
