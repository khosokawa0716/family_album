import { usePhotoList } from "@/hooks/usePhotoList";
import { formatDate } from "@/utils/date";
import PageHeader from "@/components/PageHeader";

export default function PhotoList() {
  const { photos, selectedCategory, selectedDate, setSelectedCategory, setSelectedDate } = usePhotoList();

  return (
    <div className="min-h-screen bg-gray-50">
      <PageHeader title="Photo List">
        {/* TODO: 後でリンクなどの実装内容を考える */}
        {/* <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium">
          Add Photo
        </button>
        <button className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium">
          Remove Photo
        </button> */}
      </PageHeader>

      {/* Filter */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
                Category
              </label>
              <select
                id="category"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Select Category</option>
                <option value="family">Family</option>
                <option value="travel">Travel</option>
                <option value="event">Event</option>
              </select>
            </div>
            {/* 日付のフィルターは一旦コメントアウト
            <div>
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

      {/* Photo Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {photos.map((photo) => (
            <div
              key={photo.id}
              className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => console.log(`Photo ${photo.id} clicked`)}
            >
              <img
                src={photo.thumbnail_path}
                alt={photo.title}
                className="w-full h-48 object-cover rounded-t-lg"
              />
              <div className="p-4">
                <h3 className="text-lg font-medium text-gray-900">{photo.title}</h3>
                <p className="text-sm text-gray-500 mt-1">{photo.description}</p>
                <span className="inline-block bg-indigo-100 text-indigo-800 text-xs px-2 py-1 rounded-full mt-2">
                  {formatDate(photo.taken_date)}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Pagination 後で実装 */}
        {/* <div className="text-center mt-8">
          <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-md font-medium">
            Load More
          </button>
        </div> */}
      </div>
    </div>
  );
}