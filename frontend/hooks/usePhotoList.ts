import { useState, useEffect, useCallback } from "react";
import { pictureService } from "@/services/pictures";
import { categoryService } from "@/services/categories";
import { PictureResponse } from "@/types/pictures";
import { CategoryResponse } from "@/types/categories";

/**
 * 無限スクロール対応の写真リスト管理フック
 *
 * 写真データの取得、ページング、フィルタリング機能を提供します。
 * 無限スクロールにより、ユーザーのスクロール操作に応じて
 * 自動的に追加の写真データを読み込みます。
 */
export const usePhotoList = () => {
  // === 状態管理 ===
  const [photos, setPhotos] = useState<PictureResponse[]>([]); // 表示中の写真データ
  const [categories, setCategories] = useState<CategoryResponse[]>([]); // カテゴリ一覧
  const [selectedCategory, setSelectedCategory] = useState("すべて"); // 選択中のカテゴリ
  const [selectedDate, setSelectedDate] = useState(""); // 選択中の日付

  // === 無限スクロール用の状態 ===
  const [loading, setLoading] = useState(false); // データ読み込み中フラグ
  const [hasMore, setHasMore] = useState(true); // 追加データの存在フラグ
  const [offset, setOffset] = useState(0); // 現在のデータ取得位置

  // === 設定値 ===
  const LIMIT = 20; // 1回あたりのデータ取得件数

  /**
   * カテゴリ一覧を取得する
   * アプリケーション起動時に一度だけ実行されます
   */
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        console.log("カテゴリ一覧の取得を開始");
        const response = await categoryService.getCategories();
        console.log("取得したカテゴリ:", response);
        setCategories(response);
      } catch (error) {
        console.error("カテゴリ取得エラー:", error);
      }
    };

    fetchCategories();
  }, []);

  /**
   * 写真データを取得する共通関数
   *
   * @param currentOffset 取得開始位置
   * @param isInitial 初回読み込みかどうか（true: データをリセット、false: 追加）
   */
  const fetchPhotos = useCallback(
    async (currentOffset: number, isInitial = false) => {
      // 重複リクエストの防止
      if (loading) {
        console.log("既に読み込み中のため、リクエストをスキップ");
        return;
      }

      console.log(`写真データの取得を開始 (offset: ${currentOffset}, initial: ${isInitial})`);
      setLoading(true);

      try {
        // APIリクエストパラメータの準備
        const params: any = {
          limit: LIMIT,
          offset: currentOffset,
        };

        // カテゴリフィルターの適用
        if (selectedCategory && selectedCategory !== "すべて") {
          params.category = selectedCategory;
          console.log(`カテゴリフィルター適用: ${selectedCategory}`);
        }

        // 日付フィルターの適用（将来の拡張用）
        if (selectedDate) {
          params.date = selectedDate;
          console.log(`日付フィルター適用: ${selectedDate}`);
        }

        // APIを呼び出して写真データを取得
        const response = await pictureService.getPictures(params);
        console.log(`取得した写真数: ${response.pictures.length}, 総数: ${response.total}`);

        if (isInitial) {
          // 初回読み込みまたはフィルター条件変更時
          // 既存のデータを新しいデータで置き換える
          console.log("写真データを初期化して新しいデータを設定");
          setPhotos(response.pictures);
        } else {
          // 追加読み込み時
          // 既存のデータに新しいデータを追加する
          console.log("既存の写真データに新しいデータを追加");
          setPhotos((prev) => [...prev, ...response.pictures]);
        }

        // 次ページの存在チェック
        // APIから返された has_more フラグを使用
        setHasMore(response.has_more);
        console.log(`次ページの存在: ${response.has_more}`);

        // 次回のリクエスト用にオフセットを更新
        setOffset(currentOffset + LIMIT);
      } catch (error) {
        console.error("写真取得エラー:", error);
        // エラーが発生した場合も読み込み状態をリセット
      } finally {
        setLoading(false);
        console.log("写真データ取得処理完了");
      }
    },
    [selectedCategory, selectedDate, loading],
  ); // 依存関係にloadingを含めて無限ループを防ぐ

  /**
   * 初回読み込み＆フィルター条件変更時の処理
   *
   * カテゴリや日付フィルターが変更された場合、
   * 既存のデータをリセットして最初から読み込み直します
   */
  useEffect(() => {
    console.log("フィルター条件変更による写真データリセット");

    // 状態をリセット
    setPhotos([]); // 写真データをクリア
    setOffset(0); // オフセットを0にリセット
    setHasMore(true); // 次ページフラグをリセット

    // 最初のページを取得
    fetchPhotos(0, true);
  }, [selectedCategory, selectedDate]); // fetchPhotosは依存関係から除外（無限ループ防止）

  /**
   * 追加の写真データを読み込む関数
   *
   * 無限スクロールまたは「もっと読み込む」ボタンから呼び出されます
   */
  const loadMorePhotos = useCallback(() => {
    // 追加データが存在し、かつ現在読み込み中でない場合のみ実行
    if (hasMore && !loading) {
      console.log(`追加写真データの読み込み開始 (offset: ${offset})`);
      fetchPhotos(offset);
    } else {
      console.log("追加読み込み条件を満たさないため、スキップ");
    }
  }, [hasMore, loading, offset, fetchPhotos]);

  // === 外部に公開するAPI ===
  return {
    // データ
    photos, // 現在表示中の写真配列
    categories, // カテゴリ一覧

    // 状態
    loading, // 読み込み中フラグ
    hasMore, // 追加データ存在フラグ

    // フィルター
    selectedCategory, // 選択中カテゴリ
    selectedDate, // 選択中日付
    setSelectedCategory, // カテゴリ変更関数
    setSelectedDate, // 日付変更関数

    // アクション
    loadMorePhotos, // 追加読み込み関数
  };
};
