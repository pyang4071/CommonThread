import { useState } from 'react'
import { ConfirmModal } from './ConfirmModal'

type Column<T> = {
  header: string
  accessor: (row: T) => React.ReactNode
}

type Props<T> = {
  columns: Column<T>[]
  data: T[]
  onDelete?: (row: T) => void
  deleteLabel?: (row: T) => string  // used in the confirmation message
}

export function Table<T>({ columns, data, onDelete, deleteLabel }: Props<T>) {
  const [pending, setPending] = useState<T | null>(null)

  const handleDeleteClick = (row: T) => setPending(row)

  const handleConfirm = () => {
    if (pending) onDelete?.(pending)
    setPending(null)
  }

  return (
    <>
      {pending && (
        <ConfirmModal
          title="Confirm deletion"
          message={
            deleteLabel
              ? `Are you sure you want to delete "${deleteLabel(pending)}"? This cannot be undone.`
              : 'Are you sure you want to delete this item? This cannot be undone.'
          }
          onConfirm={handleConfirm}
          onCancel={() => setPending(null)}
        />
      )}

      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.header}
                  className="px-4 py-3 text-left font-medium text-gray-600 uppercase tracking-wider"
                >
                  {col.header}
                </th>
              ))}
              {onDelete && <th className="px-4 py-3" />}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + (onDelete ? 1 : 0)}
                  className="px-4 py-8 text-center text-gray-400"
                >
                  No records yet
                </td>
              </tr>
            ) : (
              data.map((row, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  {columns.map((col) => (
                    <td key={col.header} className="px-4 py-3 text-gray-700">
                      {col.accessor(row) ?? <span className="text-gray-300">—</span>}
                    </td>
                  ))}
                  {onDelete && (
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDeleteClick(row)}
                        className="text-red-500 hover:text-red-700 text-xs font-medium"
                      >
                        Delete
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}
