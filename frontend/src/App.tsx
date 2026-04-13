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
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-6">
      <Link to="/" className="text-lg font-bold text-indigo-600 tracking-tight">
        CommonThread
      </Link>
      <nav className="flex gap-1 flex-1">
        <NavLink to="/books" className={navClass}>Books</NavLink>
        {user && <NavLink to="/shelf" className={navClass}>My Shelf</NavLink>}
        {user && <NavLink to="/my-tags" className={navClass}>My Tags</NavLink>}
        {user && <NavLink to="/friends" className={navClass}>Friends</NavLink>}
        <NavLink to="/tropes" className={navClass}>Tropes</NavLink>
        <NavLink to="/archetypes" className={navClass}>Archetypes</NavLink>
        {isAdmin && <NavLink to="/genres" className={navClass}>Genres</NavLink>}
        {isAdmin && <NavLink to="/book-types" className={navClass}>Book Types</NavLink>}
        {isAdmin && <NavLink to="/tones" className={navClass}>Tones</NavLink>}
        {isAdmin && <NavLink to="/admin" className={navClass}>Admin</NavLink>}
      </nav>
      {user ? (
        <div className="flex items-center gap-3">
          <Link to="/profile" className="text-sm text-gray-500 hover:text-indigo-600 transition-colors">
            {user.user_metadata?.name ?? user.email}
          </Link>
          <button
            onClick={signOut}
            className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Sign out
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <Link to="/auth/login" className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-md">
            Sign in
          </Link>
          <Link to="/auth/signup" className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
            Sign up
          </Link>
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
          <Route path="/books/:id/edit" element={<Layout><ProtectedRoute><EditBook /></ProtectedRoute></Layout>} />
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
