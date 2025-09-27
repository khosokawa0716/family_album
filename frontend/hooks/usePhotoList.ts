import { useState, useEffect } from "react";
import { pictureService } from "@/services/pictures";
import { categoryService } from "@/services/categories";
import { PictureResponse } from "@/types/pictures";
import { CategoryResponse } from "@/types/categories";

export const usePhotoList = () => {
  const [photos, setPhotos] = useState<PictureResponse[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("すべて");
  const [selectedDate, setSelectedDate] = useState("");

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await categoryService.getCategories();
        console.log("Fetched categories:", response);
        setCategories(response);
      } catch (error) {
        console.error("Error fetching categories:", error);
      }
    };

    fetchCategories();
  }, []);

  useEffect(() => {
    const fetchPhotos = async () => {
      try {
        const params: Record<string, string> = {};
        if (selectedCategory && selectedCategory !== "すべて") {
          params.category = selectedCategory;
        }
        if (selectedDate) params.date = selectedDate;

        const response = await pictureService.getPictures(params);
        setPhotos(response.pictures);
      } catch (error) {
        console.error("Error fetching photos:", error);
      }
    };

    fetchPhotos();
  }, [selectedCategory, selectedDate]);

  return {
    photos,
    categories,
    selectedCategory,
    selectedDate,
    setSelectedCategory,
    setSelectedDate,
  };
};
