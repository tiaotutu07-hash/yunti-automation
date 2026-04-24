# auto_tag.py — 云梯学社多模型打标脚本
#
# 用法示例：
#   python scripts/auto_tag.py --provider deepseek --model deepseek-v4-flash --limit 20
#   python scripts/auto_tag.py --provider deepseek --model deepseek-v4-pro   --limit 10
#   python scripts/auto_tag.py --provider anthropic --model claude-sonnet-4-6 --limit 20
#   python scripts/auto_tag.py --provider anthropic --model claude-opus-4-6   --limit 5
#
# .env 需包含：
#   SUPABASE_URL
#   SUPABASE_SERVICE_ROLE_KEY
#   DEEPSEEK_API_KEY      （使用 deepseek provider 时必填）
#   ANTHROPIC_API_KEY     （使用 anthropic provider 时必填）

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ── 依赖检查 ─────────────────────────────────────────────────────────────────
try:
    from supabase import create_client, Client
except ImportError:
    sys.exit("❌ 缺少依赖：pip install supabase")

try:
    import requests
except ImportError:
    sys.exit("❌ 缺少依赖：pip install requests")

# anthropic SDK 是可选的（仅 anthropic provider 需要）
try:
    import anthropic as anthropic_sdk
    _HAS_ANTHROPIC_SDK = True
except ImportError:
    _HAS_ANTHROPIC_SDK = False

# ── 常量 ─────────────────────────────────────────────────────────────────────
VALID_PROVIDERS = {"deepseek", "anthropic"}

VALID_MODELS = {
    "deepseek":  {"deepseek-v4-pro", "deepseek-v4-flash"},
    "anthropic": {"claude-sonnet-4-6", "claude-opus-4-6"},
}

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"

LOGS_DIR = Path("logs")
FAILED_LOG = LOGS_DIR / "failed_tags.jsonl"

# ── 日志配置 ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("auto_tag")

# ── 打标 System Prompt ────────────────────────────────────────────────────────
SYSTEM_PROMPT = """你是云梯学社高中数学教研数据分析师。
对高考数学题目进行精准打标，输出结构化 JSON。

primary_tag 枚举（导数专题）：
  零点存在性 | 极值最值 | 切线方程 | 恒成立 | 参数讨论 | 综合大题 | 不等式证明 | 面积计算

method_tags 标准候选（选 1-4 个）：
  虚设零点 | 换元 | ALM | 构造辅助函数 | 端点法 | 对勾函数 |
  单调性分析 | 二阶导判断极值 | 参数分离 | 数形结合 | 导数定义 |
  拉格朗日乘数思想 | 切线斜率法 | 泰勒展开估算 | 积分面积 |
  反函数思想 | 齐次化 | 绝对值拆分 | 凸函数 Jensen | 递推构造

difficulty 评分标准：
  1 = 基础计算，直接套公式
  2 = 需要分类讨论，但思路清晰
  3 = 需要构造辅助量，有一定综合性
  4 = 高考压轴前问，有技巧性
  5 = 压轴最后一问，需要非常规构造

brief_analysis 风格：极客冷峻，点破本质，不超过 50 字。
  示例："导数符号判断极值后，参数方程转化为线性不等式，ALM 直击核心，避免讨论无穷多情况。"
  示例："零点存在性的本质是连续函数介值定理，关键在于虚设零点后消去超越结构。"

只输出 JSON，不要任何其他文字、标点或 markdown 代码块：
{
  "primary_tag": "...",
  "method_tags": ["...", "..."],
  "difficulty": 4,
  "novelty": "常规",
  "typical_errors": ["...", "..."],
  "brief_analysis": "..."
}"""


# ── Provider 封装 ─────────────────────────────────────────────────────────────

class DeepSeekProvider:
    """调用 DeepSeek API（OpenAI 兼容格式）"""

    def __init__(self, model: str):
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            sys.exit("❌ .env 中缺少 DEEPSEEK_API_KEY")
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def call(self, latex_content: str) -> tuple[str, str]:
        """
        返回 (parsed_json_str, raw_response_str)
        解析失败时抛出异常，调用方负责重试/日志
        """
        payload = {
            "model": self.model,
            "max_tokens": 600,
            "temperature": 0.2,        # 打标任务低温，减少随机性
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"请打标以下题目：\n\n{latex_content}"},
            ],
        }
        resp = requests.post(
            DEEPSEEK_BASE_URL,
            headers=self.headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"].strip()
        return _parse_json(raw), raw


class AnthropicProvider:
    """调用 Anthropic Claude API"""

    def __init__(self, model: str):
        if not _HAS_ANTHROPIC_SDK:
            sys.exit("❌ 缺少依赖：pip install anthropic")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            sys.exit("❌ .env 中缺少 ANTHROPIC_API_KEY")
        self.model = model
        self.client = anthropic_sdk.Anthropic(api_key=api_key)

    def call(self, latex_content: str) -> tuple[str, str]:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"请打标以下题目：\n\n{latex_content}"}
            ],
        )
        raw = message.content[0].text.strip()
        return _parse_json(raw), raw


def build_provider(provider: str, model: str):
    if provider == "deepseek":
        return DeepSeekProvider(model)
    elif provider == "anthropic":
        return AnthropicProvider(model)
    else:
        sys.exit(f"❌ 未知 provider: {provider}")


# ── JSON 解析（容错）─────────────────────────────────────────────────────────

def _parse_json(raw: str) -> str:
    """
    清理 raw，确保能 json.loads()，返回干净的 JSON 字符串。
    失败直接抛 json.JSONDecodeError。
    """
    text = raw.strip()

    # 去掉 ```json ... ``` 或 ``` ... ```
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # 找到第一个 { 到最后一个 }
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("no JSON object found", text, 0)

    candidate = text[start:end + 1]
    json.loads(candidate)   # 验证，失败会抛异常
    return candidate


# ── 失败日志 ──────────────────────────────────────────────────────────────────

def _log_failure(problem_id: str, latex: str, raw_response: str, error: str, provider: str, model: str):
    LOGS_DIR.mkdir(exist_ok=True)
    entry = {
        "ts":          datetime.now(timezone.utc).isoformat(),
        "provider":    provider,
        "model":       model,
        "problem_id":  problem_id,
        "latex_head":  latex[:200],   # 只记前 200 字符，避免日志过大
        "raw_response": raw_response,
        "error":       error,
    }
    with open(FAILED_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── 单题打标（含重试）────────────────────────────────────────────────────────

def tag_with_retry(
    provider_obj,
    problem_id: str,
    latex: str,
    provider_name: str,
    model_name: str,
    max_retries: int = 2,
) :
    """
    调用 provider，最多重试 max_retries 次。
    全部失败返回 None，并写 failed_tags.jsonl。
    """
    last_raw = ""
    last_err = ""

    for attempt in range(1, max_retries + 2):   # 1 次正常 + 2 次重试
        try:
            json_str, raw = provider_obj.call(latex)
            result = json.loads(json_str)

            # 基本字段校验
            required = {"primary_tag", "method_tags", "difficulty", "novelty",
                        "typical_errors", "brief_analysis"}
            missing = required - result.keys()
            if missing:
                raise ValueError(f"返回 JSON 缺少字段: {missing}")

            return result

        except json.JSONDecodeError as e:
            last_err = f"JSONDecodeError: {e}"
            last_raw = raw if "raw" in dir() else ""  # noqa
        except ValueError as e:
            last_err = str(e)
            last_raw = raw if "raw" in dir() else ""  # noqa
        except requests.HTTPError as e:
            last_err = f"HTTPError {e.response.status_code}: {e.response.text[:200]}"
            last_raw = ""
        except Exception as e:
            last_err = str(e)
            last_raw = ""

        if attempt <= max_retries:
            wait = attempt * 2
            log.warning(f"    ⚠️  第 {attempt} 次失败，{wait}s 后重试 | {last_err[:60]}")
            time.sleep(wait)

    # 全部重试耗尽
    _log_failure(problem_id, latex, last_raw, last_err, provider_name, model_name)
    return None


# ── 主流程 ────────────────────────────────────────────────────────────────────

def run_batch(provider_name: str, model_name: str, limit: int, batch_size: int, retries: int):
    # 初始化 Supabase
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url or not supabase_key:
        sys.exit("❌ .env 中缺少 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)

    # 初始化 Provider
    provider_obj = build_provider(provider_name, model_name)

    # 查未打标题目
    result = (
        supabase.table("problems")
        .select("id, raw_latex")
        .is_("primary_tag", "null")
        .limit(limit)
        .execute()
    )
    problems = result.data

    if not problems:
        log.info("✅ 没有待打标题目")
        return

    log.info(f"📋 待打标: {len(problems)} 道 | provider={provider_name} | model={model_name}")

    success, failed, skipped = 0, 0, 0

    for i, prob in enumerate(problems, 1):
        pid   = prob["id"]
        latex = (prob.get("raw_latex") or "").strip()

        prefix = f"[{i:>3}/{len(problems)}] {pid[:8]}..."

        if len(latex) < 5:
            log.info(f"  {prefix} ⚠️  内容过短，跳过")
            skipped += 1
            continue

        log.info(f"  {prefix} 打标中...", )

        tags = tag_with_retry(
            provider_obj,
            pid,
            latex,
            provider_name,
            model_name,
            max_retries=retries,
        )

        if tags is None:
            log.error(f"  {prefix} ❌ 全部重试失败，已记录到 {FAILED_LOG}")
            failed += 1
        else:
            update_data = {
                "primary_tag":    tags.get("primary_tag"),
                "method_tags":    tags.get("method_tags", []),
                "difficulty":     tags.get("difficulty"),
                "novelty":        tags.get("novelty"),
                "typical_errors": tags.get("typical_errors", []),
                "brief_analysis": tags.get("brief_analysis"),
                "tagged_by":      f"{provider_name}/{model_name}",
                "tagged_at":      datetime.now(timezone.utc).isoformat(),
            }
            # 过滤 None
            update_data = {k: v for k, v in update_data.items() if v is not None}

            supabase.table("problems").update(update_data).eq("id", pid).execute()

            brief = (tags.get("brief_analysis") or "")[:35]
            log.info(f"  {prefix} ✅ [{tags.get('primary_tag')}] {brief}")
            success += 1

        # 限速保护：每 batch_size 题暂停
        if i % batch_size == 0 and i < len(problems):
            log.info(f"  ⏸  已处理 {i} 道，休息 2s...")
            time.sleep(2)
        else:
            time.sleep(0.3)

    # 汇总
    print()
    print(f"{'─'*50}")
    print(f"🏁 完成  成功:{success}  失败:{failed}  跳过:{skipped}")
    if failed:
        print(f"   失败记录见 → {FAILED_LOG.resolve()}")
    print(f"{'─'*50}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="云梯学社多模型打标脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python scripts/auto_tag.py --provider deepseek  --model deepseek-v4-flash --limit 20
  python scripts/auto_tag.py --provider deepseek  --model deepseek-v4-pro   --limit 10
  python scripts/auto_tag.py --provider anthropic --model claude-sonnet-4-6 --limit 20
  python scripts/auto_tag.py --provider anthropic --model claude-opus-4-6   --limit 5
        """,
    )
    parser.add_argument(
        "--provider",
        required=True,
        choices=list(VALID_PROVIDERS),
        help="AI 服务商: deepseek / anthropic",
    )
    parser.add_argument(
        "--model",
        required=True,
        help=(
            "模型名。deepseek: deepseek-v4-pro / deepseek-v4-flash；"
            "anthropic: claude-sonnet-4-6 / claude-opus-4-6"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="本次处理题目上限（默认 20）",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=5,
        help="每批题目数，触发限速保护（默认 5）",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="单题最大重试次数（默认 2）",
    )
    return parser.parse_args()


def validate_args(args):
    allowed = VALID_MODELS.get(args.provider, set())
    if args.model not in allowed:
        print(f"❌ provider={args.provider} 不支持 model={args.model}")
        print(f"   可用模型: {', '.join(sorted(allowed))}")
        sys.exit(1)


if __name__ == "__main__":
    args = parse_args()
    validate_args(args)
    run_batch(args.provider, args.model, args.limit, args.batch_size, args.retries)