import { useState, useEffect } from 'react'
import { Plus, X } from 'lucide-react'
import api from '../api/axios'
import useAuthStore from '../store/authStore'

function StoryAvatar({ group, onClick }) {
  const user = group.user
  const initials = user?.username?.[0]?.toUpperCase() || '?'
  const isOwn = useAuthStore(s => s.user?.id === user?.id)

  return (
    <div className="story-item" onClick={onClick}>
      <div className={`story-ring ${group.has_unseen ? '' : 'seen'} ${isOwn ? 'mine' : ''}`}>
        <div className="story-avatar">
          {user?.avatar_url || user?.avatar ? (
            <img src={user.avatar_url || user.avatar} alt={user.username} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} />
          ) : (
            <div style={{
              width: '100%', height: '100%', borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--primary), var(--secondary))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 700, color: 'white', fontSize: '1.2rem'
            }}>{initials}</div>
          )}
        </div>
      </div>
      <span className="story-username">{user?.username}</span>
    </div>
  )
}

function StoryViewer({ groups, startGroupIndex, onClose }) {
  const [groupIdx, setGroupIdx] = useState(startGroupIndex)
  const [storyIdx, setStoryIdx] = useState(0)
  const [progress, setProgress] = useState(0)

  const group = groups[groupIdx]
  const story = group?.stories?.[storyIdx]

  useEffect(() => {
    if (!story) return
    api.post(`/stories/${story.id}/view/`).catch(() => {})
    setProgress(0)
    const interval = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          clearInterval(interval)
          goNext()
          return 100
        }
        return p + 2
      })
    }, 100)
    return () => clearInterval(interval)
  }, [story?.id])

  const goNext = () => {
    if (storyIdx < (group?.stories?.length || 0) - 1) {
      setStoryIdx(i => i + 1)
    } else if (groupIdx < groups.length - 1) {
      setGroupIdx(i => i + 1)
      setStoryIdx(0)
    } else {
      onClose()
    }
  }

  const goPrev = () => {
    if (storyIdx > 0) {
      setStoryIdx(i => i - 1)
    } else if (groupIdx > 0) {
      setGroupIdx(i => i - 1)
      setStoryIdx(0)
    }
  }

  if (!story) return null

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.95)',
      zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center'
    }}>
      <div style={{
        width: '100%', maxWidth: 400, height: '100dvh', maxHeight: 720,
        position: 'relative', overflow: 'hidden', borderRadius: 16,
        background: story.bg_color || '#1a1a2e'
      }}>
        {/* Progress bars */}
        <div style={{ display: 'flex', gap: 4, padding: '12px 12px 0', position: 'absolute', top: 0, left: 0, right: 0, zIndex: 10 }}>
          {group.stories.map((_, i) => (
            <div key={i} style={{ flex: 1, height: 3, background: 'rgba(255,255,255,0.3)', borderRadius: 2, overflow: 'hidden' }}>
              <div style={{
                height: '100%', background: 'white', borderRadius: 2,
                width: i < storyIdx ? '100%' : i === storyIdx ? `${progress}%` : '0%',
                transition: 'width 0.1s linear'
              }} />
            </div>
          ))}
        </div>

        {/* Header */}
        <div style={{
          position: 'absolute', top: 24, left: 0, right: 0, zIndex: 10,
          display: 'flex', alignItems: 'center', gap: 10, padding: '0 12px'
        }}>
          <div className="avatar avatar-sm">
            {group.user?.avatar_url ? <img src={group.user.avatar_url} alt="" /> : <span>{group.user?.username?.[0]?.toUpperCase()}</span>}
          </div>
          <span style={{ color: 'white', fontWeight: 600, fontSize: '0.9rem', flex: 1 }}>{group.user?.username}</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>
            <X size={22} />
          </button>
        </div>

        {/* Media */}
        <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {story.media_url && story.media_type === 'image' && (
            <img src={story.media_url} style={{ width: '100%', height: '100%', objectFit: 'cover' }} alt="" />
          )}
          {story.text_content && (
            <div style={{
              textAlign: 'center', padding: 32, color: story.text_color || 'white',
              fontSize: '1.4rem', fontWeight: 700, textShadow: '0 2px 8px rgba(0,0,0,0.5)'
            }}>
              {story.text_content}
            </div>
          )}
        </div>

        {/* Caption */}
        {story.caption && (
          <div style={{
            position: 'absolute', bottom: 0, left: 0, right: 0,
            background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
            padding: '40px 20px 20px', color: 'white', fontSize: '0.9rem'
          }}>
            {story.caption}
          </div>
        )}

        {/* Tap zones */}
        <div onClick={goPrev} style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '35%', cursor: 'pointer' }} />
        <div onClick={goNext} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '35%', cursor: 'pointer' }} />
      </div>
    </div>
  )
}

export default function StoriesBar() {
  const [groups, setGroups] = useState([])
  const [viewerOpen, setViewerOpen] = useState(false)
  const [viewerGroupIdx, setViewerGroupIdx] = useState(0)
  const { user } = useAuthStore()

  useEffect(() => {
    api.get('/stories/').then(r => setGroups(r.data)).catch(() => {})
  }, [])

  const openStory = (idx) => {
    setViewerGroupIdx(idx)
    setViewerOpen(true)
  }

  if (groups.length === 0) return null

  return (
    <>
      <div className="card" style={{ padding: '16px 20px' }}>
        <div className="stories-bar">
          {/* Add story button */}
          <div className="story-item" onClick={() => {}}>
            <div style={{
              width: 68, height: 68, borderRadius: '50%',
              background: 'var(--bg-hover)', border: '2px dashed var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', transition: 'all 0.2s'
            }}>
              <Plus size={24} color="var(--primary)" />
            </div>
            <span className="story-username">Add Story</span>
          </div>
          {groups.map((group, idx) => (
            <StoryAvatar key={group.user?.id} group={group} onClick={() => openStory(idx)} />
          ))}
        </div>
      </div>

      {viewerOpen && (
        <StoryViewer
          groups={groups}
          startGroupIndex={viewerGroupIdx}
          onClose={() => setViewerOpen(false)}
        />
      )}
    </>
  )
}
