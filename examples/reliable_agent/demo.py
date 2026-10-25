"""Run an approval → external commit → crash → recovery story without live services."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from examples.reliable_agent.engine import AgentRuntime, ExternalService, InjectedCrash


def main():
    with TemporaryDirectory() as directory:
        local, remote = Path(directory) / 'local.sqlite', Path(directory) / 'external.sqlite'
        service = ExternalService(remote)
        agent = AgentRuntime(local, service)
        agent.create('book-order-001', '寄送一本教材')
        before = agent.run('book-order-001')['status']
        agent.approve('book-order-001')
        try:
            agent.run('book-order-001', crash_after_effect=True)
        except InjectedCrash:
            pass
        effects = service.count()
        restarted_service = ExternalService(remote)
        restarted_agent = AgentRuntime(local, restarted_service)
        after = restarted_agent.run('book-order-001')['status']
        print(json.dumps({'before_approval': before, 'effects_after_crash': effects,
            'after_recovery': after, 'effects_after_recovery': restarted_service.count(),
            'trace': [e['event'] for e in restarted_agent.trace('book-order-001')]},
            ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
