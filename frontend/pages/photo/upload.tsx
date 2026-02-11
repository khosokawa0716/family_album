import { useMemo } from "react";
import { usePhotoUpload } from "@/hooks/usePhotoUpload";
import PageHeader from "@/components/PageHeader";
import { AuthGuard } from "@/components/AuthGuard";

export default function PhotoUpload() {
  const {
    selectedFiles,
    selectedCategory,
    title,
    description,
    categories,
    isUploading,
    setSelectedCategory,
    setTitle,
    setDescription,
    handleFileChange,
    removeFile,
    handleSubmit,
  } = usePhotoUpload();

  const previewUrls = useMemo(() => {
    return selectedFiles.map((file) => URL.createObjectURL(file));
  }, [selectedFiles]);

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="Photo Upload" />

        <div className="max-w-md mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="bg-white rounded-lg shadow p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Upload */}
              <div>
                <label htmlFor="file" className="block text-sm font-medium text-gray-700 mb-2">
                  写真（最大5枚）
                </label>
                <input
                  type="file"
                  id="file"
                  accept="image/jpeg,image/png,image/gif,image/webp,image/heic,image/heif"
                  onChange={handleFileChange}
                  multiple
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  JPEG, PNG, GIF, WEBP, HEIC, HEIF（大きい画像は自動リサイズ）
                </p>

                {/* Selected files count */}
                {selectedFiles.length > 0 && (
                  <p className="text-sm text-indigo-600 font-medium mt-2">
                    {selectedFiles.length}/5枚選択中
                  </p>
                )}

                {/* Preview grid */}
                {selectedFiles.length > 0 && (
                  <div className="grid grid-cols-3 gap-2 mt-3">
                    {selectedFiles.map((file, index) => (
                      <div key={`${file.name}-${file.lastModified}`} className="relative">
                        <img
                          src={previewUrls[index]}
                          alt={file.name}
                          className="w-full h-24 object-cover rounded-md"
                        />
                        <button
                          type="button"
                          onClick={() => removeFile(index)}
                          className="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs leading-none hover:bg-red-600"
                        >
                          &times;
                        </button>
                        <p className="text-xs text-gray-500 mt-0.5 truncate">{file.name}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Title */}
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                  Title
                </label>
                <input
                  type="text"
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Enter photo title"
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              {/* Description */}
              <div>
                <label
                  htmlFor="description"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Description
                </label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  placeholder="Enter photo description"
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              {/* Category */}
              <div>
                <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
                  Category
                </label>
                <select
                  id="category"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  required
                >
                  <option value="">Select Category</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Submit Button */}
              <div>
                <button
                  type="submit"
                  disabled={isUploading || selectedFiles.length === 0 || !selectedCategory}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors"
                >
                  {isUploading ? "アップロード中..." : `アップロード（${selectedFiles.length}枚）`}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
