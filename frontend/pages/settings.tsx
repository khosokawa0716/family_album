import { useEffect, useRef, useState } from "react";
import PageHeader from "@/components/PageHeader";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/hooks/useAuth";
import { userService } from "@/services/users";
import Avatar from "@/components/Avatar";
import { getDisplayName } from "@/utils/user";
import { THEME_COLORS, THEME_COLOR_LABELS, THEME_PRESETS, DEFAULT_THEME_COLOR, applyThemeColor, isThemeColor, type ThemeColor } from "@/lib/theme/presets";

export default function Settings() {
  const { user, checkAuth } = useAuth();
  const [nickname, setNickname] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [themeSaving, setThemeSaving] = useState(false);
  const [themeError, setThemeError] = useState<string | null>(null);

  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (user) {
      setNickname(user.nickname || "");
    }
  }, [user]);

  useEffect(() => {
    return () => {
      if (avatarPreview) {
        URL.revokeObjectURL(avatarPreview);
      }
    };
  }, [avatarPreview]);

  const handleAvatarFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarError(null);
    setAvatarFile(file);
    setAvatarPreview((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(file);
    });
  };

  const handleAvatarUpload = async () => {
    if (!user || !avatarFile) return;
    setAvatarUploading(true);
    setAvatarError(null);
    try {
      await userService.uploadAvatar(user.id, avatarFile);
      await checkAuth();
      setAvatarFile(null);
      setAvatarPreview((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch {
      setAvatarError("プロフィール画像のアップロードに失敗しました");
    } finally {
      setAvatarUploading(false);
    }
  };

  const handleAvatarDelete = async () => {
    if (!user) return;
    setAvatarUploading(true);
    setAvatarError(null);
    try {
      await userService.deleteAvatar(user.id);
      await checkAuth();
    } catch {
      setAvatarError("プロフィール画像の削除に失敗しました");
    } finally {
      setAvatarUploading(false);
    }
  };

  const handleThemeColorSelect = async (color: ThemeColor) => {
    if (!user || themeSaving) return;
    setThemeSaving(true);
    setThemeError(null);
    try {
      await userService.updateUser(user.id, { theme_color: color });
      applyThemeColor(color);
      await checkAuth();
    } catch {
      setThemeError("テーマカラーの更新に失敗しました");
    } finally {
      setThemeSaving(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await userService.updateUser(user.id, { nickname: nickname.trim() || null });
      await checkAuth();
      setSuccess(true);
    } catch {
      setError("ニックネームの更新に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="設定" />

        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-1">プロフィール画像の設定</h2>
            <p className="text-sm text-gray-500 mb-4">
              投稿者表示やコメント欄に表示されるプロフィール画像を設定できます。未設定の場合はイニシャルが表示されます。
            </p>

            <div className="flex items-center space-x-4">
              <Avatar
                avatarPath={avatarPreview || user?.avatar_path}
                displayName={getDisplayName(user?.user_name, user?.nickname)}
                seed={user?.id ?? "user"}
                size={64}
              />
              <div className="flex-1">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp,image/heic,image/heif"
                  onChange={handleAvatarFileChange}
                  className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-[var(--color-primary-50)] file:text-[var(--color-primary-700)] hover:file:bg-[var(--color-primary-100)]"
                />
                <div className="mt-3 flex space-x-2">
                  <button
                    type="button"
                    onClick={handleAvatarUpload}
                    disabled={!avatarFile || avatarUploading}
                    className="px-4 py-2 bg-[var(--color-primary-600)] hover:bg-[var(--color-primary-700)] text-white rounded-md text-sm font-medium disabled:opacity-50"
                  >
                    {avatarUploading ? "処理中..." : "アップロード"}
                  </button>
                  {user?.avatar_path && (
                    <button
                      type="button"
                      onClick={handleAvatarDelete}
                      disabled={avatarUploading}
                      className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md text-sm font-medium disabled:opacity-50"
                    >
                      削除
                    </button>
                  )}
                </div>
              </div>
            </div>

            {avatarError && (
              <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
                {avatarError}
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-1">テーマカラーの設定</h2>
            <p className="text-sm text-gray-500 mb-4">
              自分の画面のボタンやリンクなどの配色を変更できます。他のユーザーの画面には影響しません。
            </p>

            <div className="flex flex-wrap gap-3">
              {THEME_COLORS.map((color) => {
                const selected = (isThemeColor(user?.theme_color) ? user.theme_color : DEFAULT_THEME_COLOR) === color;
                return (
                  <button
                    key={color}
                    type="button"
                    onClick={() => handleThemeColorSelect(color)}
                    disabled={themeSaving}
                    aria-pressed={selected}
                    aria-label={THEME_COLOR_LABELS[color]}
                    title={THEME_COLOR_LABELS[color]}
                    className={`w-10 h-10 rounded-full border-2 disabled:opacity-50 ${
                      selected ? "border-gray-900" : "border-transparent"
                    }`}
                    style={{ backgroundColor: THEME_PRESETS[color]["600"] }}
                  />
                );
              })}
            </div>

            {themeError && (
              <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
                {themeError}
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-1">表示名の設定</h2>
            <p className="text-sm text-gray-500 mb-4">
              ニックネームを設定すると、投稿者名やコメント欄でユーザー名の代わりに表示されます。空欄にするとユーザー名が表示されます。
            </p>

            <form onSubmit={handleSubmit}>
              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="user-name"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    ユーザー名
                  </label>
                  <input
                    id="user-name"
                    type="text"
                    value={user?.user_name || ""}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-500"
                    disabled
                  />
                </div>
                <div>
                  <label htmlFor="nickname" className="block text-sm font-medium text-gray-700 mb-1">
                    ニックネーム
                  </label>
                  <input
                    id="nickname"
                    type="text"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    maxLength={64}
                    placeholder="表示したい名前を入力"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-[var(--color-primary-500)] focus:border-[var(--color-primary-500)]"
                  />
                </div>
              </div>

              {error && (
                <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
                  {error}
                </div>
              )}
              {success && (
                <div className="mt-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded text-sm">
                  ニックネームを更新しました
                </div>
              )}

              <div className="mt-6 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-[var(--color-primary-600)] hover:bg-[var(--color-primary-700)] text-white rounded-md text-sm font-medium disabled:opacity-50"
                >
                  {saving ? "保存中..." : "保存"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
