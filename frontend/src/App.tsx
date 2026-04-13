import { useState } from 'react'
import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
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
import { NotFound } from './pages/NotFound'
import { Login } from './pages/auth/Login'
import { SignUp } from './pages/auth/SignUp'
import { ForgotPassword } from './pages/auth/ForgotPassword'
import { ResetPassword } from './pages/auth/ResetPassword'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-100'
  }`

function Header() {
  const { user, isAdmin, signOut } = useAuth()
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
                {user.user_metadata?.name ?? user.email}
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
                  {user.user_metadata?.name ?? user.email}
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

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
      <AuthProvider>
        <Routes>
          {/* Auth pages — full screen, no app header */}
          <Route path="/auth/login" element={<Login />} />
          <Route path="/auth/signup" element={<SignUp />} />
          <Route path="/auth/forgot-password" element={<ForgotPassword />} />
          <Route path="/auth/reset-password" element={<ResetPassword />} />

          {/* App pages — with header */}
          <Route path="/" element={<Layout><Home /></Layout>} />
          <Route path="/books" element={<Layout><ProtectedRoute><Books /></ProtectedRoute></Layout>} />
          <Route path="/books/new" element={<Layout><ProtectedRoute><AddBook /></ProtectedRoute></Layout>} />
          <Route path="/books/:id" element={<Layout><ProtectedRoute><BookDetail /></ProtectedRoute></Layout>} />
          <Route path="/books/:id/edit" element={<Layout><ProtectedRoute adminOnly><EditBook /></ProtectedRoute></Layout>} />
          <Route path="/tropes" element={<Layout><ProtectedRoute><Tropes /></ProtectedRoute></Layout>} />
          <Route path="/tropes/:id" element={<Layout><TropeDetail /></Layout>} />
          <Route path="/archetypes" element={<Layout><ProtectedRoute><Archetypes /></ProtectedRoute></Layout>} />
          <Route path="/archetypes/:id" element={<Layout><ArchetypeDetail /></Layout>} />
          <Route path="/genres" element={<Layout><ProtectedRoute adminOnly><Genres /></ProtectedRoute></Layout>} />
          <Route path="/book-types" element={<Layout><ProtectedRoute adminOnly><BookTypes /></ProtectedRoute></Layout>} />
          <Route path="/tones" element={<Layout><ProtectedRoute adminOnly><Tones /></ProtectedRoute></Layout>} />
          <Route path="/admin" element={<Layout><ProtectedRoute><Admin /></ProtectedRoute></Layout>} />
          <Route path="/profile" element={<Layout><ProtectedRoute><Profile /></ProtectedRoute></Layout>} />
          <Route path="/shelf" element={<Layout><ProtectedRoute><Shelf /></ProtectedRoute></Layout>} />
          <Route path="/my-tags" element={<Layout><ProtectedRoute><MyTags /></ProtectedRoute></Layout>} />
          <Route path="/friends" element={<Layout><ProtectedRoute><Friends /></ProtectedRoute></Layout>} />
          <Route path="/users/:userId" element={<Layout><ProtectedRoute><UserProfile /></ProtectedRoute></Layout>} />
          <Route path="*" element={<Layout><NotFound /></Layout>} />
        </Routes>
      </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  )
}

export default App
