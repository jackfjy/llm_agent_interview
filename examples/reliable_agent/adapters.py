"""Optional real SDK boundaries. Proposals never grant approval.

Responses and Agents SDK draft text; the host must inspect it and create a task.
LangGraph invokes the same durable state machine; it does not replace its ledger.
"""
from typing import TypedDict


def _proposal(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('model did not return a nonempty text proposal')
    return {'payload': text.strip(), 'approved': False}


def responses_proposal(client, prompt, *, model):
    response = client.responses.create(model=model, input=prompt, store=False,
        instructions='Draft one delivery request for human review. Do not execute any action.')
    return _proposal(response.output_text)


async def agents_proposal(model, prompt):
    from agents import Agent, Runner, RunConfig
    agent = Agent(name='Delivery proposer', model=model,
                  instructions='Draft one delivery request for human review. Do not execute any action.')
    result = await Runner.run(agent, prompt, max_turns=1,
                              run_config=RunConfig(tracing_disabled=True))
    return _proposal(result.final_output)


class GraphState(TypedDict):
    task_id: str
    result: dict


def graph_run(runtime, task_id):
    from langgraph.graph import StateGraph, START, END
    from langsmith import tracing_context
    graph = StateGraph(GraphState)
    graph.add_node('durable_run', lambda state: {'result': runtime.run(state['task_id'])})
    graph.add_edge(START, 'durable_run')
    graph.add_edge('durable_run', END)
    with tracing_context(enabled=False):
        return graph.compile().invoke({'task_id': task_id})['result']
