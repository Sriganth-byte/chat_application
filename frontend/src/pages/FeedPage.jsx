import { useState, useEffect, useCallback } from 'react'
import { Loader2, Sparkles, TrendingUp } from 'lucide-react'
import api from '../api/axios'
import PostCard from '../components/PostCard'
import PostComposer from '../components/PostComposer'
import StoriesBar from '../components/StoriesBar'
import TrendingPanel from '../components/TrendingPanel'
import SuggestionsPanel from '../components/SuggestionsPanel'
import useInfiniteScroll from '../hooks/useInfiniteScroll'

export default function FeedPage() {
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)

  const fetchFeed = useCallback(async (pageNum = 1) => {
    if (pageNum === 1) setLoading(true)
    else setLoadingMore(true)
    try {
      const { data } = await api.get(`/posts/feed/?page=${pageNum}`)
      const newPosts = data.results || data
      if (pageNum === 1) {
        setPosts(newPosts)
      } else {
        setPosts(prev => {
          const existingIds = new Set(prev.map(p => p.id))
          return [...prev, ...newPosts.filter(p => !existingIds.has(p.id))]
        })
      }
      setHasMore(!!data.next)
    } catch {
      setHasMore(false)
    }
    setLoading(false)
    setLoadingMore(false)
  }, [])

  useEffect(() => { fetchFeed(1) }, [fetchFeed])

  const loadMore = useCallback(() => {
    if (!loadingMore && hasMore) {
      const next = page + 1
      setPage(next)
      fetchFeed(next)
    }
  }, [loadingMore, hasMore, page, fetchFeed])

  // Infinite scroll sentinel
  const sentinelRef = useInfiniteScroll(loadMore, hasMore, loadingMore)

  const handleNewPost = (post) => setPosts(prev => [post, ...prev])
  const handleDeletePost = (postId) => setPosts(prev => prev.filter(p => p.id !== postId))

  return (
    <div className="feed-layout-wide">
      {/* Main Feed */}
      <main>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <section className="feed-hero fade-in-up">
            <div>
              <div className="feed-kicker"><Sparkles size={14} /> Live social feed</div>
              <h1>Discover what your circle is sharing</h1>
              <p>Real-time posts from friends, creators, and trending conversations across MindConnect.</p>
            </div>
            <a className="feed-hero-action" href="/explore"><TrendingUp size={16} /> Explore</a>
          </section>
          <StoriesBar />
          <PostComposer onPost={handleNewPost} />

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
              <Loader2 size={32} className="spin" color="var(--primary)" />
            </div>
          ) : posts.length === 0 ? (
            <div className="empty-state">
              <div style={{ fontSize: 48 }}>👋</div>
              <h3>Your feed is empty</h3>
              <p>Follow people or add friends to see their posts here. Or <a href="/explore">Explore</a> trending content!</p>
            </div>
          ) : (
            <>
              {posts.map(post => (
                <PostCard key={post.id} post={post} onDelete={handleDeletePost} />
              ))}

              {/* Infinite scroll sentinel */}
              <div ref={sentinelRef} style={{ height: 1 }} />

              {loadingMore && (
                <div style={{ display: 'flex', justifyContent: 'center', padding: 20 }}>
                  <Loader2 size={24} className="spin" color="var(--primary)" />
                </div>
              )}

              {!hasMore && posts.length > 0 && (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem', padding: 20 }}>
                  You've seen everything! 🎉
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* Right Panel */}
      <aside className="panel-right" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <SuggestionsPanel />
        <TrendingPanel />
      </aside>
    </div>
  )
}
