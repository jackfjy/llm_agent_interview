import json
import subprocess
import sys
import unittest


class DemoTests(unittest.TestCase):
    def demo(self, module):
        process = subprocess.run([sys.executable, '-m', module], capture_output=True, text=True, timeout=20, check=True)
        self.assertEqual(process.stderr, '')
        return json.loads(process.stdout)

    def test_rag_demo_shows_authorization_update_and_delete(self):
        result = self.demo('examples.rag.demo')
        self.assertFalse(result.get('authorized', {}).get('refused', True))
        self.assertTrue(result['unauthorized']['refused'])
        self.assertEqual(result['updated']['sources'][0]['version'], 2)
        self.assertTrue(result['deleted']['refused'])

    def test_agent_demo_proves_recovery_after_external_commit(self):
        result = self.demo('examples.reliable_agent.demo')
        self.assertEqual(result.get('before_approval'), 'waiting_approval')
        self.assertEqual(result['after_recovery'], 'completed')
        self.assertEqual(result['effects_after_crash'], 1)
        self.assertEqual(result['effects_after_recovery'], 1)
        self.assertIn('recovered', result['trace'])
