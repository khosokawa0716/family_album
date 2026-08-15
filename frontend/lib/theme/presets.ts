// ユーザーが選択できるテーマカラーのプリセット一覧。
// backend/schemas.py の ALLOWED_THEME_COLORS と一致させること。
export const THEME_COLORS = ["indigo", "blue", "emerald", "rose", "amber", "violet"] as const;

export type ThemeColor = (typeof THEME_COLORS)[number];

export const DEFAULT_THEME_COLOR: ThemeColor = "indigo";

export function isThemeColor(value: string | null | undefined): value is ThemeColor {
  return !!value && (THEME_COLORS as readonly string[]).includes(value);
}

// documentRoot（:root）のCSS変数を指定したプリセットの値に切り替える。
// useAuth()はコンポーネントごとに独立した状態を持つフックのため、ThemeProvider内のuser状態は
// 他コンポーネントでのcheckAuth()呼び出しでは更新されない。設定画面での保存直後に画面へ
// 即時反映させるため、ThemeProviderのuseEffectと保存後の両方からこの関数を呼び出す。
export function applyThemeColor(color: ThemeColor): void {
  const preset = THEME_PRESETS[color];
  const root = document.documentElement;
  Object.entries(preset).forEach(([shade, hex]) => {
    root.style.setProperty(`--color-primary-${shade}`, hex);
  });
}

export const THEME_COLOR_LABELS: Record<ThemeColor, string> = {
  indigo: "インディゴ（標準）",
  blue: "ブルー",
  emerald: "エメラルド",
  rose: "ローズ",
  amber: "アンバー",
  violet: "バイオレット",
};

// 各プリセットのTailwind標準パレット準拠のシェード値。
// ThemeProviderがこれをCSS変数（--color-primary-*）としてrootに設定する。
const SHADES = ["50", "100", "400", "500", "600", "700", "800", "900"] as const;
type Shade = (typeof SHADES)[number];

export const THEME_PRESETS: Record<ThemeColor, Record<Shade, string>> = {
  indigo: {
    "50": "#eef2ff",
    "100": "#e0e7ff",
    "400": "#818cf8",
    "500": "#6366f1",
    "600": "#4f46e5",
    "700": "#4338ca",
    "800": "#3730a3",
    "900": "#312e81",
  },
  blue: {
    "50": "#eff6ff",
    "100": "#dbeafe",
    "400": "#60a5fa",
    "500": "#3b82f6",
    "600": "#2563eb",
    "700": "#1d4ed8",
    "800": "#1e40af",
    "900": "#1e3a8a",
  },
  emerald: {
    "50": "#ecfdf5",
    "100": "#d1fae5",
    "400": "#34d399",
    "500": "#10b981",
    "600": "#059669",
    "700": "#047857",
    "800": "#065f46",
    "900": "#064e3b",
  },
  rose: {
    "50": "#fff1f2",
    "100": "#ffe4e6",
    "400": "#fb7185",
    "500": "#f43f5e",
    "600": "#e11d48",
    "700": "#be123c",
    "800": "#9f1239",
    "900": "#881337",
  },
  amber: {
    "50": "#fffbeb",
    "100": "#fef3c7",
    "400": "#fbbf24",
    "500": "#f59e0b",
    "600": "#d97706",
    "700": "#b45309",
    "800": "#92400e",
    "900": "#78350f",
  },
  violet: {
    "50": "#f5f3ff",
    "100": "#ede9fe",
    "400": "#a78bfa",
    "500": "#8b5cf6",
    "600": "#7c3aed",
    "700": "#6d28d9",
    "800": "#5b21b6",
    "900": "#4c1d95",
  },
};
