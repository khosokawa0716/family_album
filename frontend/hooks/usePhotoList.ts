import { useState, useEffect, useCallback } from "react";
import { pictureService } from "@/services/pictures";
import { categoryService } from "@/services/categories";
import { PictureGroupResponse } from "@/types/pictures";
import { CategoryResponse } from "@/types/categories";

/**
 * 無限スクロール対応の写真グループリスト管理フック
 *
 * グループ単位での写真データの取得、ページング、フィルタリング機能を提供します。
 */
export const usePhotoList = () => {
  // === 状態管理 ===
  const [groups, setGroups] = useState<PictureGroupResponse[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("すべて");
  const [selectedDate, setSelectedDate] = useState("");

  // === 無限スクロール用の状態 ===
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);

  // === 設定値 ===
  const LIMIT = 20;

  /**
   * カテゴリ一覧を取得する
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
   * グループデータを取得する共通関数
   */
  const fetchGroups = useCallback(
    async (currentOffset: number, isInitial = false) => {
      if (loading) {
        console.log("既に読み込み中のため、リクエストをスキップ");
        return;
      }

      console.log(`グループデータの取得を開始 (offset: ${currentOffset}, initial: ${isInitial})`);
      setLoading(true);

      try {
        const params: any = {
          limit: LIMIT,
          offset: currentOffset,
        };

        if (selectedCategory && selectedCategory !== "すべて") {
          params.category = selectedCategory;
          console.log(`カテゴリフィルター適用: ${selectedCategory}`);
        }

        if (selectedDate) {
          params.date = selectedDate;
          console.log(`日付フィルター適用: ${selectedDate}`);
        }

        const response = await pictureService.getPictureGroups(params);
        console.log(`取得したグループ数: ${response.groups.length}, 総数: ${response.total}`);

        if (isInitial) {
          console.log("グループデータを初期化して新しいデータを設定");
          setGroups(response.groups);
        } else {
          console.log("既存のグループデータに新しいデータを追加");
          setGroups((prev) => [...prev, ...response.groups]);
        }

        setHasMore(response.has_more);
        console.log(`次ページの存在: ${response.has_more}`);

        setOffset(currentOffset + LIMIT);
      } catch (error) {
        console.error("グループ取得エラー:", error);
      } finally {
        setLoading(false);
        console.log("グループデータ取得処理完了");
      }
    },
    [selectedCategory, selectedDate, loading],
  );

  /**
   * 初回読み込み＆フィルター条件変更時の処理
   */
  useEffect(() => {
    console.log("フィルター条件変更によるグループデータリセット");

    setGroups([]);
    setOffset(0);
    setHasMore(true);

    fetchGroups(0, true);
  }, [selectedCategory, selectedDate]); // fetchGroupsは依存関係から除外（無限ループ防止）

  /**
   * 追加のグループデータを読み込む関数
   */
  const loadMoreGroups = useCallback(() => {
    if (hasMore && !loading) {
      console.log(`追加グループデータの読み込み開始 (offset: ${offset})`);
      fetchGroups(offset);
    } else {
      console.log("追加読み込み条件を満たさないため、スキップ");
    }
  }, [hasMore, loading, offset, fetchGroups]);

  // === 外部に公開するAPI ===
  return {
    groups,
    categories,

    loading,
    hasMore,

    selectedCategory,
    selectedDate,
    setSelectedCategory,
    setSelectedDate,

    loadMoreGroups,
  };
};
