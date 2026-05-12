import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useThemeStore = create(
  persist(
    (set, get) => ({
      theme: 'dark', // 'dark' | 'light' | 'system'

      setTheme: (theme) => {
        set({ theme })
        applyTheme(theme)
      },

      initTheme: () => {
        applyTheme(get().theme)
      }
    }),
    { name: 'mc-theme' }
  )
)

function applyTheme(theme) {
  const root = document.documentElement
  if (theme === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    root.setAttribute('data-theme', prefersDark ? 'dark' : 'light')
  } else {
    root.setAttribute('data-theme', theme)
  }
}

// Listen for system preference changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  const store = useThemeStore.getState()
  if (store.theme === 'system') applyTheme('system')
})

export default useThemeStore
