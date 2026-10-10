import time
from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from app.core.config import get_settings

setting = get_settings()

_embeddings = None
_vectorestore = None

# getting embeddings of the docuements 
def get_embeddings():
    global _embeddings

    if _embeddings is None:
        if not setting.embedding_model:
            raise RuntimeError("embedding_model is missing")

        _embeddings = HuggingFaceEmbeddings(
            model_name=setting.embedding_model,
            encode_kwargs={"normalize_embeddings": True}
        )

    return _embeddings

# Make sure the Pinecone index exists with the right dimension (recreating it on mismatch) and return it.
def ensure_index():
    if not setting.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is missing")

    # 384 for all-MiniLM-L6-v2; measured from the model so it stays correct if the model changes
    desired_dimension = len(get_embeddings().embed_query("dimension probe"))

    pc = Pinecone(api_key=setting.pinecone_api_key)
    names = [x["name"] for x in pc.list_indexes()]

    if setting.pinecone_index_name in names:
        index_info = pc.describe_index(setting.pinecone_index_name)
        current_dimension = getattr(index_info, "dimension", None)

        if current_dimension is None and isinstance(index_info, dict):
            current_dimension = index_info.get("dimension")

        if current_dimension is not None and current_dimension != desired_dimension:
            pc.delete_index(name=setting.pinecone_index_name)

            while setting.pinecone_index_name in [x["name"] for x in pc.list_indexes()]:
                time.sleep(1)

    if setting.pinecone_index_name not in [x["name"] for x in pc.list_indexes()]:
        pc.create_index(
            name= setting.pinecone_index_name,
            dimension=desired_dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

        while not pc.describe_index(
            setting.pinecone_index_name
        ).status["ready"]:
            time.sleep(1)

    return pc.Index(setting.pinecone_index_name)

# Return the cached PineconeVectorStore, creating it on first use.
def get_vectorestore():
    global _vectorestore

    if _vectorestore is None:
        index = ensure_index()

        _vectorestore = PineconeVectorStore(
            index=index,
            embedding= get_embeddings(),
            namespace=setting.pinecone_namespace
        )

    return _vectorestore

# Return a retriever that fetches the top_k most similar chunks from the vector store.
def get_retriever():
    return get_vectorestore().as_retriever(search_kwargs={
        "k" : setting.top_k
    })

# Embed the given chunks and upsert them into the vector store.
def add_documents(chunks):
    store = get_vectorestore()

    return store.add_documents(chunks)