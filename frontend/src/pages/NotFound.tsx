import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-6xl font-bold text-gray-200 select-none">404</p>
      <h1 className="mt-4 text-xl font-semibold text-gray-800">Page not found</h1>
      <p className="mt-2 text-sm text-gray-500">
        The page you're looking for doesn't exist or was moved.
      </p>
      <Link
        to="/"
        className="mt-6 px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
      >
        Go home
      </Link>
    </div>
  )
}
