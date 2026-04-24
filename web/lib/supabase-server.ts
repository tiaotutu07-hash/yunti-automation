import { createClient } from '@supabase/supabase-js'
import type { Database } from '@/types/database.types'

// 仅在 Node.js 运行时（API Route / Server Action）调用，不可导入到 'use client' 组件
export const createServiceClient = () =>
  createClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  )
