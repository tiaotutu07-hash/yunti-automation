import { NextRequest, NextResponse } from 'next/server'
import { createServiceClient } from '@/lib/supabase-server'

type Action = 'approve' | 'edit_and_approve' | 'reject'

interface RequestBody {
  action: Action
  id: string
  // edit_and_approve
  primary_tag?: string
  brief_analysis?: string
  wife_notes?: string
  // reject
  reject_notes?: string
}

function checkEnv(): NextResponse | null {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
    console.error('[review API] missing env: NEXT_PUBLIC_SUPABASE_URL')
    return NextResponse.json({ error: 'missing SUPABASE_URL' }, { status: 500 })
  }
  if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
    console.error('[review API] missing env: SUPABASE_SERVICE_ROLE_KEY')
    return NextResponse.json({ error: 'missing SUPABASE_SERVICE_ROLE_KEY' }, { status: 500 })
  }
  return null
}

export async function POST(req: NextRequest) {
  const envError = checkEnv()
  if (envError) return envError

  let body: RequestBody
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'invalid request body' }, { status: 400 })
  }

  const { action, id } = body

  if (!id || typeof id !== 'string') {
    return NextResponse.json({ error: 'invalid request body: missing id' }, { status: 400 })
  }
  if (!action || !['approve', 'edit_and_approve', 'reject'].includes(action)) {
    return NextResponse.json({ error: `invalid request body: unknown action "${action}"` }, { status: 400 })
  }

  const supabase = createServiceClient()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let patch: Record<string, any>

  if (action === 'approve') {
    patch = { reviewed_by_wife: true }

  } else if (action === 'edit_and_approve') {
    patch = { reviewed_by_wife: true }
    if (body.primary_tag?.trim())     patch.primary_tag    = body.primary_tag.trim()
    if (body.brief_analysis?.trim())  patch.brief_analysis = body.brief_analysis.trim()
    if (body.wife_notes?.trim())      patch.wife_notes     = body.wife_notes.trim()

  } else {
    patch = {
      reviewed_by_wife: false,
      primary_tag:      null,
      method_tags:      null,
      difficulty:       null,
      novelty:          null,
      typical_errors:   null,
      brief_analysis:   null,
      tagged_by:        null,
      tagged_at:        null,
    }
    if (body.reject_notes?.trim()) patch.wife_notes = body.reject_notes.trim()
  }

  const { error } = await supabase
    .from('problems')
    .update(patch)
    .eq('id', id)

  if (error) {
    console.error('[review API] supabase update failed:', error.message)
    return NextResponse.json({ error: 'supabase update failed: ' + error.message }, { status: 500 })
  }

  return NextResponse.json({ ok: true })
}
