import { Link } from 'react-router-dom'

export function Unauthorized() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-6xl font-bold text-gray-200 select-none">403</p>
      <h1 className="mt-4 text-xl font-semibold text-gray-800">Access denied</h1>
      <p className="mt-2 text-sm text-gray-500">
        You don't have permission to view this page.
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
