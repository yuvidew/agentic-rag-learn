from langchain_core.embeddings import Embeddings
from groq import Groq


class GroqEmbeddings(Embeddings):
    def __init__(self, model: str, api_key: str, batch_size: int = 64):
        self.model = model
        self.batch_size = batch_size
        self.client = Groq(api_key=api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            res = self.client.embeddings.create(
                input=batch,
                model=self.model,
                encoding_format="float"
            )
            vectors.extend(d.embedding for d in sorted(res.data, key=lambda d: d.index))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]