#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""存储错误记录到向量数据库。

用法:
    python store.py --symptom "..." --root-cause "..." --fix "..." --type compile --module godot [--tags "a,b,c"]
    python store.py --from-ci-report report.json   # 从 CI 报告批量导入
"""

import json
import hashlib
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = Path(__file__).resolve().parent / "chroma_db"
ERRORS_FILE = Path(__file__).resolve().parent / "errors.json"

# 北京时间
TZ = timezone(timedelta(hours=8))


def get_collection():
    """获取 ChromaDB collection。"""
    import chromadb
    from rebuild import get_embedding_fn

    client = chromadb.PersistentClient(path=str(DB_DIR))
    ef = get_embedding_fn()
    return client.get_or_create_collection(
        name="project_errors",
        embedding_function=ef,
        metadata={"description": "stick-world 错误知识库"},
    )


def generate_id(symptom: str, module: str) -> str:
    """根据症状和模块生成唯一 ID。"""
    raw = f"{module}:{symptom}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def load_errors_json() -> list[dict]:
    """加载 errors.json。"""
    if ERRORS_FILE.exists():
        with open(ERRORS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_errors_json(errors: list[dict]):
    """保存 errors.json。"""
    with open(ERRORS_FILE, "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)


def store_entry(
    symptom: str,
    root_cause: str,
    fix: str,
    error_type: str = "unknown",
    module: str = "general",
    tags: list[str] | None = None,
    source: str = "manual",
) -> str:
    """存储一条错误记录到 JSON 和 ChromaDB。"""
    entry_id = generate_id(symptom, module)
    now = datetime.now(TZ).isoformat()

    entry = {
        "id": entry_id,
        "error_type": error_type,
        "module": module,
        "symptom": symptom,
        "root_cause": root_cause,
        "fix": fix,
        "tags": tags or [],
        "source": source,
        "timestamp": now,
    }

    # 更新 JSON 源文件
    errors = load_errors_json()
    # 检查是否已存在
    existing_idx = next((i for i, e in enumerate(errors) if e["id"] == entry_id), None)
    if existing_idx is not None:
        errors[existing_idx] = entry
        print(f"已更新现有记录: {entry_id}")
    else:
        errors.append(entry)
        print(f"已添加新记录: {entry_id}")
    save_errors_json(errors)

    # 更新 ChromaDB（如果已初始化）
    if DB_DIR.exists():
        try:
            collection = get_collection()
            from rebuild import build_document

            doc = build_document(entry)
            meta = {
                "error_type": error_type,
                "module": module,
                "symptom": symptom,
                "root_cause": root_cause,
                "fix": fix,
                "tags": ", ".join(tags or []),
                "source": source,
                "timestamp": now,
            }
            # 如果已存在则更新，否则添加
            existing = collection.get(ids=[entry_id])
            if existing and existing["ids"]:
                collection.update(ids=[entry_id], documents=[doc], metadatas=[meta])
            else:
                collection.add(ids=[entry_id], documents=[doc], metadatas=[meta])
            print("ChromaDB 已同步")
        except Exception as e:
            print(f"ChromaDB 同步失败（可稍后运行 rebuild.py 修复）: {e}")

    return entry_id


def store_from_ci_report(report_path: str):
    """从 CI 生成的 ai-feedback.json 批量导入错误。"""
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    failures = report.get("failures", [])
    if not failures:
        print("CI 报告中没有失败的测试")
        return

    print(f"从 CI 报告导入 {len(failures)} 条失败记录")
    for failure in failures:
        symptom = f"[{failure.get('suite', '')}] {failure.get('test', '')}: {failure.get('message', '')}"
        store_entry(
            symptom=symptom[:200],
            root_cause=failure.get("message", "")[:500],
            fix="待分析",
            error_type="test",
            module=failure.get("classname", "unknown"),
            tags=["ci", "test-failure"],
            source="ci",
        )


def main():
    parser = argparse.ArgumentParser(description="存储错误记录到向量数据库")
    parser.add_argument("--symptom", help="错误症状描述")
    parser.add_argument("--root-cause", help="根因分析")
    parser.add_argument("--fix", help="修复方案")
    parser.add_argument(
        "--type",
        default="unknown",
        dest="error_type",
        choices=[
            "compilation",
            "runtime",
            "logic",
            "ci",
            "test",
            "configuration",
            "engine",
            "unknown",
        ],
    )
    parser.add_argument("--module", default="general", help="相关模块")
    parser.add_argument("--tags", help="逗号分隔的标签")
    parser.add_argument("--source", default="manual", choices=["manual", "ci", "agent"])
    parser.add_argument("--from-ci-report", help="从 CI 报告 JSON 导入")

    args = parser.parse_args()

    if args.from_ci_report:
        store_from_ci_report(args.from_ci_report)
        return

    if not args.symptom:
        parser.error("需要 --symptom 或 --from-ci-report")

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    store_entry(
        symptom=args.symptom,
        root_cause=args.root_cause or "",
        fix=args.fix or "",
        error_type=args.error_type,
        module=args.module,
        tags=tags,
        source=args.source,
    )


if __name__ == "__main__":
    main()
