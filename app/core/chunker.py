"""文書を重なり付きで分割してチャンク化するためのモジュールです。"""

from typing import Dict, List
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(documents: List[Dict], chunk_size: int = 300, chunk_overlap: int = 50) -> List[Dict]:
    """各文書を分割し、チャンク用のメタデータを付与します。

    引数:
        documents: `id`、`title`、`text` を含む文書辞書のリストです。
        chunk_size: 1チャンクあたりの最大文字数です。
        chunk_overlap: 隣接チャンク間で重ねる文字数です。

    戻り値:
        チャンク単位のメタデータを含む辞書のリストを返します。
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks: List[Dict] = []

    for doc in documents:
        parts = splitter.split_text(doc["text"])
        for i, part in enumerate(parts):
            chunks.append({
                "id": f"{doc['id']}-chunk-{i}",
                "title": doc["title"],
                "text": part,
                "source": doc.get("source", doc["title"]),
                "parent_id": doc["id"],
                "chunk_index": i,
            })
    return chunks
