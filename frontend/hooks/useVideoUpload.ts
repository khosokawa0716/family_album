import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import { pictureService } from "@/services/pictures";
import { categoryService } from "@/services/categories";
import { CategoryResponse } from "@/types/categories";

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
const MAX_DURATION_SECONDS = 30;

const ALLOWED_TYPES = ["video/mp4", "video/quicktime"];

const isAllowedVideoFile = (file: File): boolean => {
  if (ALLOWED_TYPES.includes(file.type)) return true;
  const ext = file.name.toLowerCase().split(".").pop();
  return ext === "mp4" || ext === "mov";
};

const readVideoDuration = (file: File): Promise<number> => {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    video.preload = "metadata";
    const url = URL.createObjectURL(file);

    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(video.duration);
    };
    video.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("動画の読み込みに失敗しました"));
    };
    video.src = url;
  });
};

export const useVideoUpload = () => {
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

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];

    if (!isAllowedVideoFile(file)) {
      alert(`「${file.name}」は対応していないファイル形式です（MP4, MOV）`);
      event.target.value = "";
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      alert(`「${file.name}」のファイルサイズが大きすぎます（100MB以下にしてください）`);
      event.target.value = "";
      return;
    }

    try {
      const duration = await readVideoDuration(file);
      if (duration > MAX_DURATION_SECONDS) {
        alert(`「${file.name}」は長すぎます（${MAX_DURATION_SECONDS}秒以下にしてください）`);
        event.target.value = "";
        return;
      }
    } catch (error) {
      console.error("Failed to read video duration:", error);
      // 長さの事前チェックに失敗しても、最終判定はサーバー側で行うためアップロードは許可する
    }

    setSelectedFile(file);
    event.target.value = "";
  };

  const removeFile = () => {
    setSelectedFile(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!selectedFile || !selectedCategory) {
      alert("動画とカテゴリを選択してください");
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

      await pictureService.uploadVideo(formData);

      router.push("/photo/list");
    } catch (error) {
      console.error("Upload failed:", error);
      alert("アップロードに失敗しました");
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
    removeFile,
    handleSubmit,
  };
};
