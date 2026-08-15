import { useMemo } from "react";
import { useVideoUpload } from "@/hooks/useVideoUpload";
import PageHeader from "@/components/PageHeader";
import { AuthGuard } from "@/components/AuthGuard";

export default function VideoUpload() {
  const {
    selectedFile,
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
  } = useVideoUpload();

  const previewUrl = useMemo(() => {
    return selectedFile ? URL.createObjectURL(selectedFile) : null;
  }, [selectedFile]);

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <PageHeader title="Video Upload" />

        <div className="max-w-md mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="bg-white rounded-lg shadow p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Upload */}
              <div>
                <label htmlFor="file" className="block text-sm font-medium text-gray-700 mb-2">
                  動画（1本のみ）
                </label>
                <input
                  type="file"
                  id="file"
                  accept="video/mp4,video/quicktime"
                  onChange={handleFileChange}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-[var(--color-primary-500)] focus:border-[var(--color-primary-500)]"
                />
                <p className="text-xs text-gray-500 mt-1">
                  MP4, MOV（30秒以内・100MB以下）
                </p>

                {selectedFile && (
                  <div className="relative mt-3">
                    <video
                      src={previewUrl ?? undefined}
                      controls
                      playsInline
                      className="w-full max-h-64 rounded-md bg-black"
                    />
                    <button
                      type="button"
                      onClick={removeFile}
                      className="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs leading-none hover:bg-red-600"
                    >
                      &times;
                    </button>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{selectedFile.name}</p>
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
                  placeholder="Enter video title"
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-[var(--color-primary-500)] focus:border-[var(--color-primary-500)]"
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
                  placeholder="Enter video description"
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-[var(--color-primary-500)] focus:border-[var(--color-primary-500)]"
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
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-[var(--color-primary-500)] focus:border-[var(--color-primary-500)]"
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
                  disabled={isUploading || !selectedFile || !selectedCategory}
                  className="w-full bg-[var(--color-primary-600)] hover:bg-[var(--color-primary-700)] disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition-colors"
                >
                  {isUploading ? "アップロード中..." : "アップロード"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
