interface PhotoModalProps {
  isOpen: boolean;
  onClose: () => void;
  photoUrl: string;
  photoTitle?: string | null;
}

export default function PhotoModal({ isOpen, onClose, photoUrl, photoTitle }: PhotoModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75"
      onClick={onClose}
    >
      <div className="relative max-w-7xl max-h-screen p-4">
        <button
          onClick={onClose}
          className="absolute top-6 right-6 text-white text-4xl font-bold hover:text-gray-300 z-10"
          aria-label="閉じる"
        >
          &times;
        </button>
        <img
          src={photoUrl}
          alt={photoTitle || "Photo"}
          className="max-w-full max-h-screen object-contain"
          onClick={(e) => e.stopPropagation()}
        />
      </div>
    </div>
  );
}
