'use client'

import { useState } from 'react'
import katex from 'katex'
import type { Problem } from '@/types/database.types'

const DIFFICULTY: Record<number, string> = {
  1: '基础',
  2: '中等',
  3: '综合',
  4: '压轴前问',
  5: '压轴',
}

type Mode = 'idle' | 'editing' | 'rejecting'

function renderLatex(raw: string): string {
  try {
    return katex.renderToString(raw, {
      throwOnError: false,
      displayMode: true,
      strict: false,
    })
  } catch {
    return `<pre class="whitespace-pre-wrap text-xs text-gray-700">${raw}</pre>`
  }
}

interface Props {
  problem: Problem
  onApproved: (id: string) => void
}

export default function ProblemCard({ problem, onApproved }: Props) {
  const [mode, setMode] = useState<Mode>('idle')
  const [busy, setBusy] = useState(false)

  // 修改通过表单
  const [editTag, setEditTag]           = useState(problem.primary_tag ?? '')
  const [editAnalysis, setEditAnalysis] = useState(problem.brief_analysis ?? '')
  const [editNotes, setEditNotes]       = useState('')

  // 驳回表单
  const [rejectNotes, setRejectNotes] = useState('')

  async function callApi(body: Record<string, unknown>) {
    const res = await fetch('/api/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.error ?? `HTTP ${res.status}`)
    }
  }

  // ── 直接通过 ──────────────────────────────────────────────────────────────
  async function approve() {
    setBusy(true)
    try {
      await callApi({ action: 'approve', id: problem.id })
      onApproved(problem.id)
    } catch (e) {
      alert('操作失败：' + (e as Error).message)
      setBusy(false)
    }
  }

  // ── 修改后通过 ────────────────────────────────────────────────────────────
  async function saveEdit() {
    setBusy(true)
    try {
      await callApi({
        action:        'edit_and_approve',
        id:            problem.id,
        primary_tag:   editTag,
        brief_analysis: editAnalysis,
        wife_notes:    editNotes,
      })
      onApproved(problem.id)
    } catch (e) {
      alert('操作失败：' + (e as Error).message)
      setBusy(false)
    }
  }

  // ── 驳回 ──────────────────────────────────────────────────────────────────
  async function confirmReject() {
    setBusy(true)
    try {
      await callApi({ action: 'reject', id: problem.id, reject_notes: rejectNotes })
      onApproved(problem.id)
    } catch (e) {
      alert('操作失败：' + (e as Error).message)
      setBusy(false)
    }
  }

  // ── 渲染 ──────────────────────────────────────────────────────────────────
  return (
    <article className="bg-white border border-gray-200 rounded-xl shadow-sm p-5">

      {/* Meta */}
      <div className="flex flex-wrap gap-1.5 text-xs text-gray-500 mb-3">
        {problem.source && (
          <span className="bg-gray-100 px-2 py-0.5 rounded">{problem.source}</span>
        )}
        {problem.year     && <span>{problem.year}</span>}
        {problem.district && <span>{problem.district}</span>}
        {problem.exam_type && <span>{problem.exam_type}</span>}
        <span className="font-mono text-gray-300 ml-auto">{problem.id.slice(0, 8)}</span>
      </div>

      {/* LaTeX */}
      <div
        className="overflow-x-auto mb-4 text-sm leading-relaxed"
        dangerouslySetInnerHTML={{ __html: renderLatex(problem.raw_latex) }}
      />

      {/* Tags */}
      <div className="flex flex-wrap gap-2 mb-3">
        {problem.primary_tag && (
          <span className="bg-blue-100 text-blue-700 text-xs px-2.5 py-0.5 rounded-full font-medium">
            {problem.primary_tag}
          </span>
        )}
        {(problem.method_tags ?? []).map(t => (
          <span key={t} className="bg-purple-50 text-purple-600 text-xs px-2.5 py-0.5 rounded-full">
            {t}
          </span>
        ))}
        {problem.difficulty != null && (
          <span className="bg-amber-50 text-amber-700 text-xs px-2.5 py-0.5 rounded-full">
            {DIFFICULTY[problem.difficulty] ?? `难度 ${problem.difficulty}`}
          </span>
        )}
        {problem.novelty && (
          <span className="bg-green-50 text-green-600 text-xs px-2.5 py-0.5 rounded-full">
            {problem.novelty}
          </span>
        )}
      </div>

      {/* Analysis */}
      {problem.brief_analysis && (
        <p className="text-xs text-gray-500 italic border-l-2 border-gray-200 pl-3 mb-3">
          {problem.brief_analysis}
        </p>
      )}

      {/* Typical errors */}
      {(problem.typical_errors ?? []).length > 0 && (
        <details className="mb-3 text-xs">
          <summary className="cursor-pointer text-gray-500 select-none">
            常见错误（{(problem.typical_errors ?? []).length}）
          </summary>
          <ul className="mt-1.5 list-disc list-inside space-y-0.5 text-red-500 pl-1">
            {(problem.typical_errors ?? []).map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </details>
      )}

      {/* ── 修改通过表单 ── */}
      {mode === 'editing' && (
        <div className="mt-4 pt-4 border-t border-gray-100 flex flex-col gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">分类标签</label>
            <input
              value={editTag}
              onChange={e => setEditTag(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">简析</label>
            <textarea
              value={editAnalysis}
              onChange={e => setEditAnalysis(e.target.value)}
              rows={2}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">审核备注</label>
            <textarea
              value={editNotes}
              onChange={e => setEditNotes(e.target.value)}
              rows={2}
              placeholder="可选"
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setMode('idle')}
              className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              取消
            </button>
            <button
              onClick={saveEdit}
              disabled={busy}
              className="px-4 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {busy ? '保存中…' : '保存并通过'}
            </button>
          </div>
        </div>
      )}

      {/* ── 驳回表单 ── */}
      {mode === 'rejecting' && (
        <div className="mt-4 pt-4 border-t border-gray-100 flex flex-col gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">驳回原因（可选）</label>
            <textarea
              value={rejectNotes}
              onChange={e => setRejectNotes(e.target.value)}
              rows={2}
              placeholder="说明问题所在，方便重新打标时参考"
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 resize-none focus:outline-none focus:ring-2 focus:ring-red-200"
              autoFocus
            />
          </div>
          <p className="text-xs text-gray-400">
            驳回后将清除所有 AI 打标字段，题目回到未打标队列。
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setMode('idle')}
              className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              取消
            </button>
            <button
              onClick={confirmReject}
              disabled={busy}
              className="px-4 py-1.5 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {busy ? '处理中…' : '确认驳回'}
            </button>
          </div>
        </div>
      )}

      {/* ── 底部操作栏（仅 idle 状态显示）── */}
      {mode === 'idle' && (
        <div className="flex items-center justify-between pt-3 border-t border-gray-100 mt-3">
          <span className="text-xs text-gray-400">{problem.tagged_by}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setMode('rejecting')}
              className="px-3 py-1.5 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
            >
              ✗ 驳回
            </button>
            <button
              onClick={() => setMode('editing')}
              className="px-3 py-1.5 text-sm font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors"
            >
              ✎ 修改通过
            </button>
            <button
              onClick={approve}
              disabled={busy}
              className="px-4 py-1.5 text-sm font-medium bg-green-600 hover:bg-green-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {busy ? '处理中…' : '✓ 通过'}
            </button>
          </div>
        </div>
      )}
    </article>
  )
}
