from pathlib import Path
from typing import List, Dict
from PyPDF2 import PdfReader


SKIP_FILENAMES = {"readme.md", "readme.txt"}


def load_documents(data_dir: str = "data") -> List[Dict]:
    """指定ディレクトリ配下の文書を読み込みます。

    README 系の説明ファイルはデータセットに混ざらないよう除外します。

    引数:
        data_dir: 入力文書を格納しているルートディレクトリです。

    戻り値:
        文書 ID、タイトル、本文、ソースパスを含む辞書のリストを返します。
    """
    base = Path(data_dir)
    docs: List[Dict] = []

    for path in sorted(base.glob("**/*")):
        if path.is_dir():
            continue
        if path.name.lower() in SKIP_FILENAMES:
            continue

        suffix = path.suffix.lower()
        if suffix in {".md", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
        elif suffix == ".pdf":
            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            continue

        cleaned = " ".join(text.split())
        if cleaned:
            docs.append({
                "id": path.stem,
                "title": path.name,
                "text": cleaned,
                "source": str(path)
            })
    return docs
