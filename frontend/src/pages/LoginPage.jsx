import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mail, Lock, Eye, EyeOff, ArrowRight, Zap } from 'lucide-react'
import useAuthStore from '../store/authStore'
import s from './Auth.module.css'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, loading, error, clearError } = useAuthStore()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPw, setShowPw] = useState(false)

  const set = (k, v) => { clearError(); setForm(f => ({ ...f, [k]: v })) }

  const submit = async (e) => {
    e.preventDefault()
    const ok = await login(form.email, form.password)
    if (ok) navigate('/chat')
  }

  return (
    <div className={s.shell}>

      {/* ── Left: visual panel ── */}
      <div className={s.visual}>
        <div className={s.mesh} />
        <div className={s.visualContent}>
          <div className={s.wordmark}>
            <Zap size={18} strokeWidth={2.5} />
            MindConnect
          </div>
          <h1 className={s.headline}>
            Where ideas<br />
            <span className={s.accent}>come alive.</span>
          </h1>
          <p className={s.sub}>
            Real-time messaging built for teams who move fast.
          </p>

          {/* Live chat preview */}
          <div className={s.preview}>
            <div className={s.previewBar}>
              <div className={s.previewDots}>
                <span /><span /><span />
              </div>
              <span className={s.previewTitle}>design-team</span>
            </div>
            <div className={s.previewBody}>
              <div className={s.pMsg}>
                <div className={s.pAvatar} style={{background:'#7c6af7'}}>S</div>
                <div className={s.pBubble}>
                  <span className={s.pName}>Sara</span>
                  <span>Just pushed the new mockups 🎨</span>
                </div>
              </div>
              <div className={s.pMsg}>
                <div className={s.pAvatar} style={{background:'#3ecf8e'}}>J</div>
                <div className={s.pBubble}>
                  <span className={s.pName}>James</span>
                  <span>These look incredible, shipping today?</span>
                </div>
              </div>
              <div className={[s.pMsg, s.pMsgOwn].join(' ')}>
                <div className={s.pBubbleOwn}>
                  <span>100% — already on staging ✅</span>
                </div>
              </div>
              <div className={s.pTyping}>
                <div className={s.pAvatar} style={{background:'#f59e0b'}}>A</div>
                <div className={s.typingDots}>
                  <span /><span /><span />
                </div>
              </div>
            </div>
          </div>

          <div className={s.stats}>
            <div className={s.stat}><strong>12k+</strong><span>Users</span></div>
            <div className={s.statDiv} />
            <div className={s.stat}><strong>99.9%</strong><span>Uptime</span></div>
            <div className={s.statDiv} />
            <div className={s.stat}><strong>&lt;50ms</strong><span>Latency</span></div>
          </div>
        </div>
      </div>

      {/* ── Right: form panel ── */}
      <div className={s.panel}>
        <div className={s.panelInner}>

          <div className={s.formHead}>
            <h2 className={s.formTitle}>Sign in</h2>
            <p className={s.formSub}>Good to see you again</p>
          </div>

          {error && (
            <div className={s.errorBanner}>
              <span className={s.errorDot} />
              {error}
            </div>
          )}

          <form onSubmit={submit} className={s.form}>
            <div className={s.field}>
              <label className={s.label}>Email</label>
              <div className={s.inputWrap}>
                <Mail size={15} className={s.inputIcon} />
                <input
                  className={s.input}
                  type="email"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={e => set('email', e.target.value)}
                  required autoFocus
                />
              </div>
            </div>

            <div className={s.field}>
              <div className={s.labelRow}>
                <label className={s.label}>Password</label>
                <Link to="/forgot-password" className={s.forgotLink}>Forgot?</Link>
              </div>
              <div className={s.inputWrap}>
                <Lock size={15} className={s.inputIcon} />
                <input
                  className={s.input}
                  type={showPw ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={form.password}
                  onChange={e => set('password', e.target.value)}
                  required
                />
                <button type="button" className={s.eyeBtn} onClick={() => setShowPw(v => !v)} tabIndex={-1}>
                  {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <button type="submit" className={s.submitBtn} disabled={loading}>
              {loading
                ? <span className={s.spinner} />
                : <><span>Continue</span><ArrowRight size={16} /></>
              }
            </button>
          </form>

          <p className={s.switchLine}>
            No account?{' '}
            <Link to="/register" className={s.switchLink}>Create one free</Link>
          </p>
        </div>
      </div>

    </div>
  )
}
