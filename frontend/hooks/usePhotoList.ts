import { useState, useEffect } from "react";
import { pictureService } from "@/services/pictures";
import { Picture } from "@/types/pictures";

export const usePhotoList = () => {
  const [photos, setPhotos] = useState<Picture[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedDate, setSelectedDate] = useState("");

  useEffect(() => {
    const fetchPhotos = async () => {
      try {
        const params: Record<string, string> = {};
        if (selectedCategory) params.category = selectedCategory;
        if (selectedDate) params.date = selectedDate;

        const response = await pictureService.getPictures(params);
        setPhotos(response.pictures);
      } catch (error) {
        console.error("Error fetching photos:", error);
      }
    };

    fetchPhotos();
  }, [selectedCategory, selectedDate]);

  return { photos, selectedCategory, selectedDate, setSelectedCategory, setSelectedDate };
};