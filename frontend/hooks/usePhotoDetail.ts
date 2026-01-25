import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import { pictureService } from "@/services/pictures";
import { commentService } from "@/services/comments";
import { PictureResponse } from "@/types/pictures";
import { CommentResponse } from "@/types/comments";

export const usePhotoDetail = (pictureId: number) => {
  console.log("usePhotoDetail called with pictureId:", pictureId);
  const router = useRouter();
  const [photo, setPhoto] = useState<PictureResponse | null>(null);
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

  // 写真詳細取得
  const fetchPhotoDetail = useCallback(async () => {
    try {
      setLoading(true);
      const response = await pictureService.getPictureDetail(pictureId);
      setPhoto(response);
    } catch (err) {
      console.error("Error fetching photo detail:", err);
      setError("写真の読み込みに失敗しました");
      alert("写真の読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, [pictureId]);

  // コメント一覧取得
  const fetchComments = useCallback(async () => {
    try {
      const response = await commentService.getPictureComments(pictureId);
      setComments(response);
    } catch (err) {
      console.error("Error fetching comments:", err);
      alert("コメントの読み込みに失敗しました");
    }
  }, [pictureId]);

  // 初回読み込み
  useEffect(() => {
    if (!isNaN(pictureId) && pictureId > 0) {
      fetchPhotoDetail();
      fetchComments();
    }
  }, [pictureId, fetchPhotoDetail, fetchComments]);

  // 写真削除
  const handleDeletePhoto = async () => {
    if (!window.confirm("この写真を削除してもよろしいですか？")) {
      return;
    }

    try {
      await pictureService.deletePicture(pictureId);
      alert("写真を削除しました");
      router.push("/photo/list");
    } catch (err) {
      console.error("Error deleting photo:", err);
      alert("写真の削除に失敗しました");
    }
  };

  // 写真ダウンロード
  const handleDownloadPhoto = async () => {
    try {
      const blob = await pictureService.downloadPicture(pictureId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = photo?.title || `photo_${pictureId}`;
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
    if (!commentContent.trim()) {
      alert("コメントを入力してください");
      return;
    }

    try {
      await commentService.createComment(pictureId, { content: commentContent });
      setCommentContent("");
      await fetchComments();
    } catch (err) {
      console.error("Error posting comment:", err);
      alert("コメントの投稿に失敗しました");
    }
  };

  // コメント編集開始
  const startEditComment = (comment: CommentResponse) => {
    setEditingCommentId(comment.id);
    setEditingContent(comment.content);
  };

  // コメント編集キャンセル
  const cancelEditComment = () => {
    setEditingCommentId(null);
    setEditingContent("");
  };

  // コメント編集保存
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

  // コメント削除
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

  // 写真編集開始
  const startEditPhoto = () => {
    if (photo) {
      setEditingTitle(photo.title || "");
      setEditingDescription(photo.description || "");
      setIsEditingPhoto(true);
    }
  };

  // 写真編集キャンセル
  const cancelEditPhoto = () => {
    setIsEditingPhoto(false);
    setEditingTitle("");
    setEditingDescription("");
  };

  // 写真編集保存
  const handleUpdatePhoto = async () => {
    try {
      await pictureService.updatePicture(pictureId, {
        title: editingTitle || null,
        description: editingDescription || null,
      });
      setIsEditingPhoto(false);
      await fetchPhotoDetail();
    } catch (err) {
      console.error("Error updating photo:", err);
      alert("写真情報の更新に失敗しました");
    }
  };

  return {
    photo,
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
