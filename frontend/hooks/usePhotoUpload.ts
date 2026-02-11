import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import { pictureService } from "@/services/pictures";
import { categoryService } from "@/services/categories";
import { CategoryResponse } from "@/types/categories";

const MAX_FILES = 5;
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

const ALLOWED_TYPES = [
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
  "image/heic",
  "image/heif",
];

const isHEICFile = (file: File): boolean => {
  const ext = file.name.toLowerCase().split(".").pop();
  return ext === "heic" || ext === "heif";
};

const isAllowedFile = (file: File): boolean => {
  if (isHEICFile(file)) return true;
  return ALLOWED_TYPES.includes(file.type);
};

export const usePhotoUpload = () => {
  const router = useRouter();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
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
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const newFiles = Array.from(files);
    const totalFiles = selectedFiles.length + newFiles.length;

    if (totalFiles > MAX_FILES) {
      alert(`最大${MAX_FILES}枚まで選択できます`);
      event.target.value = "";
      return;
    }

    for (const file of newFiles) {
      if (file.size > MAX_FILE_SIZE) {
        alert(`「${file.name}」のファイルサイズが大きすぎます（50MB以下にしてください）`);
        event.target.value = "";
        return;
      }
      if (!isAllowedFile(file)) {
        alert(`「${file.name}」は対応していないファイル形式です（JPEG, PNG, GIF, WEBP, HEIC, HEIF）`);
        event.target.value = "";
        return;
      }
    }

    setSelectedFiles((prev) => [...prev, ...newFiles]);
    event.target.value = "";
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (selectedFiles.length === 0 || !selectedCategory) {
      alert("ファイルとカテゴリを選択してください");
      return;
    }

    setIsUploading(true);

    try {
      const formData = new FormData();
      for (const file of selectedFiles) {
        formData.append("files", file);
      }
      formData.append("category_id", selectedCategory);

      if (title.trim()) {
        formData.append("title", title.trim());
      }

      if (description.trim()) {
        formData.append("description", description.trim());
      }

      await pictureService.uploadPictures(formData);

      router.push("/photo/list");
    } catch (error) {
      console.error("Upload failed:", error);
      alert("アップロードに失敗しました");
    } finally {
      setIsUploading(false);
    }
  };

  return {
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
  };
};
