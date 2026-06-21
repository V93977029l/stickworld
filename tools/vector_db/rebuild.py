#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 errors.json 重建 ChromaDB 向量数据库。

用法:
    python rebuild.py [--force]
"""

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = Path(__file__).resolve().parent / "chroma_db"
ERRORS_FILE = Path(__file__).resolve().parent / "errors.json"


def get_embedding_fn():
    """获取嵌入函数，使用轻量级中文友好的模型。"""
    try:
        from chromadb.utils import embedding_functions

        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
    except ImportError:
        print("错误: 请先安装依赖: pip install -r tools/vector_db/requirements.txt")
        sys.exit(1)


def load_errors() -> list[dict]:
    """加载 errors.json 中的所有错误记录。"""
    if not ERRORS_FILE.exists():
        print(f"警告: {ERRORS_FILE} 不存在，创建空文件")
        ERRORS_FILE.write_text("[]", encoding="utf-8")
        return []
    with open(ERRORS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_document(entry: dict) -> str:
    """将错误记录拼接为用于嵌入的文本。"""
    parts = [
        f"症状: {entry.get('symptom', '')}",
        f"根因: {entry.get('root_cause', '')}",
        f"修复: {entry.get('fix', '')}",
        f"标签: {', '.join(entry.get('tags', []))}",
    ]
    return "\n".join(parts)


def rebuild(force: bool = False):
    """重建 ChromaDB 数据库。"""
    import chromadb

    if DB_DIR.exists() and not force:
        print(f"ChromaDB 已存在于 {DB_DIR}，使用 --force 强制重建")
        return

    errors = load_errors()
    if not errors:
        print("没有错误记录，跳过重建")
        return

    print(f"加载了 {len(errors)} 条错误记录")

    # 清空旧数据库
    if DB_DIR.exists():
        import shutil

        shutil.rmtree(DB_DIR)
        print("已清空旧数据库")

    # 创建 ChromaDB 客户端
    client = chromadb.PersistentClient(path=str(DB_DIR))
    ef = get_embedding_fn()

    collection = client.get_or_create_collection(
        name="project_errors",
        embedding_function=ef,
        metadata={"description": "stick-world 错误知识库"},
    )

    # 批量插入
    ids = []
    documents = []
    metadatas = []

    for entry in errors:
        ids.append(entry["id"])
        documents.append(build_document(entry))
        metadatas.append(
            {
                "error_type": entry.get("error_type", ""),
                "module": entry.get("module", ""),
                "symptom": entry.get("symptom", ""),
                "root_cause": entry.get("root_cause", ""),
                "fix": entry.get("fix", ""),
                "tags": ", ".join(entry.get("tags", [])),
                "source": entry.get("source", ""),
                "timestamp": entry.get("timestamp", ""),
            }
        )

    # ChromaDB 批量添加
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"重建完成: {len(ids)} 条记录已写入 ChromaDB")


if __name__ == "__main__":
    force = "--force" in sys.argv
    rebuild(force=force)
