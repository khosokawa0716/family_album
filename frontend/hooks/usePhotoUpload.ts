import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import { pictureService } from "@/services/pictures";
import { categoryService } from "@/services/categories";
import { CategoryResponse } from "@/types/categories";

export const usePhotoUpload = () => {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await categoryService.getCategories();
        setCategories(response);
      } catch (error) {
        console.error("Error fetching categories:", error);
      }
    };

    fetchCategories();
  }, []);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Check file size (20MB)
      if (file.size > 20 * 1024 * 1024) {
        alert("File size exceeds 20MB");
        return;
      }

      // Allowed file types - HEICファイルのtype判定を緩和
      const allowedTypes = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/heic",
        "image/heif",
      ];
      const fileExtension = file.name.toLowerCase().split(".").pop();
      const isHEIC = fileExtension === "heic" || fileExtension === "heif";

      // HEICファイルの場合はfile.typeが空でも許可
      if (!isHEIC && !allowedTypes.includes(file.type)) {
        alert("Allowed file types: JPEG, PNG, GIF, WEBP, HEIC, HEIF");
        return;
      }

      setSelectedFile(file);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!selectedFile || !selectedCategory) {
      alert("Please select a file and a category");
      return;
    }

    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("category_id", selectedCategory);

      if (title.trim()) {
        formData.append("title", title.trim());
      }

      if (description.trim()) {
        formData.append("description", description.trim());
      }

      await pictureService.uploadPicture(formData);

      // Redirect to photo list
      router.push("/photo/list");
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  return {
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
    handleSubmit,
  };
};
