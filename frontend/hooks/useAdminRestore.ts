import { useState, useEffect } from "react";
import { pictureService } from "@/services/pictures";
import { PictureResponse } from "@/types/pictures";

export const useAdminRestore = () => {
  const [deletedPictures, setDeletedPictures] = useState<PictureResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDeletedPictures = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await pictureService.getDeletedPictures();
      setDeletedPictures(response.pictures);
    } catch (err) {
      console.error("Error fetching deleted pictures:", err);
      setError("削除済み写真の取得に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const restorePicture = async (pictureId: number): Promise<boolean> => {
    try {
      await pictureService.restorePicture(pictureId);
      // Refresh the list after restoration
      await fetchDeletedPictures();
      return true;
    } catch (err) {
      console.error("Error restoring picture:", err);
      setError("写真の復元に失敗しました");
      return false;
    }
  };

  useEffect(() => {
    fetchDeletedPictures();
  }, []);

  return {
    deletedPictures,
    loading,
    error,
    restorePicture,
    refreshList: fetchDeletedPictures,
  };
};
