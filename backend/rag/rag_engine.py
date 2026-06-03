from functools import lru_cache

from sentence_transformers import SentenceTransformer
import chromadb

model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.Client()
collection = client.get_or_create_collection("research_docs")


@lru_cache(maxsize=512)
def _encode_cached(text: str) -> tuple:
    return tuple(model.encode(text).tolist())


def add_document(doc_id, text, metadata={}):
    embedding = model.encode(text).tolist()
    collection.add(ids=[doc_id], embeddings=[embedding], documents=[text], metadatas=[metadata])
    return {"status": "added"}


def search_documents(query, n_results=3):
    qe = list(_encode_cached(query))
    return collection.query(query_embeddings=[qe], n_results=n_results)


# تقسيم النص إلى أجزاء صغيرة (chunks) بحيث يكون كل جزء حوالي 200 كلمة
# مع تداخل 20 كلمة بين كل جزء والذي يليه لتحسين جودة البحث
def chunk_text(text, chunk_size=200, overlap=20):
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [text]
    step = chunk_size - overlap
    chunks = []
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + chunk_size])
        chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
    return chunks


# تقسيم المستند إلى أجزاء وتخزين كل جزء بشكل منفصل في ChromaDB
# مع حفظ معلومات إضافية (chunk_index, total_chunks, parent_doc_id) في الـ metadata
def add_document_chunked(doc_id, text, metadata=None):
    metadata = metadata or {}
    chunks = chunk_text(text)
    if not chunks:
        return {"status": "added", "doc_id": doc_id, "total_chunks": 0}

    total = len(chunks)
    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        ids.append(f"{doc_id}_chunk_{i}")
        embeddings.append(model.encode(chunk).tolist())
        documents.append(chunk)
        metadatas.append({**metadata, "chunk_index": i, "total_chunks": total, "parent_doc_id": doc_id})

    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    return {"status": "added", "doc_id": doc_id, "total_chunks": total}


# بحث في المستندات المقسّمة وإرجاع النتائج مع معلومات الـ chunk
# كل نتيجة تحتوي على النص والـ metadata والمسافة عن الاستعلام
def search_chunked_documents(query, n_results=3):
    qe = list(_encode_cached(query))
    raw = collection.query(query_embeddings=[qe], n_results=n_results)
    return [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(
            raw["documents"][0],
            raw["metadatas"][0],
            raw["distances"][0],
        )
    ]
