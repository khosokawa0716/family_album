import { apiClient } from "@/lib/api/client";
import { PictureRequest, PictureResponse } from "@/types/pictures";

export const pictureService = {
  async getPictures(params: PictureRequest): Promise<PictureResponse> {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    const endpoint = query ? `/pictures?${query}` : "/pictures";
    return apiClient.get<PictureResponse>(endpoint);
  },
};