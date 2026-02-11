import { useEffect, useRef, useCallback } from "react";

/**
 * 無限スクロール実装のためのカスタムフック
 *
 * このフックは Intersection Observer API を使用して、
 * 指定された要素が画面に表示されたときに追加データの読み込みをトリガーします。
 */

interface UseInfiniteScrollProps {
  hasMore: boolean; // まだ読み込めるデータがあるかどうか
  loading: boolean; // 現在読み込み中かどうか
  onLoadMore: () => void; // 追加データを読み込む関数
  threshold?: number; // 発火するタイミング（下端からの距離、ピクセル単位）
}

export const useInfiniteScroll = ({
  hasMore,
  loading,
  onLoadMore,
  threshold = 200,
}: UseInfiniteScrollProps) => {
  // 監視対象となる要素への参照
  // この要素が画面に表示されると追加読み込みが発生します
  const sentinelRef = useRef<HTMLDivElement>(null);

  /**
   * Intersection Observer のコールバック関数
   * 監視対象要素が画面内に入ったかどうかを判定し、
   * 条件を満たす場合に追加データの読み込みを実行します
   */
  const handleIntersect = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const target = entries[0];

      // 以下の条件がすべて満たされた場合に追加読み込みを実行：
      // 1. 監視要素が画面内に表示されている
      // 2. まだ読み込めるデータが存在する
      // 3. 現在読み込み処理中ではない
      if (target.isIntersecting && hasMore && !loading) {
        console.log("無限スクロール: 追加データの読み込みを開始");
        onLoadMore();
      }
    },
    [hasMore, loading, onLoadMore],
  );

  /**
   * Intersection Observer の設定と監視開始
   *
   * useEffect を使用して、依存関係が変更されるたびに
   * Observer を再設定します
   */
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) {
      // 監視対象要素がまだマウントされていない場合は何もしない
      return;
    }

    // Intersection Observer を作成
    // rootMargin で指定した距離だけ監視領域を拡張することで、
    // 実際に画面下端に到達する前に読み込みを開始できます
    const observer = new IntersectionObserver(handleIntersect, {
      rootMargin: `${threshold}px`, // 下端より指定されたピクセル手前で発火
      threshold: 0, // 要素が少しでも見えた時点で発火
    });

    // 要素の監視を開始
    observer.observe(sentinel);
    console.log("無限スクロール: 監視を開始しました");

    // クリーンアップ関数
    // コンポーネントのアンマウント時や依存関係の変更時に
    // Observer の監視を停止します
    return () => {
      console.log("無限スクロール: 監視を停止しました");
      observer.unobserve(sentinel);
    };
  }, [handleIntersect, threshold]);

  // 監視対象要素への参照を返す
  // 呼び出し元でこの ref を適切な要素に設定する必要があります
  return sentinelRef;
};
