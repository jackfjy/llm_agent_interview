"""Tiny extractive RAG: authorization → hybrid retrieval → explainable rerank."""
import hashlib
import math
import re


def tokens(text):
    # English words and Chinese bigrams; no semantic or linguistic model.
    words = re.findall(r'[a-z0-9]+|[\u4e00-\u9fff]+', text.lower())
    return set(t for word in words for t in
               ([word] if not re.match(r'[\u4e00-\u9fff]', word) or len(word) == 1
                else [word[i:i + 2] for i in range(len(word) - 1)]))


def vector(terms, dimensions=64):
    result = [0.0] * dimensions
    for term in terms:
        slot = int.from_bytes(hashlib.sha256(term.encode()).digest()[:4], 'big') % dimensions
        result[slot] += 1
    norm = math.sqrt(sum(x * x for x in result)) or 1
    return [x / norm for x in result]


class KnowledgeBase:
    """One document = one chunk. Trusted callers supply the authenticated principal."""

    def __init__(self):
        self.documents = {}

    def upsert(self, doc_id, text, readers, version=1):
        if not doc_id or not text.strip() or not readers:
            raise ValueError('id, text and readers are required')
        self.documents[doc_id] = {'id': doc_id, 'text': text,
                                  'readers': frozenset(readers), 'version': version}

    def delete(self, doc_id):
        self.documents.pop(doc_id, None)

    def retrieve(self, query, principal, limit=3):
        query_terms = tokens(query)
        if not query_terms or limit <= 0:
            return []
        query_vector = vector(query_terms)
        candidates = []
        for doc in self.documents.values():
            # ACL is checked before document tokenization, vectorization, or scoring.
            if principal not in doc['readers'] and '*' not in doc['readers']:
                continue
            document_terms = tokens(doc['text'])
            matched = query_terms & document_terms
            if not matched:  # Hash collisions alone never count as evidence.
                continue
            keyword = len(matched) / len(query_terms)
            similarity = sum(a * b for a, b in zip(query_vector, vector(document_terms)))
            hybrid = 0.7 * keyword + 0.3 * similarity
            phrase = float(query.lower() in doc['text'].lower())
            candidates.append({'id': doc['id'], 'text': doc['text'], 'version': doc['version'],
                               'keyword': keyword, 'vector': similarity, 'hybrid': hybrid,
                               'rerank': hybrid + 0.2 * phrase,
                               'matched': sorted(matched), 'phrase_bonus': 0.2 * phrase})
        return sorted(candidates, key=lambda d: (-d['rerank'], d['id']))[:limit]

    def answer(self, query, principal):
        hits = self.retrieve(query, principal)
        sources = [{'id': h['id'], 'version': h['version'], 'text': h['text']} for h in hits]
        return {'refused': not hits,
                'answer': '\n'.join(f"[{s['id']}@v{s['version']}] {s['text']}" for s in sources)
                if hits else '没有可访问的证据，拒绝作答。', 'sources': sources}
