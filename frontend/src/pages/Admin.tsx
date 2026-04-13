import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

type EmbedStatus = { total: number; done: number; pending: number; failed: number }

function StatusBar({ done, pending, failed, total }: EmbedStatus) {
  if (total === 0) return <p className="text-sm text-gray-400">No books yet.</p>
  const donePct = Math.round((done / total) * 100)
  const pendingPct = Math.round((pending / total) * 100)
  const failedPct = Math.round((failed / total) * 100)
  return (
    <div className="space-y-2">
      <div className="flex h-3 rounded-full overflow-hidden bg-gray-100">
        <div className="bg-emerald-500 transition-all" style={{ width: `${donePct}%` }} />
        <div className="bg-yellow-400 transition-all" style={{ width: `${pendingPct}%` }} />
        <div className="bg-red-400 transition-all" style={{ width: `${failedPct}%` }} />
      </div>
      <div className="flex gap-4 text-xs text-gray-500">
        <span><span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1" />Done {done}</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-yellow-400 mr-1" />Pending {pending}</span>
        <span><span className="inline-block w-2 h-2 rounded-full bg-red-400 mr-1" />Failed {failed}</span>
        <span className="ml-auto">{total} total</span>
      </div>
    </div>
  )
}

export function Admin() {
  const { session } = useAuth()
  const [status, setStatus] = useState<EmbedStatus | null>(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [polling, setPolling] = useState(false)
  const [running, setRunning] = useState(false)
  const [lastQueued, setLastQueued] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [coverRunning, setCoverRunning] = useState(false)
  const [coversQueued, setCoversQueued] = useState<number | null>(null)
  const [coverError, setCoverError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadStatus = () => {
    if (!session) return
    setStatusLoading(true)
    api.admin.embedStatus(session.access_token)
      .then(s => {
        setStatus(s)
        // Stop polling once nothing is pending
        if (s.pending === 0) {
          setPolling(false)
          if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setStatusLoading(false))
  }

  useEffect(() => { loadStatus() }, [session])

  // Clear interval on unmount
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const handleEmbedAll = async () => {
    if (!session) return
    setRunning(true)
    setError(null)
    setLastQueued(null)
    try {
      const result = await api.admin.embedAll(session.access_token)
      setLastQueued(result.queued)
      // Start polling every 4s to watch live progress
      setTimeout(loadStatus, 800)
      if (result.queued > 0 && !pollRef.current) {
        setPolling(true)
        pollRef.current = setInterval(loadStatus, 4000)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start embedding job.')
    } finally {
      setRunning(false)
    }
  }

  const handleFetchCovers = async () => {
    if (!session) return
    setCoverRunning(true)
    setCoverError(null)
    setCoversQueued(null)
    try {
      const result = await api.admin.fetchCovers(session.access_token)
      setCoversQueued(result.queued)
    } catch (e: unknown) {
      setCoverError(e instanceof Error ? e.message : 'Failed to start cover fetch.')
    } finally {
      setCoverRunning(false)
    }
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <h1 className="text-2xl font-semibold text-gray-800">Admin</h1>

      {/* Embedding panel */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-gray-800">Embedding Index</h2>
          {polling && (
            <span className="text-xs text-indigo-500 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded-full animate-pulse">
              Refreshing…
            </span>
          )}
        </div>
        <div>
          <p className="text-sm text-gray-500 mt-0.5">
            Each book needs to be embedded before it appears in vibe search and
            similarity recommendations. Books are embedded automatically when
            added or edited; use the button below to re-queue any that are
            pending or failed.
          </p>
        </div>

        {statusLoading ? (
          <div className="space-y-2 animate-pulse">
            <div className="h-3 bg-gray-200 rounded-full" />
            <div className="h-3 w-1/2 bg-gray-200 rounded" />
          </div>
        ) : status ? (
          <StatusBar {...status} />
        ) : null}

        <div className="flex items-center gap-3">
          <button
            onClick={handleEmbedAll}
            disabled={running}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {running ? 'Starting…' : 'Embed pending & failed books'}
          </button>
          <button
            onClick={loadStatus}
            disabled={statusLoading}
            className="px-3 py-2 text-sm text-gray-500 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Refresh
          </button>
        </div>

        {lastQueued !== null && (
          <p className="text-sm text-emerald-600">
            {lastQueued === 0
              ? 'All books are already indexed.'
              : `Batch job started — ${lastQueued} book${lastQueued !== 1 ? 's' : ''} queued.`}
          </p>
        )}
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>

      {/* Cover images panel */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-800">Cover Images</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Fetch missing cover images for books that don't have one yet. Covers are
            pulled automatically when a book is added; use this to backfill any gaps.
          </p>
        </div>

        <button
          onClick={handleFetchCovers}
          disabled={coverRunning}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {coverRunning ? 'Starting…' : 'Fetch missing covers'}
        </button>

        {coversQueued !== null && (
          <p className="text-sm text-emerald-600">
            {coversQueued === 0
              ? 'All books already have covers.'
              : `Cover fetch started — ${coversQueued} book${coversQueued !== 1 ? 's' : ''} queued.`}
          </p>
        )}
        {coverError && <p className="text-sm text-red-500">{coverError}</p>}
      </div>
    </div>
  )
}
