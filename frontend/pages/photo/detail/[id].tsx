import { useRouter } from "next/router";
import { useState } from "react";
import { Calendar } from "lucide-react";
import { usePhotoDetail } from "@/hooks/usePhotoDetail";
import { useAuth } from "@/hooks/useAuth";
import { formatDate } from "@/utils/date";
import PageHeader from "@/components/PageHeader";
import PhotoModal from "@/components/PhotoModal";
import { AuthGuard } from "@/components/AuthGuard";
import { PictureResponse } from "@/types/pictures";

export default function PhotoDetail() {
  const router = useRouter();
  const { id } = router.query;
  const groupId = typeof id === "string" ? id : "";

  const {
    photos,
    selectedPhoto,
    setSelectedPhoto,
    comments,
    loading,
    commentContent,
    setCommentContent,
    editingCommentId,
    editingContent,
    setEditingContent,
    handleDeletePhoto,
    handleDownloadPhoto,
    handlePostComment,
    startEditComment,
    cancelEditComment,
    handleUpdateComment,
    handleDeleteComment,
    isEditingPhoto,
    editingTitle,
    setEditingTitle,
    editingDescription,
    setEditingDescription,
    startEditPhoto,
    cancelEditPhoto,
    handleUpdatePhoto,
  } = usePhotoDetail(groupId);

  const { user } = useAuth();
  const [modalPhoto, setModalPhoto] = useState<PictureResponse | null>(null);

  if (!id) {
    return (
      <AuthGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <p className="text-gray-500">Invalid photo ID</p>
        </div>
      </AuthGuard>
    );
  }

  if (loading) {
    return (
      <AuthGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <p className="text-gray-500">読み込み中...</p>
        </div>
      </AuthGuard>
    );
  }

  if (photos.length === 0) {
    return (
      <AuthGuard>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <p className="text-gray-500">写真が見つかりませんでした</p>
        </div>
      </AuthGuard>
    );
  }

  const firstPhoto = photos[0];
  const isMultiple = photos.length > 1;

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="Detail">
          <button
            onClick={() => {
              router.push("/photo/list", undefined, { scroll: false });
            }}
            className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium"
          >
            Back
          </button>
        </PageHeader>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* 写真表示エリア */}
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            {isMultiple ? (
              /* 複数枚: grid-cols-2グリッド表示 */
              <div className="grid grid-cols-2 gap-2 mb-4">
                {photos.map((photo) => (
                  <div
                    key={photo.id}
                    className={`relative cursor-pointer rounded-lg overflow-hidden border-2 transition-colors ${
                      selectedPhoto?.id === photo.id
                        ? "border-indigo-500"
                        : "border-transparent hover:border-gray-300"
                    }`}
                    onClick={() => setSelectedPhoto(photo)}
                  >
                    <img
                      src={photo.file_path}
                      alt={photo.title || "Photo"}
                      className="w-full h-48 object-cover hover:opacity-90 transition-opacity"
                    />
                    {selectedPhoto?.id === photo.id && (
                      <div className="absolute top-1 left-1 bg-indigo-500 text-white text-xs px-1.5 py-0.5 rounded">
                        選択中
                      </div>
                    )}
                    <button
                      type="button"
                      className="absolute bottom-1 right-1 bg-black/50 text-white text-xs px-2 py-1 rounded hover:bg-black/70"
                      onClick={(e) => {
                        e.stopPropagation();
                        setModalPhoto(photo);
                      }}
                    >
                      拡大
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              /* 1枚: 従来レイアウト */
              <div className="mb-4">
                <img
                  src={firstPhoto.file_path}
                  alt={firstPhoto.title || "Photo"}
                  className="w-full max-h-96 object-contain cursor-pointer hover:opacity-90 transition-opacity"
                  onClick={() => setModalPhoto(firstPhoto)}
                />
              </div>
            )}

            {/* タイトルと説明（グループ共通） */}
            {isEditingPhoto ? (
              <div className="mb-4 space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">タイトル</label>
                  <input
                    type="text"
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="タイトルを入力"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">説明</label>
                  <textarea
                    value={editingDescription}
                    onChange={(e) => setEditingDescription(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="説明を入力"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleUpdatePhoto}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                  >
                    保存
                  </button>
                  <button
                    onClick={cancelEditPhoto}
                    className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-4 py-2 rounded-md text-sm font-medium"
                  >
                    キャンセル
                  </button>
                </div>
              </div>
            ) : (
              <div className="mb-4">
                {firstPhoto.title && (
                  <h2 className="text-xl font-bold text-gray-900 mb-2">{firstPhoto.title}</h2>
                )}
                <p className="text-sm text-gray-500 mb-1">
                  投稿者: {firstPhoto.user?.user_name || "不明"}
                </p>
                {isMultiple && (
                  <p className="text-sm text-gray-500 mb-1">{photos.length}枚の写真</p>
                )}
                {firstPhoto.description && (
                  <p className="text-gray-600">{firstPhoto.description}</p>
                )}
                {!firstPhoto.title && !firstPhoto.description && (
                  <p className="text-gray-400 italic">タイトル・説明なし</p>
                )}
              </div>
            )}

            {/* 投稿日 */}
            <p className="text-sm text-gray-500 mb-4 inline-flex items-center">
              <Calendar className="h-4 w-4 mr-1" aria-hidden="true" />
              {formatDate(firstPhoto.create_date)}
            </p>

            {/* 操作ボタン */}
            <div className="flex gap-3">
              <button
                onClick={handleDownloadPhoto}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                {isMultiple && selectedPhoto
                  ? "選択中の写真をダウンロード"
                  : "ダウンロード"}
              </button>
              {user?.id === firstPhoto.uploaded_by && !isEditingPhoto && (
                <button
                  onClick={startEditPhoto}
                  className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                >
                  編集
                </button>
              )}
              {user?.type === 10 && (
                <button
                  onClick={handleDeletePhoto}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                >
                  削除
                </button>
              )}
            </div>
          </div>

          {/* コメントエリア */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">コメント一覧</h3>

            {isMultiple && selectedPhoto && (
              <p className="text-sm text-gray-500 mb-3">
                写真 #{photos.findIndex((p) => p.id === selectedPhoto.id) + 1} へのコメント
              </p>
            )}

            {/* コメント一覧 */}
            <div className="space-y-4 mb-6">
              {comments.length === 0 ? (
                <p className="text-gray-500 text-sm">コメントはまだありません</p>
              ) : (
                comments.map((comment) => (
                  <div key={comment.id} className="border border-gray-200 rounded-lg p-4">
                    {editingCommentId === comment.id ? (
                      <div>
                        <textarea
                          value={editingContent}
                          onChange={(e) => setEditingContent(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 mb-2"
                          rows={3}
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleUpdateComment(comment.id)}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded-md text-sm"
                          >
                            保存
                          </button>
                          <button
                            onClick={cancelEditComment}
                            className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-3 py-1 rounded-md text-sm"
                          >
                            キャンセル
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div className="flex items-start justify-between mb-2">
                          <p className="font-medium text-gray-900">{comment.user_name}</p>
                          {user?.id === comment.user_id && (
                            <div className="flex gap-2">
                              <button
                                onClick={() => startEditComment(comment)}
                                className="text-indigo-600 hover:text-indigo-800 text-sm"
                              >
                                編集
                              </button>
                              <button
                                onClick={() => handleDeleteComment(comment.id)}
                                className="text-red-600 hover:text-red-800 text-sm"
                              >
                                削除
                              </button>
                            </div>
                          )}
                        </div>
                        <p className="text-gray-700 whitespace-pre-wrap">{comment.content}</p>
                        <p className="text-xs text-gray-400 mt-2">
                          {formatDate(comment.create_date)}
                        </p>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* コメント投稿フォーム */}
            <div>
              <textarea
                value={commentContent}
                onChange={(e) => setCommentContent(e.target.value)}
                placeholder="コメントを入力..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 mb-2"
                rows={3}
              />
              <button
                onClick={handlePostComment}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                投稿
              </button>
            </div>
          </div>
        </div>

        {/* 写真拡大モーダル */}
        <PhotoModal
          isOpen={!!modalPhoto}
          onClose={() => setModalPhoto(null)}
          photoUrl={modalPhoto?.file_path || ""}
          photoTitle={modalPhoto?.title}
        />
      </div>
    </AuthGuard>
  );
}
