import { createClient } from '@supabase/supabase-js'

// 仅在 Node.js 运行时（API Route / Server Action）调用，不可导入到 'use client' 组件
// 不传 Database 泛型：手写类型缺少 SDK 要求的 Views/Functions/Enums 字段，会导致
// .update() 参数被推断为 never；服务端写操作由上层代码保证字段正确性。
export const createServiceClient = () =>
  createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  )
