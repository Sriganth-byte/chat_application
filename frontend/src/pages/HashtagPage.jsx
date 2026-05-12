import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Hash, TrendingUp, Users, Eye } from 'lucide-react'
import api from '../api/axios'
import PostCard from '../components/PostCard'
import { motion } from 'framer-motion'

export default function HashtagPage() {
  const { tag } = useParams()
  const cleanTag = tag?.replace(/^#/, '')
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ count: 0 })
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [relatedTags, setRelatedTags] = useState([])

  useEffect(() => {
    setPosts([])
    setPage(1)
    setHasMore(true)
    fetchPosts(1, true)
    fetchRelatedTags()
  }, [cleanTag])

  const fetchRelatedTags = async () => {
    try {
      const { data } = await api.get('/posts/trending/')
      const tags = (data.hashtags || data || [])
        .map(t => (typeof t === 'string' ? t : t.tag || t.name || ''))
        .filter(t => t && t !== cleanTag)
        .slice(0, 5)
      setRelatedTags(tags)
    } catch { /* silently ignore */ }
  }

  const fetchPosts = async (pageNum = 1, reset = false) => {
    if (pageNum === 1) setLoading(true)
    else setLoadingMore(true)
    try {
      const { data } = await api.get(`/posts/hashtag/${cleanTag}/?page=${pageNum}`)
      const results = data.results || data
      if (reset) {
        setPosts(results)
        setStats({ count: data.count || results.length })
      } else {
        setPosts(prev => [...prev, ...results])
      }
      setHasMore(!!data.next)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
    setLoadingMore(false)
  }

  const loadMore = () => {
    if (!hasMore || loadingMore) return
    const next = page + 1
    setPage(next)
    fetchPosts(next)
  }

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '20px 16px' }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card"
        style={{
          marginBottom: 24,
          background: 'linear-gradient(135deg, var(--primary), var(--secondary))',
          border: 'none',
          padding: '28px 24px',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        {/* Background decorative element */}
        <div style={{
          position: 'absolute', right: -20, top: -20, width: 120, height: 120,
          borderRadius: '50%', background: 'rgba(255,255,255,0.1)'
        }} />
        <div style={{
          position: 'absolute', right: 30, bottom: -30, width: 80, height: 80,
          borderRadius: '50%', background: 'rgba(255,255,255,0.07)'
        }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
          <div style={{
            width: 48, height: 48, borderRadius: '50%', background: 'rgba(255,255,255,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Hash size={24} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'white', margin: 0 }}>
              #{cleanTag}
            </h1>
            <p style={{ fontSize: '0.82rem', color: 'rgba(255,255,255,0.75)', margin: 0 }}>
              Trending hashtag
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 20, marginTop: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <TrendingUp size={14} color="rgba(255,255,255,0.8)" />
            <span style={{ fontSize: '0.82rem', color: 'rgba(255,255,255,0.9)', fontWeight: 600 }}>
              {stats.count} posts
            </span>
          </div>
        </div>
      </motion.div>

      {/* Related tags */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        {['technology', 'coding', 'webdev', 'mindconnect', 'design'].filter(t => t !== cleanTag).slice(0, 4).map(t => (
          <Link key={t} to={`/hashtag/${t}`} style={{
            padding: '4px 12px', borderRadius: 'var(--radius-full)',
            background: 'var(--bg-hover)', border: '1px solid var(--border)',
            fontSize: '0.78rem', color: 'var(--text-secondary)',
            textDecoration: 'none', transition: 'all 0.2s'
          }}>
            #{t}
          </Link>
        ))}
      </div>

      {/* Posts */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[1, 2, 3].map(i => (
            <div key={i} className="card" style={{ height: 180, background: 'var(--bg-hover)' }}>
              <div style={{ display: 'flex', gap: 12, padding: 16 }}>
                <div style={{ width: 44, height: 44, borderRadius: '50%', background: 'var(--border)' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ height: 12, background: 'var(--border)', borderRadius: 6, marginBottom: 8, width: '40%' }} />
                  <div style={{ height: 10, background: 'var(--border)', borderRadius: 6, width: '70%' }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : posts.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
          <Hash size={48} style={{ color: 'var(--text-muted)', marginBottom: 16 }} />
          <h3 style={{ fontWeight: 600, marginBottom: 8 }}>No posts yet</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Be the first to post with #{cleanTag}!
          </p>
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {posts.map(post => (
              <motion.div key={post.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <PostCard post={post} />
              </motion.div>
            ))}
          </div>
          {hasMore && (
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <button className="btn btn-secondary" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? 'Loading…' : 'Load more'}
              </button>
            </div>
          )}
          {!hasMore && posts.length > 5 && (
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: 16 }}>
              You've seen all posts with #{cleanTag} 🎉
            </p>
          )}
        </>
      )}
    </div>
  )
}
