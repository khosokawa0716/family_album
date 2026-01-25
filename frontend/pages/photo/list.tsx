import { usePhotoList } from "@/hooks/usePhotoList";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";
import { formatDate } from "@/utils/date";
import PageHeader from "@/components/PageHeader";
import { AuthGuard } from "@/components/AuthGuard";

/**
 * 写真一覧ページ（無限スクロール対応）
 * 
 * このコンポーネントは以下の機能を提供します：
 * - 写真の一覧表示（グリッドレイアウト）
 * - カテゴリによるフィルタリング
 * - 無限スクロールによる自動読み込み
 * - 手動での追加読み込み（オプション）
 */
export default function PhotoList() {
  // === カスタムフックからデータと関数を取得 ===
  const { 
    photos,              // 表示する写真データの配列
    categories,          // 利用可能なカテゴリ一覧
    loading,             // 現在データを読み込み中かどうか
    hasMore,             // まだ読み込めるデータがあるかどうか
    selectedCategory,    // 現在選択されているカテゴリ
    setSelectedCategory, // カテゴリ選択を変更する関数
    loadMorePhotos       // 追加の写真を読み込む関数
  } = usePhotoList();

  // === 無限スクロール用の監視要素を設定 ===
  // この要素が画面に表示されると自動的に次のページが読み込まれます
  const sentinelRef = useInfiniteScroll({
    hasMore,           // まだ読み込めるデータがある場合のみ監視
    loading,           // 読み込み中は重複リクエストを防ぐ
    onLoadMore: loadMorePhotos, // スクロール時に実行される関数
    threshold: 200,    // 画面下端から200px手前で読み込み開始
  });

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        {/* === ページヘッダー === */}
        <PageHeader title="Photo List">
          {/* 将来的にボタンなどを追加予定 */}
          {/* <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium">
            Add Photo
          </button> */}
        </PageHeader>

        {/* === フィルター機能 === */}
        <div className="max-w-7xl mx-auto px-2 sm:px-6 lg:px-8 py-3 sm:py-6">
          <div className="bg-white rounded-lg shadow p-3 sm:p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* カテゴリフィルター（タブスタイル） */}
              <div>
                <div
                  role="radiogroup"
                  aria-label="カテゴリを選択"
                  className="flex flex-wrap gap-2"
                >
                  {/* 「すべて」タブ */}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={selectedCategory === "すべて"}
                    onClick={() => {
                      console.log("カテゴリ変更: すべて");
                      setSelectedCategory("すべて");
                    }}
                    className={`
                      min-h-[44px] px-4 py-2 rounded-lg text-sm font-medium
                      border-2 transition-colors
                      ${selectedCategory === "すべて"
                        ? "bg-indigo-600 text-white border-indigo-600"
                        : "bg-white text-gray-700 border-gray-300 hover:border-indigo-400 hover:bg-indigo-50"
                      }
                    `}
                  >
                    すべて
                  </button>
                  {/* 各カテゴリタブ */}
                  {categories.map((category) => (
                    <button
                      key={category.id}
                      type="button"
                      role="radio"
                      aria-checked={selectedCategory === String(category.id)}
                      onClick={() => {
                        console.log("カテゴリ変更:", category.id);
                        setSelectedCategory(String(category.id));
                      }}
                      className={`
                        min-h-[44px] px-4 py-2 rounded-lg text-sm font-medium
                        border-2 transition-colors
                        ${selectedCategory === String(category.id)
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
              
              {/* 日付フィルター（将来実装予定のためコメントアウト） */}
              {/* <div>
                <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-2">
                  Date
                </label>
                <input
                  type="month"
                  id="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div> */}
            </div>
          </div>
        </div>

        {/* === 写真グリッド === */}
        <div className="max-w-7xl mx-auto px-2 sm:px-6 lg:px-8 pb-6 sm:pb-12">
          {/* グリッドレイアウト：画面サイズに応じて列数を調整 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-6">
            {photos.map((photo) => (
              <div
                key={photo.id}
                className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => {
                  console.log("写真詳細ページへ移動:", photo.id);
                  window.location.href = `/photo/detail/${photo.id}`;
                }}
              >
                {/* 写真のサムネイル画像 */}
                <img
                  src={photo.thumbnail_path || ""}
                  alt={photo.title || "Photo"}
                  className="w-full h-48 object-cover rounded-t-lg"
                  onError={(e) => {
                    console.error("画像読み込みエラー:", photo.id);
                    // エラー時の代替画像設定などを将来実装予定
                  }}
                />
                
                {/* 写真の情報 */}
                <div className="p-3 sm:p-4">
                  <h3 className="text-lg font-medium text-gray-900">
                    {photo.title || "無題"}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {photo.description || "説明がありません"}
                  </p>
                  {/* 投稿日の表示 */}
                  <span className="inline-block bg-indigo-100 text-indigo-800 text-xs px-2 py-1 rounded-full mt-2">
                    {formatDate(photo.create_date)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* === 無限スクロール用の監視要素 === */}
          {/* この要素が画面に表示されると自動的に次のページが読み込まれます */}
          <div ref={sentinelRef} className="h-10" />

          {/* === ローディング表示 === */}
          {loading && (
            <div className="text-center py-8">
              <div className="inline-flex items-center">
                {/* 回転するスピナーアイコン */}
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
                  <path 
                    className="opacity-75" 
                    fill="currentColor" 
                    d="M4 12a8 8 0 018-8v8H4z" 
                  />
                </svg>
                <span className="text-gray-600">読み込み中...</span>
              </div>
            </div>
          )}

          {/* === 全件読み込み完了メッセージ === */}
          {!hasMore && photos.length > 0 && (
            <div className="text-center py-8">
              <p className="text-gray-500">
                すべての写真を読み込みました ({photos.length}件)
              </p>
            </div>
          )}

          {/* === データが存在しない場合のメッセージ === */}
          {!loading && photos.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">
                写真が見つかりませんでした
              </p>
              <p className="text-gray-400 text-sm mt-2">
                フィルター条件を変更するか、新しい写真をアップロードしてください
              </p>
            </div>
          )}

          {/* === 手動読み込みボタン（オプション） === */}
          {/* 無限スクロールが動作しない環境やユーザビリティ向上のための代替手段 */}
          {hasMore && !loading && photos.length > 0 && (
            <div className="text-center mt-8">
              <button
                onClick={() => {
                  console.log("手動で追加読み込みを実行");
                  loadMorePhotos();
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
