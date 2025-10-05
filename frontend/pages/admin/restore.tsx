import { useState } from "react";
import PageHeader from "@/components/PageHeader";
import { AdminGuard } from "@/components/AdminGuard";
import { useAdminRestore } from "@/hooks/useAdminRestore";
import { formatDateTime } from "@/utils/date";

export default function AdminRestore() {
  const { deletedPictures, loading, error, restorePicture } = useAdminRestore();
  const [selectedPictureId, setSelectedPictureId] = useState<number | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);

  const handleRestoreClick = (pictureId: number) => {
    setSelectedPictureId(pictureId);
  };

  const handleConfirmRestore = async () => {
    if (selectedPictureId === null) return;

    setIsRestoring(true);
    const success = await restorePicture(selectedPictureId);
    setIsRestoring(false);

    if (success) {
      alert("写真を復元しました");
      setSelectedPictureId(null);
    } else {
      alert("写真の復元に失敗しました");
    }
  };

  const handleCancelRestore = () => {
    setSelectedPictureId(null);
  };

  const getFileName = (filePath: string): string => {
    return filePath.split("/").pop() || filePath;
  };

  return (
    <AdminGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="写真復元管理" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white rounded-lg shadow">
            {loading ? (
              <div className="p-6 text-center text-gray-600">Loading...</div>
            ) : error ? (
              <div className="p-6 text-center text-red-600">{error}</div>
            ) : deletedPictures.length === 0 ? (
              <div className="p-6 text-center text-gray-600">
                削除済み写真はありません
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        サムネイル
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        ファイル名
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        タイトル
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        削除日
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        復元
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {deletedPictures.map((picture) => (
                      <tr key={picture.id}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <img
                            src={picture.thumbnail_path || ""}
                            alt={picture.title || "Deleted photo"}
                            className="w-16 h-16 object-cover rounded"
                          />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {getFileName(picture.file_path)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {picture.title || "-"}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDateTime(picture.deleted_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <button
                            onClick={() => handleRestoreClick(picture.id)}
                            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md font-medium"
                          >
                            復元
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Confirmation Dialog */}
        {selectedPictureId !== null && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={handleCancelRestore}
          >
            <div
              className="bg-white rounded-lg p-6 max-w-md w-full mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                写真の復元
              </h3>
              <p className="text-gray-700 mb-6">この写真を復元しますか？</p>
              <div className="flex justify-end space-x-4">
                <button
                  onClick={handleCancelRestore}
                  disabled={isRestoring}
                  className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md font-medium disabled:opacity-50"
                >
                  キャンセル
                </button>
                <button
                  onClick={handleConfirmRestore}
                  disabled={isRestoring}
                  className="px-4 py-2 text-white bg-green-600 hover:bg-green-700 rounded-md font-medium disabled:opacity-50"
                >
                  {isRestoring ? "復元中..." : "復元"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminGuard>
  );
}
