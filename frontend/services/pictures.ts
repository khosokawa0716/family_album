import { apiClient } from "@/lib/api/client";
import {
  PictureRequest,
  PictureListResponse,
  PictureResponse,
  PictureRestoreResponse,
  PictureUpdateRequest,
} from "@/types/pictures";

export const pictureService = {
  async getPictures(params: PictureRequest): Promise<PictureListResponse> {
    console.log("Fetching pictures with params:", params);
    const queryParams: Record<string, string> = {};

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams[key] = String(value);
      }
    });
    console.log("Query parameters:", queryParams);
    const query = new URLSearchParams(queryParams).toString();
    const endpoint = query ? `/pictures?${query}` : "/pictures";
    return apiClient.get<PictureListResponse>(endpoint);
  },

  async getPictureDetail(pictureId: number): Promise<PictureResponse> {
    return apiClient.get<PictureResponse>(`/pictures/${pictureId}`);
  },

  async getDeletedPictures(): Promise<PictureListResponse> {
    return apiClient.get<PictureListResponse>("/pictures/deleted");
  },

  async uploadPicture(formData: FormData): Promise<PictureResponse> {
    return apiClient.postFormData<PictureResponse>("/pictures", formData);
  },

  async deletePicture(pictureId: number): Promise<void> {
    return apiClient.delete<void>(`/pictures/${pictureId}`);
  },

  async restorePicture(pictureId: number): Promise<PictureRestoreResponse> {
    return apiClient.patch<PictureRestoreResponse>(`/pictures/${pictureId}/restore`);
  },

  async downloadPicture(pictureId: number): Promise<Blob> {
    return apiClient.downloadBlob(`/pictures/${pictureId}/download`);
  },

  async updatePicture(pictureId: number, data: PictureUpdateRequest): Promise<PictureResponse> {
    return apiClient.patch<PictureResponse>(`/pictures/${pictureId}`, data);
  },
};
