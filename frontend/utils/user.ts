// ニックネームが設定されていればそれを、なければuser_nameを表示名として返す
export const getDisplayName = (
  userName: string | null | undefined,
  nickname?: string | null
): string => {
  return nickname?.trim() ? nickname : userName || "不明";
};
