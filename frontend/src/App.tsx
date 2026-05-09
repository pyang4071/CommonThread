import { useEffect, useLayoutEffect, useState } from 'react'
import { createBrowserRouter, Link, NavLink, Outlet, RouterProvider, useLocation, useNavigationType } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AddBook } from './pages/AddBook'
import { EditBook } from './pages/EditBook'
import { Home } from './pages/Home'
import { Archetypes } from './pages/Archetypes'
import { BookDetail } from './pages/BookDetail'
import { BookTypes } from './pages/BookTypes'
import { Books } from './pages/Books'
import { Genres } from './pages/Genres'
import { Tones } from './pages/Tones'
import { Tropes } from './pages/Tropes'
import { Admin } from './pages/Admin'
import { ArchetypeDetail } from './pages/ArchetypeDetail'
import { Friends } from './pages/Friends'
import { UserProfile } from './pages/UserProfile'
import { MyTags } from './pages/MyTags'
import { Profile } from './pages/Profile'
import { Shelf } from './pages/Shelf'
import { TropeDetail } from './pages/TropeDetail'
import { SimilarBooks } from './pages/SimilarBooks'
import { NotFound } from './pages/NotFound'
import { Unauthorized } from './pages/Unauthorized'
import { Login } from './pages/auth/Login'
import { SignUp } from './pages/auth/SignUp'
import { ForgotPassword } from './pages/auth/ForgotPassword'
import { ResetPassword } from './pages/auth/ResetPassword'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-100'
  }`

function Header() {
  const { user, profile, isAdmin, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const close = () => setMenuOpen(false)

  const navLinks = (
    <>
      <NavLink to="/books" className={navClass} onClick={close}>Books</NavLink>
      {user && <NavLink to="/shelf" className={navClass} onClick={close}>My Shelf</NavLink>}
      {user && <NavLink to="/my-tags" className={navClass} onClick={close}>My Tags</NavLink>}
      {user && <NavLink to="/friends" className={navClass} onClick={close}>Friends</NavLink>}
      <NavLink to="/tropes" className={navClass} onClick={close}>Tropes</NavLink>
      <NavLink to="/archetypes" className={navClass} onClick={close}>Archetypes</NavLink>
      {isAdmin && <NavLink to="/genres" className={navClass} onClick={close}>Genres</NavLink>}
      {isAdmin && <NavLink to="/book-types" className={navClass} onClick={close}>Book Types</NavLink>}
      {isAdmin && <NavLink to="/tones" className={navClass} onClick={close}>Tones</NavLink>}
      {isAdmin && <NavLink to="/admin" className={navClass} onClick={close}>Admin</NavLink>}
    </>
  )

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="px-6 py-4 flex items-center gap-6">
        <Link to="/" className="text-lg font-bold text-indigo-600 tracking-tight shrink-0">
          CommonThread
        </Link>
        {/* Desktop nav */}
        <nav className="hidden md:flex gap-1 flex-1">
          {navLinks}
        </nav>
        {/* Desktop auth */}
        <div className="hidden md:flex items-center gap-3 shrink-0">
          {user ? (
            <>
              <Link to="/profile" className="text-sm text-gray-500 hover:text-indigo-600 transition-colors" onClick={close}>
                {profile?.name ?? user.email}
              </Link>
              <button
                onClick={() => { signOut(); close() }}
                className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/auth/login" className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-md" onClick={close}>
                Sign in
              </Link>
              <Link to="/auth/signup" className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700" onClick={close}>
                Sign up
              </Link>
            </>
          )}
        </div>
        {/* Hamburger (mobile only) */}
        <button
          className="md:hidden ml-auto p-2 rounded-md text-gray-600 hover:bg-gray-100"
          onClick={() => setMenuOpen(o => !o)}
          aria-label="Toggle menu"
        >
          {menuOpen ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-gray-100 px-4 py-3 flex flex-col gap-1 animate-panel-in">
          {navLinks}
          <div className="border-t border-gray-100 mt-2 pt-2 flex flex-col gap-1">
            {user ? (
              <>
                <Link to="/profile" onClick={close}
                  className="px-4 py-2 rounded-md text-sm text-gray-600 hover:bg-gray-100">
                  {profile?.name ?? user.email}
                </Link>
                <button onClick={() => { signOut(); close() }}
                  className="text-left px-4 py-2 rounded-md text-sm text-gray-600 hover:bg-gray-100">
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link to="/auth/login" onClick={close}
                  className="px-4 py-2 rounded-md text-sm text-gray-600 hover:bg-gray-100">
                  Sign in
                </Link>
                <Link to="/auth/signup" onClick={close}
                  className="px-4 py-2 rounded-md text-sm bg-indigo-600 text-white hover:bg-indigo-700">
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
    </div>
  )
}

function scrollToTop() {
  window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  document.documentElement.scrollTop = 0
  document.body.scrollTop = 0
}

function ScrollToTop() {
  const { pathname } = useLocation()
  const navType = useNavigationType()
  useLayoutEffect(() => {
    if (navType !== 'POP') scrollToTop()
  }, [pathname, navType])
  useEffect(() => {
    if (navType !== 'POP') scrollToTop()
  }, [pathname, navType])
  return null
}

/** Root layout: provides context to all routes via Outlet. */
function RootLayout() {
  return (
    <ToastProvider>
      <AuthProvider>
        <ScrollToTop />
        <Outlet />
      </AuthProvider>
    </ToastProvider>
  )
}

window.history.scrollRestoration = 'manual'

// Intercept pushState to scroll to top at the earliest possible moment —
// before React starts rendering the new route, covering any timing gaps
// that useLayoutEffect alone cannot close.
const _origPushState = window.history.pushState.bind(window.history)
window.history.pushState = function (...args) {
  _origPushState(...args)
  scrollToTop()
}

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      // Auth pages — full screen, no app header
      { path: '/auth/login',           element: <Login /> },
      { path: '/auth/signup',          element: <SignUp /> },
      { path: '/auth/forgot-password', element: <ForgotPassword /> },
      { path: '/auth/reset-password',  element: <ResetPassword /> },

      // App pages — with header/layout
      { path: '/',              element: <AppLayout><Home /></AppLayout> },
      { path: '/books',         element: <AppLayout><ProtectedRoute><Books /></ProtectedRoute></AppLayout> },
      { path: '/books/new',     element: <AppLayout><ProtectedRoute><AddBook /></ProtectedRoute></AppLayout> },
      { path: '/books/:id',     element: <AppLayout><ProtectedRoute><BookDetail /></ProtectedRoute></AppLayout> },
      { path: '/books/:id/edit',   element: <AppLayout><ProtectedRoute adminOnly><EditBook /></ProtectedRoute></AppLayout> },
      { path: '/books/:id/similar', element: <AppLayout><ProtectedRoute><SimilarBooks /></ProtectedRoute></AppLayout> },
      { path: '/tropes',        element: <AppLayout><ProtectedRoute><Tropes /></ProtectedRoute></AppLayout> },
      { path: '/tropes/:id',    element: <AppLayout><TropeDetail /></AppLayout> },
      { path: '/archetypes',    element: <AppLayout><ProtectedRoute><Archetypes /></ProtectedRoute></AppLayout> },
      { path: '/archetypes/:id',element: <AppLayout><ArchetypeDetail /></AppLayout> },
      { path: '/genres',        element: <AppLayout><ProtectedRoute adminOnly><Genres /></ProtectedRoute></AppLayout> },
      { path: '/book-types',    element: <AppLayout><ProtectedRoute adminOnly><BookTypes /></ProtectedRoute></AppLayout> },
      { path: '/tones',         element: <AppLayout><ProtectedRoute adminOnly><Tones /></ProtectedRoute></AppLayout> },
      { path: '/admin',         element: <AppLayout><ProtectedRoute adminOnly><Admin /></ProtectedRoute></AppLayout> },
      { path: '/profile',       element: <AppLayout><ProtectedRoute><Profile /></ProtectedRoute></AppLayout> },
      { path: '/shelf',         element: <AppLayout><ProtectedRoute><Shelf /></ProtectedRoute></AppLayout> },
      { path: '/my-tags',       element: <AppLayout><ProtectedRoute><MyTags /></ProtectedRoute></AppLayout> },
      { path: '/friends',       element: <AppLayout><ProtectedRoute><Friends /></ProtectedRoute></AppLayout> },
      { path: '/users/:userId', element: <AppLayout><ProtectedRoute><UserProfile /></ProtectedRoute></AppLayout> },
      { path: '/unauthorized',  element: <AppLayout><Unauthorized /></AppLayout> },
      { path: '*',              element: <AppLayout><NotFound /></AppLayout> },
    ],
  },
])

function App() {
  return <RouterProvider router={router} />
}

export default App
