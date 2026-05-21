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
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)  # 指定サイズと重なり幅で分割器を作成する
    chunks: List[Dict] = []  # 分割後のチャンクを格納するリストを初期化する
    for doc in documents:  # すべての文書を順に処理する
        parts = splitter.split_text(doc["text"])  # 文書本文をチャンク単位に分割する
        for i, part in enumerate(parts):  # 分割結果を順番に取り出して番号を振る
            chunks.append({
                "id": f"{doc['id']}-chunk-{i}",  # 元文書IDにチャンク番号を付けた一意IDを作る
                "title": doc["title"],  # 元文書のタイトルを保持する
                "text": part,  # 分割されたチャンク本文を保存する
                "source": doc.get("source", doc["title"]),  # 元データのsourceがあれば使い、なければtitleを使う
                "parent_id": doc["id"],  # このチャンクの元になった文書IDを保存する
                "chunk_index": i,  # 何番目のチャンクかを記録する
            })
    return chunks  # すべてのチャンクを返す
