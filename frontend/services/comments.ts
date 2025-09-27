import { apiClient } from "@/lib/api/client";
import { CommentResponse, CommentCreateRequest, CommentUpdateRequest } from "@/types/comments";

export const commentService = {
  async getPictureComments(pictureId: number): Promise<CommentResponse[]> {
    return apiClient.get<CommentResponse[]>(`/pictures/${pictureId}/comments`);
  },

  async createComment(
    pictureId: number,
    commentData: CommentCreateRequest,
  ): Promise<CommentResponse> {
    return apiClient.post<CommentResponse>(`/pictures/${pictureId}/comments`, commentData);
  },

  async updateComment(
    commentId: number,
    commentData: CommentUpdateRequest,
  ): Promise<CommentResponse> {
    return apiClient.patch<CommentResponse>(`/comments/${commentId}`, commentData);
  },

  async deleteComment(commentId: number): Promise<void> {
    return apiClient.delete<void>(`/comments/${commentId}`);
  },
};
