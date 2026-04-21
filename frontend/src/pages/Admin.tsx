import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

type EmbedStatus = { total: number; done: number; pending: number; failed: number }
type VectorCoverage = { total: number; both: number; description_only: number; neither: number; genome_eligible: number; review_embedded: number }
type HealthStatus = { status: string; models: { genome: string; description: string; review: string } }

function CoverageBar({ both, description_only, neither, total, genome_eligible, review_embedded }: VectorCoverage) {
  if (total === 0) return <p className="text-sm text-gray-400">No books yet.</p>
  const bothPct = (both / total) * 100
  const descPct = (description_only / total) * 100
  const neitherPct = (neither / total) * 100
  const genomeGap = genome_eligible - both
  const eligiblePct = genome_eligible > 0 ? Math.round((both / genome_eligible) * 100) : 0
  return (
    <div className="space-y-3">
      <div className="flex h-3 rounded-full overflow-hidden bg-gray-100">
        <div className="bg-emerald-500 transition-all" style={{ width: `${bothPct}%` }} title="Genome + description" />
        <div className="bg-indigo-400 transition-all" style={{ width: `${descPct}%` }} title="Description only" />
        <div className="bg-gray-300 transition-all" style={{ width: `${neitherPct}%` }} title="Neither" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="flex flex-col gap-0.5 p-3 rounded-lg bg-emerald-50 border border-emerald-100">
          <span className="text-xs text-emerald-600 font-medium">Genome + description</span>
          <span className="text-xl font-semibold text-emerald-700">{both.toLocaleString()}</span>
          <span className="text-xs text-emerald-500">{Math.round(bothPct)}% of {total.toLocaleString()} books</span>
        </div>
        <div className="flex flex-col gap-0.5 p-3 rounded-lg bg-amber-50 border border-amber-100">
          <span className="text-xs text-amber-600 font-medium">Genome-eligible (≥ 3 tropes)</span>
          <span className="text-xl font-semibold text-amber-700">{genome_eligible.toLocaleString()}</span>
          <span className="text-xs text-amber-500">
            {eligiblePct}% embedded · {genomeGap > 0 ? `${genomeGap.toLocaleString()} awaiting genome` : 'all embedded'}
          </span>
        </div>
        <div className="flex flex-col gap-0.5 p-3 rounded-lg bg-indigo-50 border border-indigo-100">
          <span className="text-xs text-indigo-600 font-medium">Description only</span>
          <span className="text-xl font-semibold text-indigo-700">{description_only.toLocaleString()}</span>
          <span className="text-xs text-indigo-500">{Math.round(descPct)}% of {total.toLocaleString()} books</span>
        </div>
        <div className="flex flex-col gap-0.5 p-3 rounded-lg bg-gray-50 border border-gray-200">
          <span className="text-xs text-gray-500 font-medium">Neither</span>
          <span className="text-xl font-semibold text-gray-600">{neither.toLocaleString()}</span>
          <span className="text-xs text-gray-400">{Math.round(neitherPct)}% of {total.toLocaleString()} books</span>
        </div>
        <div className="flex flex-col gap-0.5 p-3 rounded-lg bg-sky-50 border border-sky-100 col-span-2">
          <span className="text-xs text-sky-600 font-medium">Review-embedded</span>
          <span className="text-xl font-semibold text-sky-700">{review_embedded.toLocaleString()}</span>
          <span className="text-xs text-sky-500">
            {total > 0 ? Math.round((review_embedded / total) * 100) : 0}% of books · blended into recommendation scoring
          </span>
        </div>
      </div>
    </div>
  )
}

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
  useEffect(() => { document.title = 'Admin — CommonThread' }, [])
  const [polling, setPolling] = useState(false)
  const [running, setRunning] = useState(false)
  const [lastQueued, setLastQueued] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [coverage, setCoverage] = useState<VectorCoverage | null>(null)
  const [coverageLoading, setCoverageLoading] = useState(true)
  const [coverRunning, setCoverRunning] = useState(false)
  const [coversQueued, setCoversQueued] = useState<number | null>(null)
  const [coverError, setCoverError] = useState<string | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const prevPendingRef = useRef<number | null>(null)
  const stalePollsRef = useRef(0)
  const STALE_POLL_LIMIT = 5

  const stopPolling = () => {
    setPolling(false)
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    prevPendingRef.current = null
    stalePollsRef.current = 0
  }

  const loadCoverage = () => {
    if (!session) return
    setCoverageLoading(true)
    api.admin.vectorCoverage(session.access_token)
      .then(c => setCoverage(c))
      .catch(() => {/* non-critical, fail silently */})
      .finally(() => setCoverageLoading(false))
  }

  const loadStatus = () => {
    if (!session) return
    setStatusLoading(true)
    api.admin.embedStatus(session.access_token)
      .then(s => {
        setStatus(s)
        if (s.pending === 0) {
          stopPolling()
          loadCoverage()
        } else if (s.pending === prevPendingRef.current) {
          stalePollsRef.current += 1
          if (stalePollsRef.current >= STALE_POLL_LIMIT) {
            stopPolling()
            setError('Embedding job appears stalled — some books may still be pending. Check server logs.')
          }
        } else {
          stalePollsRef.current = 0
        }
        prevPendingRef.current = s.pending
      })
      .catch(e => setError(e.message))
      .finally(() => setStatusLoading(false))
  }

  useEffect(() => {
    loadStatus()
    loadCoverage()
    api.health.get().then(setHealth).catch(() => {})
  }, [session])

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const handleEmbedAll = async () => {
    if (!session) return
    setRunning(true)
    setError(null)
    setLastQueued(null)
    prevPendingRef.current = null
    stalePollsRef.current = 0
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
              ? status && status.pending > 0
                ? `No eligible books to queue — ${status.pending} book${status.pending !== 1 ? 's are' : ' is'} pending but haven't reached the tagging threshold yet.`
                : 'All books are already indexed.'
              : `Batch job started — ${lastQueued} book${lastQueued !== 1 ? 's' : ''} queued.`}
          </p>
        )}
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>

      {/* Vector coverage panel */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
        <h2 className="text-base font-semibold text-gray-800">Vector Coverage</h2>
        <p className="text-sm text-gray-500">
          Books with both embeddings appear in vibe search and similarity recommendations.
          Description-only books appear in hybrid search. Books with neither are not searchable by vector.
        </p>
        {coverageLoading ? (
          <div className="space-y-3 animate-pulse">
            <div className="h-3 bg-gray-200 rounded-full" />
            <div className="grid grid-cols-3 gap-2">
              <div className="h-16 bg-gray-100 rounded-lg" />
              <div className="h-16 bg-gray-100 rounded-lg" />
              <div className="h-16 bg-gray-100 rounded-lg" />
            </div>
          </div>
        ) : coverage ? (
          <CoverageBar {...coverage} />
        ) : null}
        <button
          onClick={loadCoverage}
          disabled={coverageLoading}
          className="px-3 py-2 text-sm text-gray-500 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 disabled:opacity-50"
        >
          Refresh
        </button>
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

      {/* Model status panel */}
      {health && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-gray-800">Embedding Models</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              Models must be loaded before embedding jobs can run.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {(['genome', 'description', 'review'] as const).map(m => {
              const state = health.models[m]
              const ready = state === 'ready'
              return (
                <div key={m} className={`p-3 rounded-lg border ${ready ? 'bg-emerald-50 border-emerald-100' : 'bg-amber-50 border-amber-200'}`}>
                  <p className="text-xs font-medium text-gray-600 capitalize">{m}</p>
                  <p className={`text-sm font-semibold mt-0.5 ${ready ? 'text-emerald-700' : 'text-amber-700'}`}>
                    {ready ? 'Ready' : 'Loading…'}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
