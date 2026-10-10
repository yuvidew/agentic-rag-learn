from dotenv import load_dotenv

from pathlib import Path
from app.core.config import get_settings
from app.services.ingestion import load_files, chunk_documents
from app.rag.vectorestore import add_documents

load_dotenv()

settings = get_settings()

folder = Path(settings.sample_kb_dir)
files = [p for p in folder.iterdir() if p.is_file()]

all_docs = []

for path in files:
    all_docs.extend(load_files(path))
chunks = chunk_documents(all_docs)
ids = add_documents(chunks)

print(f"Indexed {len(files)} files -> {len(chunks)} chunks -> {len(ids)}")