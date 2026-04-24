import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client


ROOT_DIR = Path(__file__).resolve().parents[1]
INBOX_DIR = ROOT_DIR / "data" / "inbox"
LOG_DIR = ROOT_DIR / "logs"
FAILED_LOG = LOG_DIR / "ingest_failed.jsonl"


def load_supabase():
    load_dotenv(ROOT_DIR / ".env")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")

    return create_client(url, key)


def write_failed(raw_line: str, error: str, file_path: str, line_no: int):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "time": datetime.now().isoformat(),
        "file": file_path,
        "line_no": line_no,
        "raw_line": raw_line,
        "error": error,
    }

    with FAILED_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def normalize_record(item: dict) -> dict:
    raw_latex = item.get("raw_latex")

    if not raw_latex or not isinstance(raw_latex, str):
        raise ValueError("Each record must contain raw_latex as a non-empty string")

    return {
        "raw_latex": raw_latex.strip(),
        "source": item.get("source", "手动录入"),
        "year": item.get("year"),
        "district": item.get("district", ""),
        "exam_type": item.get("exam_type", "练习"),
        "reviewed_by_wife": False,
        "reviewed_by_chief": False,
    }


def ingest_file(supabase, file_path: Path):
    success = 0
    failed = 0

    print(f"\nReading: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw_line = line.strip()

            if not raw_line:
                continue

            try:
                item = json.loads(raw_line)
                record = normalize_record(item)

                result = supabase.table("problems").insert(record).execute()

                if result.data:
                    inserted_id = result.data[0]["id"]
                    print(f"  OK line {line_no}: {inserted_id}")
                    success += 1
                else:
                    raise RuntimeError(f"Insert returned no data: {result}")

            except Exception as e:
                print(f"  FAIL line {line_no}: {e}")
                write_failed(raw_line, str(e), str(file_path), line_no)
                failed += 1

    return success, failed


def find_input_files(file_arg: Optional[str]):
    if file_arg:
        file_path = Path(file_arg)
        if not file_path.is_absolute():
            file_path = ROOT_DIR / file_path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return [file_path]

    files = sorted(INBOX_DIR.glob("*.jsonl"))

    if not files:
        raise FileNotFoundError(f"No .jsonl files found in {INBOX_DIR}")

    return files


def main():
    parser = argparse.ArgumentParser(description="Manual JSONL ingest into Supabase problems table")
    parser.add_argument("--file", help="Path to a specific .jsonl file")
    args = parser.parse_args()

    supabase = load_supabase()
    files = find_input_files(args.file)

    total_success = 0
    total_failed = 0

    for file_path in files:
        success, failed = ingest_file(supabase, file_path)
        total_success += success
        total_failed += failed

    print("\nDone.")
    print(f"Success: {total_success}")
    print(f"Failed: {total_failed}")

    if total_failed:
        print(f"Failed records saved to: {FAILED_LOG}")


if __name__ == "__main__":
    main()