import { ReactNode, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { DEFAULT_THEME_COLOR, applyThemeColor, isThemeColor } from "@/lib/theme/presets";

interface ThemeProviderProps {
  children: ReactNode;
}

// ログイン中ユーザーのtheme_colorに応じてCSS変数（--color-primary-*）を切り替える。
// 未ログイン時・未設定時はデフォルト（indigo、globals.cssの初期値と同じ）のまま。
export function ThemeProvider({ children }: ThemeProviderProps) {
  const { user } = useAuth();
  const themeColor = isThemeColor(user?.theme_color) ? user.theme_color : DEFAULT_THEME_COLOR;

  useEffect(() => {
    applyThemeColor(themeColor);
  }, [themeColor]);

  return <>{children}</>;
}
