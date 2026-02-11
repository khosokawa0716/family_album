import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import { pictureService } from "@/services/pictures";
import { commentService } from "@/services/comments";
import { PictureResponse } from "@/types/pictures";
import { CommentResponse } from "@/types/comments";

export const usePhotoDetail = (id: string) => {
  console.log("usePhotoDetail called with id:", id);
  const router = useRouter();
  const [photos, setPhotos] = useState<PictureResponse[]>([]);
  const [selectedPhoto, setSelectedPhoto] = useState<PictureResponse | null>(null);
  const [comments, setComments] = useState<CommentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commentContent, setCommentContent] = useState("");
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editingContent, setEditingContent] = useState("");

  // 写真編集用の状態
  const [isEditingPhoto, setIsEditingPhoto] = useState(false);
  const [editingTitle, setEditingTitle] = useState("");
  const [editingDescription, setEditingDescription] = useState("");

  // グループ詳細を取得
  const fetchGroupDetail = useCallback(async () => {
    try {
      setLoading(true);

      // 数値IDの場合、旧APIで写真を取得してgroup_idにリダイレクト
      const numericId = Number(id);
      if (!isNaN(numericId) && numericId > 0) {
        try {
          const picture = await pictureService.getPictureDetail(numericId);
          if (picture.group_id) {
            router.replace(`/photo/detail/${picture.group_id}`);
            return;
          }
        } catch {
          // 数値IDとして取得できない場合はgroup_idとして扱う
        }
      }

      // group_idとしてグループ詳細を取得
      const response = await pictureService.getPictureGroupDetail(id);
      setPhotos(response.pictures);
      if (response.pictures.length > 0) {
        setSelectedPhoto(response.pictures[0]);
      }
    } catch (err) {
      console.error("Error fetching group detail:", err);
      setError("写真の読み込みに失敗しました");
      alert("写真の読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, [id, router]);

  // コメント一覧取得（選択中の写真に対して）
  const fetchComments = useCallback(async () => {
    if (!selectedPhoto) return;
    try {
      const response = await commentService.getPictureComments(selectedPhoto.id);
      setComments(response);
    } catch (err) {
      console.error("Error fetching comments:", err);
      alert("コメントの読み込みに失敗しました");
    }
  }, [selectedPhoto]);

  // 初回読み込み
  useEffect(() => {
    if (id) {
      fetchGroupDetail();
    }
  }, [id, fetchGroupDetail]);

  // 選択写真変更時にコメント取得
  useEffect(() => {
    if (selectedPhoto) {
      fetchComments();
    }
  }, [selectedPhoto, fetchComments]);

  // グループ内全写真を削除
  const handleDeletePhoto = async () => {
    if (!window.confirm("このグループの写真をすべて削除してもよろしいですか？")) {
      return;
    }

    try {
      for (const photo of photos) {
        await pictureService.deletePicture(photo.id);
      }
      alert("写真を削除しました");
      router.push("/photo/list");
    } catch (err) {
      console.error("Error deleting photos:", err);
      alert("写真の削除に失敗しました");
    }
  };

  // 選択中の写真をダウンロード
  const handleDownloadPhoto = async () => {
    if (!selectedPhoto) return;
    try {
      const blob = await pictureService.downloadPicture(selectedPhoto.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = selectedPhoto.title || `photo_${selectedPhoto.id}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Error downloading photo:", err);
      alert("写真のダウンロードに失敗しました");
    }
  };

  // コメント投稿
  const handlePostComment = async () => {
    if (!commentContent.trim() || !selectedPhoto) {
      alert("コメントを入力してください");
      return;
    }

    try {
      await commentService.createComment(selectedPhoto.id, { content: commentContent });
      setCommentContent("");
      await fetchComments();
    } catch (err) {
      console.error("Error posting comment:", err);
      alert("コメントの投稿に失敗しました");
    }
  };

  const startEditComment = (comment: CommentResponse) => {
    setEditingCommentId(comment.id);
    setEditingContent(comment.content);
  };

  const cancelEditComment = () => {
    setEditingCommentId(null);
    setEditingContent("");
  };

  const handleUpdateComment = async (commentId: number) => {
    if (!editingContent.trim()) {
      alert("コメントを入力してください");
      return;
    }

    try {
      await commentService.updateComment(commentId, { content: editingContent });
      setEditingCommentId(null);
      setEditingContent("");
      await fetchComments();
    } catch (err) {
      console.error("Error updating comment:", err);
      alert("コメントの更新に失敗しました");
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!window.confirm("このコメントを削除してもよろしいですか？")) {
      return;
    }

    try {
      await commentService.deleteComment(commentId);
      await fetchComments();
    } catch (err) {
      console.error("Error deleting comment:", err);
      alert("コメントの削除に失敗しました");
    }
  };

  // 写真編集開始（グループ共通のtitle/description）
  const startEditPhoto = () => {
    const first = photos[0];
    if (first) {
      setEditingTitle(first.title || "");
      setEditingDescription(first.description || "");
      setIsEditingPhoto(true);
    }
  };

  const cancelEditPhoto = () => {
    setIsEditingPhoto(false);
    setEditingTitle("");
    setEditingDescription("");
  };

  // グループ内全写真のtitle/descriptionを更新
  const handleUpdatePhoto = async () => {
    try {
      for (const photo of photos) {
        await pictureService.updatePicture(photo.id, {
          title: editingTitle || null,
          description: editingDescription || null,
        });
      }
      setIsEditingPhoto(false);
      await fetchGroupDetail();
    } catch (err) {
      console.error("Error updating photo:", err);
      alert("写真情報の更新に失敗しました");
    }
  };

  return {
    photos,
    selectedPhoto,
    setSelectedPhoto,
    comments,
    loading,
    error,
    commentContent,
    setCommentContent,
    editingCommentId,
    editingContent,
    setEditingContent,
    handleDeletePhoto,
    handleDownloadPhoto,
    handlePostComment,
    startEditComment,
    cancelEditComment,
    handleUpdateComment,
    handleDeleteComment,
    // 写真編集
    isEditingPhoto,
    editingTitle,
    setEditingTitle,
    editingDescription,
    setEditingDescription,
    startEditPhoto,
    cancelEditPhoto,
    handleUpdatePhoto,
  };
};
