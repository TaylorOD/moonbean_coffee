import re
from pathlib import Path

HANDBOOK_PATH = Path(__file__).parent.parent / "data" / "moonbean_handbook.md"


def slugify(title, separator="-"):
    return re.sub(r"[^a-z0-9]+", separator, title.lower()).strip(separator)


def read_handbook():
    return HANDBOOK_PATH.read_text(encoding="utf-8")


def to_records(text):
    """One Pinecone record per h1 section of the handbook."""
    chunks = re.findall(r"(?m)^# .+?(?=^# |\Z)", text, re.DOTALL)
    records = []
    for chunk in chunks:
        title = chunk.splitlines()[0].removeprefix("# ").strip()
        records.append({"id": slugify(title), "section": title, "chunk_text": chunk.strip()})
    return records
