// Serenity (@aleabitoreddit) の X 上の公開銘柄言及データ
//
// X 本体は認証なしで取得できないため、本データは公開トラッカー
// (trackserenity.com / serenitystock.com / semiconstocks.com)、
// 報道 (PANews / Odaily / BigGo Finance)、および検索経由で確認できた
// 投稿内容から再構成したスナップショットです (2026-09 時点)。
// X API v2 のベアラートークンを設定すればライブ取得に置き換えられます
// (README「データ更新」参照)。

export const ACCOUNT = {
  handle: "@aleabitoreddit",
  name: "Serenity",
  alias: "白毛股神 / 白髪の株神",
  profile:
    "元 AI 研究者を自称する半導体・AI サプライチェーン投資 KOL。Reddit (u/AleaBito) 出身。" +
    "AI インフラの供給網を逆算し、見落とされた「ボトルネック銘柄」を探す手法で知られる。",
  followers: "75万+",
};

// direction: "bull" | "bear" / conviction: 1〜5 (投稿の熱量・繰り返し言及から推定)
export const SIGNALS = [
  {
    id: "axti-2022",
    date: "2022-06-01",
    ticker: "AXTI",
    name: "AXT Inc.",
    market: "NASDAQ",
    theme: "InP基板 (光半導体)",
    direction: "bull",
    conviction: 5,
    thesis:
      "リン化インジウム (InP) 基板メーカー。高速光リンク用レーザーの上流。Reddit時代に$12→$70を的中させた原点の銘柄で、本人が「史上最高のテーゼ」と呼ぶ。",
    performance: "2026年再言及後 $15.61 → $140.83 (約9.0倍)",
    source: "PANews / trackserenity.com",
  },
  {
    id: "sive-2026-03",
    date: "2026-03-16",
    ticker: "SIVE",
    name: "Sivers Semiconductors",
    market: "STO (スウェーデン)",
    theme: "InPレーザー (光半導体)",
    direction: "bull",
    conviction: 5,
    thesis:
      "小型のスウェーデン InP レーザーメーカー。光トランシーバー供給網の「真の上流チョークポイント」とする最大・最愛のポジション。",
    performance: "言及後 約19.6倍 (2026-06 時点で +1900% と本人投稿)",
    source: "KuCoin News / 本人投稿 (2026-06-13)",
  },
  {
    id: "aaoi-2026",
    date: "2026-04-10",
    ticker: "AAOI",
    name: "Applied Optoelectronics",
    market: "NASDAQ",
    theme: "光トランシーバー組立",
    direction: "bull",
    conviction: 4,
    thesis: "光トランシーバーの組立レイヤー。AIデータセンターの光化需要の受け皿。",
    performance: "$35.57 → $181.49 (約5.1倍)",
    source: "KuCoin News",
  },
  {
    id: "aehr-2026",
    date: "2026-05-20",
    ticker: "AEHR",
    name: "Aehr Test Systems",
    market: "NASDAQ",
    theme: "フォトニクス検査装置",
    direction: "bull",
    conviction: 3,
    thesis:
      "フォトニクス供給網の検査工程。大手光トランシーバー企業からの新規クオリフィケーション受注を材料視。",
    performance: "—",
    source: "検索スニペット (本人投稿)",
  },
  {
    id: "rpi-2026",
    date: "2026-05-01",
    ticker: "RPI",
    name: "Raspberry Pi Holdings",
    market: "LSE",
    theme: "エッジAI/ロボティクス",
    direction: "bull",
    conviction: 4,
    thesis:
      "OpenClaw / Picoclaw / Nanobot 系の需要で成長率が 48〜55% に加速するとの読み。",
    performance: "言及後 約 +175%",
    source: "KuCoin News",
  },
  {
    id: "lng-2026",
    date: "2026-06-05",
    ticker: "LNG",
    name: "Cheniere Energy",
    market: "NYSE",
    theme: "エネルギー (LNG輸出)",
    direction: "bull",
    conviction: 3,
    thesis: "地政学的な供給混乱の「最もクリーンな」米国LNG輸出の受益者。",
    performance: "—",
    source: "検索スニペット (本人投稿)",
  },
  {
    id: "lite-2026",
    date: "2026-06-15",
    ticker: "LITE",
    name: "Lumentum",
    market: "NASDAQ",
    theme: "光部品 (レーザー)",
    direction: "bull",
    conviction: 3,
    thesis: "光通信・レーザー部品。フォトニクス供給網テーゼの一角として頻出。",
    performance: "—",
    source: "serenitystock.com (トラッカー)",
  },
  {
    id: "cohr-2026",
    date: "2026-06-15",
    ticker: "COHR",
    name: "Coherent",
    market: "NYSE",
    theme: "光部品 (レーザー)",
    direction: "bull",
    conviction: 3,
    thesis: "光トランシーバー/レーザーの大手。フォトニクステーマの中核言及銘柄。",
    performance: "—",
    source: "serenitystock.com (トラッカー)",
  },
  {
    id: "mrvl-2026",
    date: "2026-07-01",
    ticker: "MRVL",
    name: "Marvell Technology",
    market: "NASDAQ",
    theme: "AIネットワーキング半導体",
    direction: "bull",
    conviction: 3,
    thesis: "AIデータセンターの光DSP・カスタムシリコン。供給網テーゼの下流側。",
    performance: "—",
    source: "serenitystock.com (トラッカー)",
  },
  {
    id: "nbis-2026",
    date: "2026-07-10",
    ticker: "NBIS",
    name: "Nebius Group",
    market: "NASDAQ",
    theme: "AIインフラ (GPUクラウド)",
    direction: "bull",
    conviction: 3,
    thesis: "AIコンピュートインフラの新興プレイヤーとして言及。",
    performance: "—",
    source: "serenitystock.com (トラッカー)",
  },
  {
    id: "leaderdrive-2026",
    date: "2026-06-01",
    ticker: "688017",
    name: "緑的諧波 (Leaderdrive)",
    market: "上海STAR",
    theme: "ロボティクス (減速機)",
    direction: "bull",
    conviction: 4,
    thesis:
      "ヒューマノイドロボット用ハーモニック減速機。投稿が中国国内に転載され連続ストップ高を誘発した銘柄。",
    performance: "連続20%ストップ高 (2026-06)",
    source: "BigGo Finance / 東方財富網",
  },
  {
    id: "eastgroup-2026",
    date: "2026-06-01",
    ticker: "300376",
    name: "易事特 (East Group)",
    market: "深圳",
    theme: "電源設備 (AI電力)",
    direction: "bull",
    conviction: 3,
    thesis: "AIデータセンター向け電源設備。転載で急騰した中国A株言及の一つ。",
    performance: "連続ストップ高 (2026-06)",
    source: "BigGo Finance",
  },
];

// テーマ → NISA で買える連動しやすい投資信託/ETF の対応表 (例示)
export const THEME_FUNDS = {
  半導体: [
    { name: "ニッセイSOX指数インデックスファンド (米国半導体)", account: "growth", type: "投資信託" },
    { name: "グローバルX 半導体関連 ETF (2644)", account: "growth", type: "ETF" },
  ],
  フォトニクス: [
    { name: "野村 世界業種別投資シリーズ (半導体)", account: "growth", type: "投資信託" },
  ],
  AIインフラ: [
    { name: "グローバルAIファンド", account: "growth", type: "投資信託" },
    { name: "iFreeNEXT FANG+インデックス", account: "growth", type: "投資信託" },
  ],
  ロボティクス: [
    { name: "グローバル・ロボティクス株式ファンド", account: "growth", type: "投資信託" },
  ],
  エネルギー: [
    { name: "iシェアーズ グローバルエネルギーETF等 (特定口座推奨)", account: "growth", type: "ETF" },
  ],
  コア: [
    { name: "eMAXIS Slim 全世界株式 (オール・カントリー)", account: "tsumitate", type: "投資信託" },
    { name: "eMAXIS Slim 米国株式 (S&P500)", account: "tsumitate", type: "投資信託" },
  ],
};

// シグナルの theme 文字列 → THEME_FUNDS のキーへの丸め
export function themeGroup(theme) {
  if (/InP|光|フォトニクス|トランシーバー/.test(theme)) return "フォトニクス";
  if (/半導体|ネットワーキング/.test(theme)) return "半導体";
  if (/AIインフラ|GPU|電力|電源/.test(theme)) return "AIインフラ";
  if (/ロボ|エッジ/.test(theme)) return "ロボティクス";
  if (/エネルギー|LNG/.test(theme)) return "エネルギー";
  return "半導体";
}

export const CAVEATS = [
  "Serenity の成績 (2026年 +4,502% 等) は本人の自己申告で、第三者検証はありません。公開されるのは主に成功例です。",
  "独立系の定量バックテスト (fxcryptobots, BULL 383件) では、言及銘柄の等ウェイトポートフォリオは半導体セクターETF比で平均 -37% のアンダーパフォームという報告もあります。",
  "投稿の転載による急騰は「越境的な相場操縦の新形態になり得る」と法律専門家が警告しています。急騰後の高値掴みリスクに注意してください。",
  "本アプリは情報整理ツールであり、金融商品取引法上の投資助言ではありません。売買の最終判断はご自身の責任で行ってください。",
];
