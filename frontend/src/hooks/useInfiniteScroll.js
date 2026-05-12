import { useEffect, useRef, useCallback } from 'react'

/**
 * useInfiniteScroll — fires `onLoadMore` when the sentinel element enters viewport
 * @param {function} onLoadMore - callback to load next page
 * @param {boolean} hasMore - whether there are more pages
 * @param {boolean} loading - whether a load is in progress
 */
export default function useInfiniteScroll(onLoadMore, hasMore, loading) {
  const sentinelRef = useRef(null)

  const handleIntersect = useCallback((entries) => {
    const [entry] = entries
    if (entry.isIntersecting && hasMore && !loading) {
      onLoadMore()
    }
  }, [onLoadMore, hasMore, loading])

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return

    const observer = new IntersectionObserver(handleIntersect, {
      root: null,
      rootMargin: '200px',
      threshold: 0.1,
    })
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [handleIntersect])

  return sentinelRef
}
