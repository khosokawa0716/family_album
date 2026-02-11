import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/router";
import { usePhotoList } from "@/hooks/usePhotoList";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";
import { formatDate } from "@/utils/date";
import PageHeader from "@/components/PageHeader";
import { AuthGuard } from "@/components/AuthGuard";
import { PictureGroupResponse } from "@/types/pictures";

/**
 * 写真一覧ページ（グループ表示・無限スクロール対応）
 */
export default function PhotoList() {
  const router = useRouter();
  const SCROLL_POSITION_KEY = "photo-list-scroll-position";
  const isRestoringScrollRef = useRef(false);
  const isNavigatingToDetailRef = useRef(false);
  const hasRestoredScrollRef = useRef(false);

  const {
    groups,
    categories,
    loading,
    hasMore,
    selectedCategory,
    setSelectedCategory,
    loadMoreGroups,
  } = usePhotoList();

  const sentinelRef = useInfiniteScroll({
    hasMore,
    loading,
    onLoadMore: loadMoreGroups,
    threshold: 200,
  });

  // === スクロール位置の保存・復元 ===
  useEffect(() => {
    const savedPosition = sessionStorage.getItem(SCROLL_POSITION_KEY);
    if (savedPosition && groups.length > 0 && !hasRestoredScrollRef.current) {
      isRestoringScrollRef.current = true;
      hasRestoredScrollRef.current = true;
      sessionStorage.removeItem(SCROLL_POSITION_KEY);

      const timeout = setTimeout(() => {
        window.scrollTo(0, parseInt(savedPosition, 10));
        console.log("スクロール位置を復元:", savedPosition);
        isRestoringScrollRef.current = false;
      }, 100);

      return () => {
        clearTimeout(timeout);
        isRestoringScrollRef.current = false;
      };
    }
  }, [groups.length]);

  useEffect(() => {
    const handleScroll = () => {
      if (isRestoringScrollRef.current || isNavigatingToDetailRef.current) {
        return;
      }
      sessionStorage.setItem(SCROLL_POSITION_KEY, window.scrollY.toString());
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // === 詳細ページへの移動処理 ===
  const handleGroupClick = (groupId: string) => {
    const currentScrollY = window.scrollY.toString();
    sessionStorage.setItem(SCROLL_POSITION_KEY, currentScrollY);
    isNavigatingToDetailRef.current = true;
    console.log("詳細ページへ移動、スクロール位置を保存:", window.scrollY);
    void router.push(`/photo/detail/${groupId}`, undefined, { scroll: false }).finally(() => {
      isNavigatingToDetailRef.current = false;
    });
  };

  // === カテゴリ変更時の処理 ===
  const handleCategoryChange = (category: string) => {
    console.log("カテゴリ変更:", category);
    sessionStorage.removeItem(SCROLL_POSITION_KEY);
    setSelectedCategory(category);
    window.scrollTo(0, 0);
  };

  const totalPhotos = groups.reduce((sum, g) => sum + g.pictures.length, 0);

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="Photo List" />

        {/* === フィルター機能 === */}
        <div className="max-w-7xl mx-auto px-2 sm:px-6 lg:px-8 py-3 sm:py-6">
          <div className="bg-white rounded-lg shadow p-3 sm:p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div role="radiogroup" aria-label="カテゴリを選択" className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    role="radio"
                    aria-checked={selectedCategory === "すべて"}
                    onClick={() => handleCategoryChange("すべて")}
                    className={`
                      min-h-[44px] px-4 py-2 rounded-lg text-sm font-medium
                      border-2 transition-colors
                      ${
                        selectedCategory === "すべて"
                          ? "bg-indigo-600 text-white border-indigo-600"
                          : "bg-white text-gray-700 border-gray-300 hover:border-indigo-400 hover:bg-indigo-50"
                      }
                    `}
                  >
                    すべて
                  </button>
                  {categories.map((category) => (
                    <button
                      key={category.id}
                      type="button"
                      role="radio"
                      aria-checked={selectedCategory === String(category.id)}
                      onClick={() => handleCategoryChange(String(category.id))}
                      className={`
                        min-h-[44px] px-4 py-2 rounded-lg text-sm font-medium
                        border-2 transition-colors
                        ${
                          selectedCategory === String(category.id)
                            ? "bg-indigo-600 text-white border-indigo-600"
                            : "bg-white text-gray-700 border-gray-300 hover:border-indigo-400 hover:bg-indigo-50"
                        }
                      `}
                    >
                      {category.name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* === 写真グリッド === */}
        <div className="max-w-7xl mx-auto px-2 sm:px-6 lg:px-8 pb-6 sm:pb-12">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-6">
            {groups.map((group) => (
              <GroupCard
                key={group.group_id}
                group={group}
                onClick={() => handleGroupClick(group.group_id)}
              />
            ))}
          </div>

          {/* === 無限スクロール用の監視要素 === */}
          <div ref={sentinelRef} className="h-10" />

          {/* === ローディング表示 === */}
          {loading && (
            <div className="text-center py-8">
              <div className="inline-flex items-center">
                <svg
                  className="animate-spin h-5 w-5 mr-3 text-indigo-600"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span className="text-gray-600">読み込み中...</span>
              </div>
            </div>
          )}

          {/* === 全件読み込み完了メッセージ === */}
          {!hasMore && groups.length > 0 && (
            <div className="text-center py-8">
              <p className="text-gray-500">すべての写真を読み込みました ({totalPhotos}件)</p>
            </div>
          )}

          {/* === データが存在しない場合のメッセージ === */}
          {!loading && groups.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">写真が見つかりませんでした</p>
              <p className="text-gray-400 text-sm mt-2">
                フィルター条件を変更するか、新しい写真をアップロードしてください
              </p>
            </div>
          )}

          {/* === 手動読み込みボタン === */}
          {hasMore && !loading && groups.length > 0 && (
            <div className="text-center mt-8">
              <button
                onClick={() => {
                  console.log("手動で追加読み込みを実行");
                  loadMoreGroups();
                }}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-md font-medium transition-colors"
              >
                もっと読み込む
              </button>
            </div>
          )}
        </div>
      </div>
    </AuthGuard>
  );
}

/**
 * グループカードコンポーネント
 * 1枚: 通常サムネイル表示
 * 2枚以上: CSS scroll-snapスライダー + ドットインジケーター
 */
function GroupCard({
  group,
  onClick,
}: {
  group: PictureGroupResponse;
  onClick: () => void;
}) {
  const firstPhoto = group.pictures[0];
  const isMultiple = group.pictures.length > 1;

  if (!isMultiple) {
    // 1枚の場合: 従来どおりのカード
    return (
      <div
        className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer"
        onClick={onClick}
      >
        <img
          src={firstPhoto.thumbnail_path || ""}
          alt={firstPhoto.title || "Photo"}
          className="w-full h-48 object-cover rounded-t-lg"
        />
        <div className="p-3 sm:p-4">
          <h3 className="text-lg font-medium text-gray-900">{firstPhoto.title || "無題"}</h3>
          <p className="text-xs text-gray-500 mt-1">
            投稿者: {firstPhoto.user?.user_name || "不明"}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {firstPhoto.description || "説明がありません"}
          </p>
          <span className="inline-block bg-indigo-100 text-indigo-800 text-xs px-2 py-1 rounded-full mt-2">
            {formatDate(firstPhoto.create_date)}
          </span>
        </div>
      </div>
    );
  }

  // 2枚以上: スライダーカード
  return (
    <div
      className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <ImageSlider group={group} />
      <div className="p-3 sm:p-4">
        <h3 className="text-lg font-medium text-gray-900">{firstPhoto.title || "無題"}</h3>
        <p className="text-xs text-gray-500 mt-1">
          投稿者: {firstPhoto.user?.user_name || "不明"}
        </p>
        <p className="text-sm text-gray-500 mt-1">
          {firstPhoto.description || "説明がありません"}
        </p>
        <span className="inline-block bg-indigo-100 text-indigo-800 text-xs px-2 py-1 rounded-full mt-2">
          {formatDate(firstPhoto.create_date)}
        </span>
      </div>
    </div>
  );
}

/**
 * CSS scroll-snapベースの画像スライダー
 */
function ImageSlider({ group }: { group: PictureGroupResponse }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const index = Math.round(el.scrollLeft / el.clientWidth);
    setActiveIndex(index);
  }, []);

  return (
    <div className="relative">
      {/* スライダー本体 */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex overflow-x-auto snap-x snap-mandatory scrollbar-hide rounded-t-lg"
      >
        {group.pictures.map((photo) => (
          <img
            key={photo.id}
            src={photo.thumbnail_path || ""}
            alt={photo.title || "Photo"}
            className="w-full h-48 object-cover flex-shrink-0 snap-center"
          />
        ))}
      </div>

      {/* 枚数バッジ */}
      <div className="absolute top-2 right-2 bg-black/60 text-white text-xs px-2 py-0.5 rounded-full">
        {group.pictures.length}枚
      </div>

      {/* ドットインジケーター */}
      <div className="absolute bottom-2 left-0 right-0 flex justify-center gap-1.5">
        {group.pictures.map((photo, i) => (
          <span
            key={photo.id}
            className={`w-1.5 h-1.5 rounded-full transition-colors ${
              i === activeIndex ? "bg-white" : "bg-white/50"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
