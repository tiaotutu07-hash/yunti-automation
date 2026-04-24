'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'
import ProblemCard from '@/components/ProblemCard'
import type { Problem } from '@/types/database.types'

export default function ReviewPage() {
  const [problems, setProblems] = useState<Problem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    createClient()
      .from('problems')
      .select('*')
      .eq('reviewed_by_wife', false)
      .not('primary_tag', 'is', null)
      .order('created_at', { ascending: true })
      .limit(30)
      .then(({ data, error }) => {
        if (error) setError(error.message)
        else setProblems(data ?? [])
        setLoading(false)
      })
  }, [])

  function handleApproved(id: string) {
    setProblems(prev => prev.filter(p => p.id !== id))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-gray-400">
        加载中…
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-2 text-red-500">
        <p className="font-medium">加载失败</p>
        <p className="text-sm text-gray-500">{error}</p>
      </div>
    )
  }

  return (
    <main className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-baseline gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">题目审核</h1>
        <span className="text-sm text-gray-400">待审核 {problems.length} 道</span>
      </div>
      {problems.length === 0 ? (
        <div className="text-center text-gray-400 py-24 text-lg">
          🎉 全部审核完毕
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {problems.map(p => (
            <ProblemCard key={p.id} problem={p} onApproved={handleApproved} />
          ))}
        </div>
      )}
    </main>
  )
}
