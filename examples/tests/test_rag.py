import unittest
from examples.rag.engine import KnowledgeBase


class RAGTests(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase()
        self.kb.upsert('guide', 'Atlas refund window is 30 days.', ['staff'], version=1)
        self.kb.upsert('secret', 'Atlas refund secret is 999 days.', ['finance'])

    def test_permission_before_ranking_and_citations(self):
        hits = self.kb.retrieve('Atlas refund', 'staff', limit=1)
        self.assertEqual([h['id'] for h in hits], ['guide'])
        answer = self.kb.answer('Atlas refund', 'staff')
        self.assertEqual([s['id'] for s in answer['sources']], ['guide'])
        self.assertNotIn('999', answer['answer'])

    def test_update_replaces_old_text_and_citation_version(self):
        self.kb.upsert('guide', 'Atlas warranty lasts 90 days.', ['staff'], version=2)
        self.assertEqual(self.kb.retrieve('refund', 'staff'), [])
        answer = self.kb.answer('warranty', 'staff')
        self.assertIn('90', answer['answer'])
        self.assertEqual(answer['sources'][0]['version'], 2)

    def test_delete_removes_evidence(self):
        self.kb.delete('guide')
        self.assertTrue(self.kb.answer('refund', 'staff')['refused'])
        self.assertEqual(self.kb.retrieve('refund', 'staff'), [])

    def test_unknown_query_refuses_despite_hash_collision(self):
        answer = self.kb.answer('unicorn', 'staff')
        self.assertTrue(answer['refused'])
        self.assertEqual(answer['sources'], [])

    def test_permission_revocation_takes_effect(self):
        self.kb.upsert('guide', 'Atlas refund window is 30 days.', ['finance'], version=2)
        self.assertTrue(self.kb.answer('refund', 'staff')['refused'])

    def test_ranking_exposes_keyword_vector_and_rerank_evidence(self):
        self.kb.upsert('partial', 'Atlas guide.', ['staff'])
        result = self.kb.retrieve('Atlas refund', 'staff')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'guide')
        self.assertGreater(result[0]['keyword'], result[1]['keyword'])
        self.assertIn('vector', result[0])
        self.assertIn('rerank', result[0])

    def test_empty_query_and_zero_limit_return_no_evidence(self):
        self.assertEqual(self.kb.retrieve('', 'staff'), [])
        self.assertEqual(self.kb.retrieve('Atlas', 'staff', limit=0), [])

    def test_private_text_is_not_vectorized_for_unauthorized_principal(self):
        from unittest.mock import patch
        from examples.rag.engine import vector
        def checked_vector(terms, dimensions=64):
            self.assertNotIn('999', terms)
            return vector(terms, dimensions)
        with patch('examples.rag.engine.vector', side_effect=checked_vector):
            self.assertEqual(self.kb.retrieve('refund', 'staff')[0]['id'], 'guide')
