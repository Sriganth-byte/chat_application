import { useState, useEffect } from 'react'
import { Bookmark, Loader2 } from 'lucide-react'
import api from '../api/axios'
import PostCard from '../components/PostCard'

export default function SavedPage() {
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/posts/saved/').then(r => {
      setPosts(r.data.results || r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '20px 16px' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: 20 }}>
        Saved Posts
      </h1>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <Loader2 size={32} className="spin" color="var(--primary)" />
        </div>
      ) : posts.length === 0 ? (
        <div className="empty-state">
          <Bookmark size={48} />
          <h3>No saved posts</h3>
          <p>Bookmark posts to read them later</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {posts.map(p => <PostCard key={p.id} post={p} onDelete={id => setPosts(ps => ps.filter(p => p.id !== id))} />)}
        </div>
      )}
    </div>
  )
}
