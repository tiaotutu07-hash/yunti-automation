-- ============================================================
-- yunti-automation  Supabase Schema  Phase 1
-- ============================================================
-- 部署：在 Supabase SQL Editor 中一次性执行本文件。
-- 所有表均已启用 RLS；具体 policy 见文末注释块。
-- ============================================================

create extension if not exists "pgcrypto";  -- gen_random_uuid()

-- ============================================================
-- 1. problems — 题目主表
-- ============================================================
create table if not exists problems (
  id                  uuid        primary key default gen_random_uuid(),

  -- 原始题目
  raw_latex           text        not null,
  source              text        not null default '手动录入',
  year                integer,
  district            text        not null default '',
  exam_type           text        not null default '练习',

  -- AI 打标结果（auto_tag.py 回写）
  primary_tag         text,
  method_tags         text[]      not null default '{}',
  difficulty          integer     check (difficulty between 1 and 5),
  novelty             text,
  typical_errors      text[]      not null default '{}',
  brief_analysis      text,
  -- 记录 provider/model，例如 deepseek/deepseek-v4-flash
  tagged_by           text,
  tagged_at           timestamptz,

  -- 审核流
  reviewed_by_wife    boolean     not null default false,
  reviewed_by_chief   boolean     not null default false,
  wife_notes          text,

  created_at          timestamptz not null default now()
);

comment on column problems.tagged_by
  is '记录打标的 provider/model，例如 deepseek/deepseek-v4-flash';
comment on column problems.method_tags
  is 'AI 打标的解题方法列表，与 method_cards.name 保持一致';
comment on column problems.reviewed_by_wife
  is '妻子审核通过为 true；驳回时置 false 并清空所有 AI 字段';
comment on column problems.reviewed_by_chief
  is '主管二审标志（第二阶段启用）';
comment on column problems.wife_notes
  is '妻子审核备注：通过时的修改说明，或驳回原因';

create index if not exists idx_problems_primary_tag       on problems (primary_tag);
create index if not exists idx_problems_reviewed_by_wife  on problems (reviewed_by_wife);
create index if not exists idx_problems_created_at        on problems (created_at desc);

-- ============================================================
-- 2. method_cards — 解题方法卡片
-- ============================================================
-- name 与 problems.method_tags 中的字符串保持一致，
-- 前端可通过 method_tags[] 关联查询对应卡片。
-- ============================================================
create table if not exists method_cards (
  id                   uuid        primary key default gen_random_uuid(),

  name                 text        not null unique,  -- 例如：虚设零点、ALM、构造辅助函数
  description          text        not null default '',
  example_latex        text,                         -- 可选示范题 LaTeX
  related_primary_tags text[]      not null default '{}',

  created_at           timestamptz not null default now()
);

comment on table  method_cards
  is '解题方法卡片库；name 与 problems.method_tags 中的值一一对应';
comment on column method_cards.related_primary_tags
  is '该方法常见于哪些 primary_tag，例如：{极值最值, 不等式证明}';

create index if not exists idx_method_cards_name on method_cards (name);

-- ============================================================
-- 3. formula_cards — 公式卡片
-- ============================================================
create table if not exists formula_cards (
  id          uuid        primary key default gen_random_uuid(),

  title       text        not null,   -- 公式名称，例如：导数四则运算法则
  category    text        not null,   -- 所属模块，例如：导数、极值最值、不等式
  body_latex  text        not null,   -- 公式正文（LaTeX），前端用 KaTeX 渲染
  note        text,                   -- 纯文本补充说明

  created_at  timestamptz not null default now()
);

comment on column formula_cards.body_latex
  is '公式 LaTeX 正文，前端使用 KaTeX 渲染';
comment on column formula_cards.category
  is '所属模块，例如：导数、极值最值、不等式证明';

create index if not exists idx_formula_cards_category on formula_cards (category);

-- ============================================================
-- RLS
-- ============================================================
alter table problems      enable row level security;
alter table method_cards  enable row level security;
alter table formula_cards enable row level security;

-- 以下 policy 按需在 Supabase SQL Editor 执行：
--
-- -- 匿名读取（三张表）
-- create policy "anon read problems"
--   on problems for select using (true);
-- create policy "anon read method_cards"
--   on method_cards for select using (true);
-- create policy "anon read formula_cards"
--   on formula_cards for select using (true);
--
-- -- 匿名更新 problems（审核页写回）
-- create policy "anon update problems"
--   on problems for update using (true) with check (true);
