# build_index.py
import json, pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = "chunks.json"
INDEX_FILE  = "faiss.index"
META_FILE   = "chunks_meta.pkl"

# بهترین مدل چندزبانه برای فارسی
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

print("📥 بارگذاری مدل embedding...")
model = SentenceTransformer(EMBED_MODEL, device='cuda')  # GPU

with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
    chunks = json.load(f)

texts = [c['text'] for c in chunks]
print(f"🔢 encoding {len(texts)} chunks...")

embeddings = model.encode(
    texts,
    batch_size=64,
    show_progress_bar=True,
    normalize_embeddings=True,
    convert_to_numpy=True,
).astype(np.float32)

dim = embeddings.shape[1]
index = faiss.IndexFlatIP(dim)  # cosine similarity (با normalize)
index.add(embeddings)

faiss.write_index(index, INDEX_FILE)
with open(META_FILE, 'wb') as f:
    pickle.dump(chunks, f)

print(f"✅ Index: {index.ntotal} بردار | dim={dim}")
print(f"💾 {INDEX_FILE} + {META_FILE}")
