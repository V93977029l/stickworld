#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""向量知识库统一管理 CLI。

用法:
    python manage.py rebuild              # 从 errors.json 重建向量库
    python manage.py store ...            # 存储错误（参数同 store.py）
    python manage.py query "..." [...]    # 语义搜索（参数同 query.py）
    python manage.py stats                # 查看统计信息
    python manage.py list [--type ci]     # 列出所有记录
    python manage.py export               # 导出为 JSON
"""

import sys
import argparse
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))


def cmd_rebuild(args):
    from rebuild import rebuild

    rebuild(force=args.force)


def cmd_store(args):
    from store import store_entry

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    store_entry(
        symptom=args.symptom,
        root_cause=args.root_cause or "",
        fix=args.fix or "",
        error_type=args.type,
        module=args.module,
        tags=tags,
        source=args.source,
    )


def cmd_query(args):
    from query import query

    query(
        text=args.query,
        error_type=args.type,
        module=args.module,
        limit=args.limit,
        threshold=args.threshold,
        json_output=args.json,
    )


def cmd_stats(args):
    import json
    from collections import Counter

    errors_file = TOOLS_DIR / "errors.json"
    if not errors_file.exists():
        print("errors.json 不存在")
        return

    with open(errors_file, "r", encoding="utf-8") as f:
        errors = json.load(f)

    print(f"总记录数: {len(errors)}")
    print()

    type_counts = Counter(e.get("error_type", "unknown") for e in errors)
    print("按错误类型:")
    for t, c in type_counts.most_common():
        print(f"  {t}: {c}")

    print()
    module_counts = Counter(e.get("module", "unknown") for e in errors)
    print("按模块:")
    for m, c in module_counts.most_common():
        print(f"  {m}: {c}")

    print()
    source_counts = Counter(e.get("source", "unknown") for e in errors)
    print("按来源:")
    for s, c in source_counts.most_common():
        print(f"  {s}: {c}")

    # 检查 ChromaDB 状态
    db_dir = TOOLS_DIR / "chroma_db"
    if db_dir.exists():
        print(f"\nChromaDB: 已初始化 ({db_dir})")
    else:
        print("\nChromaDB: 未初始化，运行 'python manage.py rebuild' 初始化")


def cmd_list(args):
    import json

    errors_file = TOOLS_DIR / "errors.json"
    if not errors_file.exists():
        print("errors.json 不存在")
        return

    with open(errors_file, "r", encoding="utf-8") as f:
        errors = json.load(f)

    if args.type:
        errors = [e for e in errors if e.get("error_type") == args.type]
    if args.module:
        errors = [
            e for e in errors if args.module.lower() in e.get("module", "").lower()
        ]
    if args.search:
        keyword = args.search.lower()
        errors = [
            e
            for e in errors
            if keyword in e.get("symptom", "").lower()
            or keyword in e.get("root_cause", "").lower()
            or keyword in e.get("fix", "").lower()
            or any(keyword in t.lower() for t in e.get("tags", []))
        ]

    if not errors:
        print("无匹配记录")
        return

    for i, e in enumerate(errors):
        print(f"\n{'─' * 50}")
        print(f"[{i + 1}] {e['id']}")
        print(
            f"  类型: {e.get('error_type', '?')}  |  模块: {e.get('module', '?')}  |  来源: {e.get('source', '?')}"
        )
        print(f"  症状: {e.get('symptom', '')}")
        print(f"  修复: {e.get('fix', '')}")
        print(f"  标签: {', '.join(e.get('tags', []))}")


def cmd_export(args):
    import shutil

    errors_file = TOOLS_DIR / "errors.json"
    if not errors_file.exists():
        print("errors.json 不存在")
        return

    output = args.output or "errors_export.json"
    shutil.copy(errors_file, output)
    print(f"已导出到: {output}")


def main():
    parser = argparse.ArgumentParser(description="向量知识库管理工具")
    sub = parser.add_subparsers(dest="command", help="子命令")

    # rebuild
    p_rebuild = sub.add_parser("rebuild", help="从 errors.json 重建向量库")
    p_rebuild.add_argument("--force", action="store_true", help="强制重建")
    p_rebuild.set_defaults(func=cmd_rebuild)

    # store
    p_store = sub.add_parser("store", help="存储错误记录")
    p_store.add_argument("--symptom", required=True)
    p_store.add_argument("--root-cause", default="")
    p_store.add_argument("--fix", default="")
    p_store.add_argument(
        "--type",
        default="unknown",
        dest="type",
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
    p_store.add_argument("--module", default="general")
    p_store.add_argument("--tags", default="")
    p_store.add_argument(
        "--source", default="manual", choices=["manual", "ci", "agent"]
    )
    p_store.set_defaults(func=cmd_store)

    # query
    p_query = sub.add_parser("query", help="语义搜索")
    p_query.add_argument("query")
    p_query.add_argument(
        "--type",
        dest="type",
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
    p_query.add_argument("--module")
    p_query.add_argument("--limit", type=int, default=5)
    p_query.add_argument("--threshold", type=float, default=0.0)
    p_query.add_argument("--json", action="store_true")
    p_query.set_defaults(func=cmd_query)

    # stats
    p_stats = sub.add_parser("stats", help="统计信息")
    p_stats.set_defaults(func=cmd_stats)

    # list
    p_list = sub.add_parser("list", help="列出记录")
    p_list.add_argument("--type")
    p_list.add_argument("--module")
    p_list.add_argument("--search")
    p_list.set_defaults(func=cmd_list)

    # export
    p_export = sub.add_parser("export", help="导出 JSON")
    p_export.add_argument("--output")
    p_export.set_defaults(func=cmd_export)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
