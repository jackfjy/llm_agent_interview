import asyncio
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from examples.reliable_agent import adapters
from examples.reliable_agent.engine import AgentRuntime, ExternalService

SDK_AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ('openai', 'agents', 'langgraph', 'httpx2'))


@unittest.skipUnless(SDK_AVAILABLE, 'optional SDKs missing; install examples/requirements.lock')
class AdapterTests(unittest.TestCase):
    def test_responses_sdk_request_and_unapproved_proposal(self):
        from openai import OpenAI
        import httpx2
        requests = []
        def handle(request):
            requests.append(json.loads(request.content))
            return httpx2.Response(200, json={'id': 'resp_fixture', 'object': 'response', 'created_at': 0,
                'model': 'fixture-model', 'status': 'completed', 'output': [{'id': 'msg_fixture',
                'type': 'message', 'role': 'assistant', 'status': 'completed', 'content': [
                {'type': 'output_text', 'text': 'ship book', 'annotations': []}]}]})
        with OpenAI(api_key='offline-fixture', base_url='https://fixture.invalid/v1',
                    http_client=httpx2.Client(transport=httpx2.MockTransport(handle)), max_retries=0) as client:
            proposal = adapters.responses_proposal(client, 'please ship a book', model='fixture-model')
        self.assertEqual(proposal, {'payload': 'ship book', 'approved': False})
        self.assertEqual(requests[0]['input'], 'please ship a book')
        self.assertEqual(requests[0]['model'], 'fixture-model')
        self.assertFalse(requests[0]['store'])

    def test_agents_runner_uses_model_response_without_authorizing_effect(self):
        from agents import Model, ModelResponse, Usage
        from openai.types.responses import ResponseOutputMessage, ResponseOutputText
        class FixtureModel(Model):
            async def get_response(self, system_instructions, input, model_settings, tools,
                                   output_schema, handoffs, tracing, **kwargs):
                if input != [{'content': 'please ship a book', 'role': 'user'}] or tools or handoffs:
                    raise AssertionError('proposal contract changed')
                return ModelResponse(output=[ResponseOutputMessage(id='msg_fixture', type='message',
                    role='assistant', status='completed', content=[ResponseOutputText(
                    type='output_text', text='ship book', annotations=[])])], usage=Usage(), response_id='resp_fixture')
            async def stream_response(self, *args, **kwargs):
                raise NotImplementedError('not a streaming fixture')
                yield
        proposal = asyncio.run(adapters.agents_proposal(FixtureModel(), 'please ship a book'))
        self.assertEqual(proposal, {'payload': 'ship book', 'approved': False})

    def test_langgraph_invokes_durable_runtime_and_respects_approval(self):
        with TemporaryDirectory() as directory:
            service = ExternalService(Path(directory) / 'remote.db')
            runtime = AgentRuntime(Path(directory) / 'local.db', service)
            runtime.create('a', 'ship book')
            result = adapters.graph_run(runtime, 'a')
            self.assertEqual(result['status'], 'waiting_approval')
            self.assertEqual(service.count(), 0)
            runtime.approve('a')
            self.assertEqual(adapters.graph_run(runtime, 'a')['status'], 'completed')
            self.assertEqual(service.count(), 1)
