import { useState } from "react";
import { useRouter } from "next/router";

export const usePhotoUpload = () => {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Check file size (10MB)
      if (file.size > 10 * 1024 * 1024) {
        alert("File size exceeds 10MB");
        return;
      }

      // Allowed file types
      const allowedTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
      if (!allowedTypes.includes(file.type)) {
        alert("Allowed file types: JPEG, PNG, GIF, WEBP");
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
      // TODO: Implement upload logic
      console.log("Uploading file:", selectedFile.name);
      console.log("Category:", selectedCategory);

      // Simulate upload
      await new Promise((resolve) => setTimeout(resolve, 2000));

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
    isUploading,
    setSelectedCategory,
    handleFileChange,
    handleSubmit,
  };
};
