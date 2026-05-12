import { useState, useEffect } from 'react'
import { User, Shield, Palette, Key, LogOut, Save, Camera, Loader2, Smartphone, Trash2, Download, Monitor } from 'lucide-react'
import useAuthStore from '../store/authStore'
import useThemeStore from '../store/themeStore'
import api from '../api/axios'
import toast from 'react-hot-toast'
import SessionManager from '../components/SessionManager'

const SECTIONS = [
  { key: 'profile',    icon: User,    label: 'Profile' },
  { key: 'privacy',    icon: Shield,  label: 'Privacy' },
  { key: 'appearance', icon: Palette, label: 'Appearance' },
  { key: 'security',   icon: Key,     label: 'Security' },
  { key: 'sessions',   icon: Monitor, label: 'Sessions' },
  { key: 'data',       icon: Download, label: 'Your Data' },
]

function FieldLabel({ children }) {
  return <label className="settings-label">{children}</label>
}

function ToggleSwitch({ checked, onChange, label, description }) {
  return (
    <div className="settings-toggle-row">
      <div>
        <div className="settings-toggle-label">{label}</div>
        {description && <div className="settings-toggle-desc">{description}</div>}
      </div>
      <button type="button" className={`settings-switch ${checked ? 'active' : ''}`} onClick={onChange}>
        <span />
      </button>
    </div>
  )
}

// ─── Profile ──────────────────────────────────────────────────────────────────
function ProfileSettings() {
  const { user, updateUser } = useAuthStore()
  const [form, setForm] = useState({ bio: user?.bio || '', display_name: '', location: '', website: '' })
  const [saving, setSaving] = useState(false)
  const [uploadingAvatar, setUploadingAvatar] = useState(false)
  const [avatarPreview, setAvatarPreview] = useState(user?.avatar_url || null)

  useEffect(() => {
    if (!user?.username) return
    api.get(`/social/profile/${user.username}/`).then(({ data }) => {
      setForm(f => ({
        ...f,
        bio: data.user?.bio || user.bio || '',
        display_name: data.display_name || '',
        location: data.location || '',
        website: data.website || '',
      }))
    }).catch(() => {})
  }, [user?.username])

  const handleAvatarChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploadingAvatar(true)
    try {
      // Step 1: upload file, get URL
      const formData = new FormData()
      formData.append('file', file)
      const { data: upload } = await api.post('/chat/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const fileUrl = upload.file_url

      // Step 2: save URL to user profile (avatar_url_write maps to avatar_url_field)
      const { data: updated } = await api.put('/auth/profile/', { avatar_url_write: fileUrl })

      // Step 3: sync Zustand store + localStorage so all components update instantly
      const newAvatarUrl = updated.avatar_url || fileUrl
      updateUser({ avatar_url: newAvatarUrl })
      setAvatarPreview(newAvatarUrl)
      toast.success('Avatar updated!')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Upload failed')
    }
    setUploadingAvatar(false)
  }

  const save = async () => {
    setSaving(true)
    try {
      const { data: updated } = await api.put('/auth/profile/', { bio: form.bio })
      updateUser({ bio: updated.bio })
      try {
        await api.patch(`/social/profile/${user.username}/`, {
          display_name: form.display_name,
          location: form.location,
          website: form.website,
          bio: form.bio,
        })
      } catch {}
      toast.success('Profile updated!')
    } catch { toast.error('Failed to save') }
    setSaving(false)
  }

  return (
    <div className="settings-section">
      <div className="settings-section-head"><h2>Profile Settings</h2><p>Keep your public profile current and recognizable.</p></div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ position: 'relative' }}>
          <div className="avatar avatar-xl">
            {avatarPreview
              ? <img src={avatarPreview} alt="" key={avatarPreview} />
              : user?.avatar_url
                ? <img src={user.avatar_url} alt="" />
                : <span>{user?.username?.[0]?.toUpperCase()}</span>
            }
          </div>
          <label htmlFor="avatar-upload" style={{
            position: 'absolute', bottom: 0, right: 0, width: 28, height: 28,
            borderRadius: '50%', background: 'var(--primary)', border: '2px solid var(--bg-card)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer'
          }}>
            {uploadingAvatar ? <Loader2 size={13} color="white" className="spin" /> : <Camera size={13} color="white" />}
          </label>
          <input id="avatar-upload" type="file" accept="image/*" style={{ display: 'none' }} onChange={handleAvatarChange} />
        </div>
        <div>
          <div style={{ fontWeight: 600 }}>{user?.username}</div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Click the camera icon to upload</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <FieldLabel>Username</FieldLabel>
          <input value={user?.username || ''} disabled style={{ opacity: 0.5 }} />
        </div>
        <div>
          <FieldLabel>Email</FieldLabel>
          <input value={user?.email || ''} disabled style={{ opacity: 0.5 }} />
        </div>
        <div>
          <FieldLabel>Display Name</FieldLabel>
          <input value={form.display_name} onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))} placeholder="Your display name" />
        </div>
        <div>
          <FieldLabel>Location</FieldLabel>
          <input value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} placeholder="City, Country" />
        </div>
        <div style={{ gridColumn: '1/-1' }}>
          <FieldLabel>Website</FieldLabel>
          <input value={form.website} onChange={e => setForm(f => ({ ...f, website: e.target.value }))} placeholder="https://yourwebsite.com" type="url" />
        </div>
        <div style={{ gridColumn: '1/-1' }}>
          <FieldLabel>Bio</FieldLabel>
          <textarea value={form.bio} onChange={e => setForm(f => ({ ...f, bio: e.target.value }))} rows={3} placeholder="Tell people about yourself…" style={{ resize: 'vertical' }} maxLength={500} />
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textAlign: 'right', marginTop: 4 }}>{form.bio.length}/500</div>
        </div>
      </div>
      <button className="btn btn-primary" style={{ alignSelf: 'flex-start' }} onClick={save} disabled={saving}>
        {saving ? <Loader2 size={16} className="spin" /> : <Save size={16} />} Save Changes
      </button>
    </div>
  )
}

// ─── Appearance ───────────────────────────────────────────────────────────────
function AppearanceSettings() {
  const { theme, setTheme } = useThemeStore()
  const themes = [
    { key: 'dark',   label: '🌙 Dark',   desc: 'Easy on the eyes at night' },
    { key: 'light',  label: '☀️ Light',  desc: 'Bright and clean' },
    { key: 'system', label: '💻 System', desc: 'Follows your device setting' },
  ]

  return (
    <div className="settings-section">
      <div className="settings-section-head"><h2>Appearance</h2><p>Choose a theme with readable contrast for your environment.</p></div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {themes.map(t => (
          <div key={t.key} onClick={() => { setTheme(t.key); toast.success(`Switched to ${t.label} theme`) }}
            style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '14px 16px', borderRadius: 'var(--radius-md)',
              border: `2px solid ${theme === t.key ? 'var(--primary)' : 'var(--border)'}`,
              background: theme === t.key ? 'rgba(108,99,255,0.07)' : 'var(--bg-hover)',
              cursor: 'pointer', transition: 'all 0.2s'
            }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{t.label}</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>{t.desc}</div>
            </div>
            <div style={{
              width: 20, height: 20, borderRadius: '50%',
              border: `2px solid ${theme === t.key ? 'var(--primary)' : 'var(--border)'}`,
              background: theme === t.key ? 'var(--primary)' : 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              {theme === t.key && <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'white' }} />}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Privacy ──────────────────────────────────────────────────────────────────
function PrivacySettings() {
  const { user } = useAuthStore()
  const [settings, setSettings] = useState({ is_private: false, show_online_status: true, allow_messages_from: 'everyone' })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!user?.username) return
    api.get(`/social/profile/${user.username}/`).then(({ data }) => {
      setSettings({
        is_private: !!data.is_private,
        show_online_status: data.show_online_status !== false,
        allow_messages_from: data.allow_messages_from || 'everyone',
      })
    }).catch(() => {})
  }, [user?.username])

  const save = async () => {
    setSaving(true)
    try {
      await api.patch(`/social/profile/${user.username}/`, settings)
      toast.success('Privacy settings saved')
    } catch { toast.error('Failed to save') }
    setSaving(false)
  }

  return (
    <div className="settings-section">
      <div className="settings-section-head"><h2>Privacy</h2><p>Control who can reach you and see your activity.</p></div>
      <ToggleSwitch checked={settings.is_private} onChange={() => setSettings(s => ({ ...s, is_private: !s.is_private }))} label="Private Account" description="Only approved followers can see your posts" />
      <ToggleSwitch checked={settings.show_online_status} onChange={() => setSettings(s => ({ ...s, show_online_status: !s.show_online_status }))} label="Show Online Status" description="Let others see when you're online" />
      <div>
        <FieldLabel>Who can message you</FieldLabel>
        <select value={settings.allow_messages_from} onChange={e => setSettings(s => ({ ...s, allow_messages_from: e.target.value }))}>
          <option value="everyone">Everyone</option>
          <option value="friends">Friends Only</option>
          <option value="none">No One</option>
        </select>
      </div>
      <button className="btn btn-primary" style={{ alignSelf: 'flex-start' }} onClick={save} disabled={saving}>
        <Save size={16} /> Save Privacy Settings
      </button>
    </div>
  )
}

// ─── Security / 2FA ───────────────────────────────────────────────────────────
function SecuritySettings() {
  const [pwForm, setPwForm] = useState({ current: '', new: '', confirm: '' })
  const [savingPw, setSavingPw] = useState(false)
  const [totpData, setTotpData] = useState(null)
  const [totpToken, setTotpToken] = useState('')
  const [loadingTotp, setLoadingTotp] = useState(false)
  const [twoFaEnabled, setTwoFaEnabled] = useState(false)

  const changePassword = async () => {
    if (pwForm.new !== pwForm.confirm) { toast.error('Passwords do not match'); return }
    setSavingPw(true)
    try {
      await api.post('/auth/change-password/', { current_password: pwForm.current, new_password: pwForm.new })
      toast.success('Password changed!')
      setPwForm({ current: '', new: '', confirm: '' })
    } catch (e) { toast.error(e.response?.data?.error || 'Failed') }
    setSavingPw(false)
  }

  const setup2FA = async () => {
    setLoadingTotp(true)
    try {
      const { data } = await api.get('/auth/2fa/setup/')
      setTotpData(data)
    } catch { toast.error('Could not generate 2FA setup') }
    setLoadingTotp(false)
  }

  const confirm2FA = async () => {
    try {
      await api.post('/auth/2fa/setup/', { token: totpToken })
      setTwoFaEnabled(true)
      setTotpData(null)
      toast.success('2FA enabled! Your account is now more secure.')
    } catch (e) { toast.error(e.response?.data?.error || 'Invalid code') }
  }

  return (
    <div className="settings-section">
      <div className="settings-section-head"><h2>Security</h2><p>Protect your account with strong credentials and two-factor authentication.</p></div>

      {/* Password Change */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Change Password</h3>
        {['current', 'new', 'confirm'].map((field) => (
          <div key={field}>
            <FieldLabel>{field === 'confirm' ? 'Confirm New Password' : `${field} Password`}</FieldLabel>
            <input type="password" value={pwForm[field]} onChange={e => setPwForm(f => ({ ...f, [field]: e.target.value }))} placeholder="••••••••" />
          </div>
        ))}
        <button className="btn btn-primary" style={{ alignSelf: 'flex-start' }} onClick={changePassword} disabled={savingPw || !pwForm.current || !pwForm.new}>
          <Key size={16} /> Update Password
        </button>
      </div>

      {/* 2FA */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: 4 }}>Two-Factor Authentication</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {twoFaEnabled ? '✅ 2FA is enabled. Your account is protected.' : 'Add an extra layer of security using an authenticator app.'}
            </p>
          </div>
          {!twoFaEnabled && !totpData && (
            <button className="btn btn-secondary" onClick={setup2FA} disabled={loadingTotp}>
              <Smartphone size={14} /> {loadingTotp ? 'Loading…' : 'Enable 2FA'}
            </button>
          )}
        </div>

        {totpData && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Scan this QR code with <strong>Google Authenticator</strong>, <strong>Authy</strong>, or any TOTP app:
            </p>
            <img src={totpData.qr_code} alt="QR Code" style={{ width: 180, height: 180, borderRadius: 8, background: 'white', padding: 8 }} />
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Manual key: <code style={{ background: 'var(--bg-hover)', padding: '2px 6px', borderRadius: 4 }}>{totpData.manual_entry_key}</code>
            </p>
            <div style={{ display: 'flex', gap: 10 }}>
              <input placeholder="Enter 6-digit code" value={totpToken} onChange={e => setTotpToken(e.target.value)} maxLength={6} style={{ width: 160 }} />
              <button className="btn btn-primary" onClick={confirm2FA} disabled={totpToken.length < 6}>Verify & Enable</button>
              <button className="btn btn-ghost" onClick={() => setTotpData(null)}>Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Your Data (GDPR) ─────────────────────────────────────────────────────────
function DataSettings() {
  const { user, logout } = useAuthStore()
  const [delPw, setDelPw] = useState('')
  const [showDelete, setShowDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const exportData = async () => {
    try {
      const response = await api.get('/auth/export-data/', { responseType: 'blob' })
      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `mindconnect-data-${user.username}.json`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Your data download has started')
    } catch { toast.error('Export failed') }
  }

  const deleteAccount = async () => {
    if (!delPw) { toast.error('Enter your password to confirm'); return }
    setDeleting(true)
    try {
      await api.delete('/auth/delete-account/', { data: { password: delPw } })
      toast.success('Account deleted. Goodbye!')
      logout()
    } catch (e) { toast.error(e.response?.data?.error || 'Deletion failed') }
    setDeleting(false)
  }

  return (
    <div className="settings-section">
      <div className="settings-section-head"><h2>Your Data</h2><p>Export your information or permanently delete your account.</p></div>
      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: 8 }}>Export Your Data</h3>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 16 }}>
          Download a copy of all your posts, messages, and profile information in JSON format.
        </p>
        <button className="btn btn-secondary" onClick={exportData}><Download size={16} /> Download My Data</button>
      </div>

      <div className="card" style={{ borderColor: 'rgba(239,68,68,0.3)' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--danger)', marginBottom: 8 }}>Delete Account</h3>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 16 }}>
          This will permanently anonymize your account and remove your personal information. This cannot be undone.
        </p>
        {!showDelete ? (
          <button className="btn btn-danger" onClick={() => setShowDelete(true)}><Trash2 size={16} /> Delete My Account</button>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input type="password" placeholder="Confirm your password" value={delPw} onChange={e => setDelPw(e.target.value)} />
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-danger" onClick={deleteAccount} disabled={deleting}>
                {deleting ? <Loader2 size={14} className="spin" /> : <Trash2 size={14} />} {deleting ? 'Deleting…' : 'Confirm Delete'}
              </button>
              <button className="btn btn-ghost" onClick={() => { setShowDelete(false); setDelPw('') }}>Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Main Settings Page ───────────────────────────────────────────────────────
export default function SettingsPage() {
  const [section, setSection] = useState('profile')
  const { logout } = useAuthStore()

  const CONTENT = {
    profile:    <ProfileSettings />,
    privacy:    <PrivacySettings />,
    appearance: <AppearanceSettings />,
    security:   <SecuritySettings />,
    sessions:   <SessionManager />,
    data:       <DataSettings />,
  }

  return (
    <div className="settings-page">
      <div className="settings-page-head"><h1>Settings</h1><p>Manage your profile, privacy, security, and app preferences.</p></div>
      <div className="settings-grid">
        {/* Sidebar */}
        <div className="card settings-nav">
          {SECTIONS.map(({ key, icon: Icon, label }) => (
            <button key={key} onClick={() => setSection(key)} style={{
              display: 'flex', alignItems: 'center', gap: 10, width: '100%',
              padding: '10px 12px', borderRadius: 'var(--radius-md)',
              border: 'none', cursor: 'pointer', fontFamily: 'var(--font)',
              fontSize: '0.88rem', fontWeight: section === key ? 600 : 400,
              color: section === key ? 'var(--primary)' : 'var(--text-secondary)',
              background: section === key ? 'rgba(108,99,255,0.1)' : 'transparent',
              textAlign: 'left', transition: 'all 0.15s'
            }}>
              <Icon size={16} /> {label}
            </button>
          ))}
          <div style={{ margin: '8px 0', height: 1, background: 'var(--border)' }} />
          <button onClick={logout} style={{
            display: 'flex', alignItems: 'center', gap: 10, width: '100%',
            padding: '10px 12px', borderRadius: 'var(--radius-md)',
            border: 'none', cursor: 'pointer', fontFamily: 'var(--font)',
            fontSize: '0.88rem', color: 'var(--danger)', background: 'transparent', textAlign: 'left'
          }}>
            <LogOut size={16} /> Sign Out
          </button>
        </div>
        {/* Content */}
        <div className="card">{CONTENT[section]}</div>
      </div>
    </div>
  )
}
