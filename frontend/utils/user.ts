// ニックネームが設定されていればそれを、なければuser_nameを表示名として返す
export const getDisplayName = (
  userName: string | null | undefined,
  nickname?: string | null
): string => {
  return nickname?.trim() ? nickname : userName || "不明";
};

// アバター未設定時のイニシャルアバターに使う背景色パレット
const AVATAR_COLORS = [
  "#EF4444", "#F97316", "#F59E0B", "#84CC16", "#10B981",
  "#14B8A6", "#06B6D4", "#3B82F6", "#6366F1", "#8B5CF6",
  "#A855F7", "#EC4899",
];

// 表示名の先頭1文字（イニシャルアバター用）
export const getInitial = (displayName: string): string => {
  const trimmed = displayName.trim();
  return trimmed ? trimmed.charAt(0).toUpperCase() : "?";
};

// ユーザーごとに安定した背景色を返す（ユーザーIDなどをseedに使う）
export const getAvatarColor = (seed: string): string => {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = seed.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
};
