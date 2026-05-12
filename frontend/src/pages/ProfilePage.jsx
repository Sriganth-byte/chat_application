import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Edit3, MapPin, Link as LinkIcon, UserPlus, UserMinus, MessageSquare, Users, Heart, Loader2, Check, X } from 'lucide-react'
import api from '../api/axios'
import useAuthStore from '../store/authStore'
import PostCard from '../components/PostCard'
import toast from 'react-hot-toast'

function StatBadge({ value, label }) {
  return (
    <div style={{ textAlign: 'center', cursor: 'default' }}>
      <div style={{ fontWeight: 700, fontSize: '1.2rem', color: 'var(--text-primary)' }}>{value}</div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
    </div>
  )
}

export default function ProfilePage() {
  const { username } = useParams()
  const { user: me } = useAuthStore()
  const [profile, setProfile] = useState(null)
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const isMe = me?.username === username

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.get(`/social/profile/${username}/`),
      api.get(`/posts/user/${username}/`)
    ]).then(([pRes, postsRes]) => {
      setProfile(pRes.data)
      setPosts(postsRes.data.results || postsRes.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [username])

  const handleFriendRequest = async () => {
    setActionLoading(true)
    try {
      if (profile.is_friend) {
        // Unfriend
        await api.delete(`/social/friends/${profile.user.id}/`)
        setProfile(p => ({ ...p, is_friend: false, pending_request: null }))
        toast.success('Unfriended')

      } else if (profile.pending_request === 'sent') {
        // Already sent — do nothing, just inform
        toast('Request already sent — waiting for them to accept', { icon: '⏳' })

      } else if (profile.pending_request === 'received') {
        // They sent YOU a request — find and accept it
        const { data: requests } = await api.get('/social/friend-requests/?direction=received')
        const req = requests.find(r => r.sender?.id === profile.user.id)
        if (req) {
          await api.patch(`/social/friend-request/${req.id}/`, { action: 'accept' })
          setProfile(p => ({ ...p, is_friend: true, pending_request: null }))
          toast.success(`You and ${profile.user.username} are now friends! 🎉`)
        } else {
          toast.error('Could not find the request — try refreshing')
        }

      } else {
        // Send new request
        await api.post('/social/friend-request/', { user_id: profile.user.id })
        setProfile(p => ({ ...p, pending_request: 'sent' }))
        toast.success('Friend request sent!')
      }
    } catch (e) {
      const resp = e.response?.data || {}
      if (resp.direction === 'received' && resp.request) {
        // They already sent us a request — accept it immediately (no second click needed)
        try {
          await api.patch(`/social/friend-request/${resp.request_id}/`, { action: 'accept' })
          setProfile(p => ({ ...p, is_friend: true, pending_request: null }))
          toast.success(`You and ${profile.user.username} are now friends! 🎉`)
        } catch {
          // If accept also fails, at least update UI state
          setProfile(p => ({ ...p, pending_request: 'received' }))
          toast(`${profile.user.username} sent you a request — tap Accept to confirm`, { icon: '👆', duration: 4000 })
        }
      } else if (resp.direction === 'sent') {
        setProfile(p => ({ ...p, pending_request: 'sent' }))
        toast('Request already sent', { icon: '⏳' })
      } else {
        toast.error(resp.error || 'Failed')
      }
    }
    setActionLoading(false)
  }

  const handleFollow = async () => {
    setActionLoading(true)
    try {
      const { data } = await api.post(`/social/follow/${profile.user.id}/`)
      setProfile(p => ({
        ...p,
        is_following: data.following,
        followers_count: data.following ? p.followers_count + 1 : p.followers_count - 1
      }))
    } catch {}
    setActionLoading(false)
  }

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
      <Loader2 size={32} className="spin" color="var(--primary)" />
    </div>
  )

  if (!profile) return (
    <div className="empty-state" style={{ padding: 80 }}>
      <h3>User not found</h3>
    </div>
  )

  const { user } = profile
  const initials = user?.username?.[0]?.toUpperCase() || '?'

  return (
    <div style={{ maxWidth: 780, margin: '0 auto', padding: '20px 16px' }}>
      {/* Profile Card */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 20 }}>
        {/* Cover */}
        <div className="profile-cover">
          {profile.cover_photo && <img src={profile.cover_photo} alt="cover" />}
        </div>

        {/* Info Section */}
        <div className="profile-info-section" style={{ paddingTop: 60 }}>
          {/* Avatar */}
          <div className="profile-avatar-wrapper">
            <div className="avatar avatar-xl">
              {user?.avatar_url || user?.avatar ? (
                <img src={user.avatar_url || user.avatar} alt={user.username} />
              ) : <span>{initials}</span>}
            </div>
          </div>

          {/* Actions */}
          {!isMe && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginBottom: 12 }}>
              <Link to="/chat" className="btn btn-secondary btn-sm">
                <MessageSquare size={16} /> Message
              </Link>
              <button className="btn btn-secondary btn-sm" onClick={handleFollow} disabled={actionLoading}>
                {profile.is_following ? 'Following' : 'Follow'}
              </button>
              <button
                className={`btn btn-sm ${profile.is_friend ? 'btn-secondary' : 'btn-primary'}`}
                onClick={handleFriendRequest}
                disabled={actionLoading}
              >
                {profile.is_friend ? <><UserMinus size={16}/> Unfriend</> :
                 profile.pending_request === 'sent' ? <><Check size={16}/> Sent</> :
                 profile.pending_request === 'received' ? <><UserPlus size={16}/> Accept</> :
                 <><UserPlus size={16}/> Add Friend</>}
              </button>
            </div>
          )}
          {isMe && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
              <Link to="/settings" className="btn btn-secondary btn-sm">
                <Edit3 size={16} /> Edit Profile
              </Link>
            </div>
          )}

          {/* Name & Bio */}
          <h1 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: 4 }}>
            {profile.display_name || user?.username}
          </h1>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 8 }}>@{user?.username}</div>
          {user?.bio && <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', marginBottom: 12, lineHeight: 1.6 }}>{user.bio}</p>}

          {/* Location / Website */}
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 16 }}>
            {profile.location && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                <MapPin size={14} /> {profile.location}
              </span>
            )}
            {profile.website && (
              <a href={profile.website} target="_blank" rel="noopener noreferrer"
                style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.82rem', color: 'var(--primary)' }}>
                <LinkIcon size={14} /> {profile.website.replace(/^https?:\/\//, '')}
              </a>
            )}
          </div>

          {/* Stats */}
          <div style={{ display: 'flex', gap: 32, padding: '16px 0', borderTop: '1px solid var(--border)' }}>
            <StatBadge value={profile.posts_count} label="Posts" />
            <StatBadge value={profile.friends_count} label="Friends" />
            <StatBadge value={profile.followers_count} label="Followers" />
            <StatBadge value={profile.following_count} label="Following" />
          </div>
        </div>
      </div>

      {/* Posts */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Posts
        </h2>
        {posts.length === 0 ? (
          <div className="empty-state">
            <Heart size={40} />
            <h3>No posts yet</h3>
            <p>{isMe ? 'Share your first post!' : `${user?.username} hasn't posted yet`}</p>
          </div>
        ) : (
          posts.map(post => <PostCard key={post.id} post={post} />)
        )}
      </div>
    </div>
  )
}
