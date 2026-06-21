#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语义搜索错误知识库。

用法:
    python query.py "GDScript 信号连接失败"              # 自然语言搜索
    python query.py "导出失败" --type ci --limit 3       # 按类型过滤
    python query.py "信号" --module godot-engine         # 按模块过滤
    python query.py "class_name" --json                  # JSON 输出
"""

import json
import sys
import argparse
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent / "chroma_db"


def get_collection():
    """获取 ChromaDB collection。"""
    import chromadb
    from rebuild import get_embedding_fn

    if not DB_DIR.exists():
        print("错误: ChromaDB 尚未初始化，请先运行: python tools/vector_db/rebuild.py")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(DB_DIR))
    ef = get_embedding_fn()
    return client.get_collection(name="project_errors", embedding_function=ef)


def format_result(i: int, meta: dict, distance: float) -> str:
    """格式化单条结果。"""
    sim_pct = (1 - distance) * 100
    lines = [
        f"\n{'─' * 60}",
        f"  #{i + 1}  相似度: {sim_pct:.0f}%  |  类型: {meta.get('error_type', '?')}  |  模块: {meta.get('module', '?')}",
        f"  症状: {meta.get('symptom', '')}",
        f"  根因: {meta.get('root_cause', '')}",
        f"  修复: {meta.get('fix', '')}",
    ]
    tags = meta.get("tags", "")
    if tags:
        lines.append(f"  标签: {tags}")
    return "\n".join(lines)


def query(
    text: str,
    error_type: str | None = None,
    module: str | None = None,
    limit: int = 5,
    threshold: float = 0.0,
    json_output: bool = False,
):
    """执行语义搜索。"""
    collection = get_collection()

    # 构建过滤条件
    where = {}
    if error_type:
        where["error_type"] = error_type
    if module:
        where["module"] = module

    kwargs = {
        "query_texts": [text],
        "n_results": limit,
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    if not results["ids"] or not results["ids"][0]:
        print("未找到匹配的错误记录")
        return

    items = []
    for i, (doc_id, meta, distance) in enumerate(
        zip(
            results["ids"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ):
        if threshold > 0 and distance > threshold:
            continue
        if json_output:
            items.append(
                {
                    "id": doc_id,
                    "similarity": round((1 - distance) * 100, 1),
                    "metadata": meta,
                    "document": results["documents"][0][i]
                    if results["documents"]
                    else "",
                }
            )
        else:
            print(format_result(i, meta, distance))

    if json_output:
        print(json.dumps(items, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="语义搜索错误知识库")
    parser.add_argument("query", help="搜索查询文本（自然语言）")
    parser.add_argument(
        "--type",
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
    parser.add_argument("--module", help="按模块过滤")
    parser.add_argument("--limit", type=int, default=5, help="返回结果数量")
    parser.add_argument(
        "--threshold", type=float, default=0.0, help="相似度阈值（0-1，越小越相似）"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="JSON 格式输出"
    )

    args = parser.parse_args()
    query(
        text=args.query,
        error_type=args.error_type,
        module=args.module,
        limit=args.limit,
        threshold=args.threshold,
        json_output=args.json_output,
    )


if __name__ == "__main__":
    main()
