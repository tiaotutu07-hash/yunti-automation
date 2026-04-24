# check_db.py
# 用法: python scripts/check_db.py

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)

def check():
    # 总数
    total = supabase.table("problems").select("id", count="exact").execute()
    print(f"📊 题目总数: {total.count}")
    
    # 未打标
    untagged = supabase.table("problems") \
        .select("id", count="exact") \
        .is_("primary_tag", "null") \
        .execute()
    print(f"🏷  未打标:   {untagged.count}")
    
    # 待妻子审核
    unreviewed = supabase.table("problems") \
        .select("id", count="exact") \
        .eq("reviewed_by_wife", False) \
        .not_.is_("primary_tag", "null") \
        .execute()
    print(f"👀 待审核:   {unreviewed.count}")
    
    # 最近 5 条
    recent = supabase.table("problems") \
        .select("id, source, primary_tag, brief_analysis, created_at") \
        .order("created_at", desc=True) \
        .limit(5) \
        .execute()
    
    print(f"\n最近 5 条记录:")
    for r in recent.data:
        tag = r.get("primary_tag") or "未打标"
        brief = (r.get("brief_analysis") or "")[:25]
        print(f"  {r['id'][:8]}... [{r.get('source','')}] [{tag}] {brief}")

if __name__ == "__main__":
    check()