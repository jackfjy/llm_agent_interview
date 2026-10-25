"""Run from repository root: python -m examples.rag.demo."""
import json
from examples.rag.engine import KnowledgeBase


def main():
    kb = KnowledgeBase()
    kb.upsert('差旅政策', '差旅报销需要发票，提交期限为30天。', ['employee'])
    result = {'authorized': kb.answer('报销', 'employee'),
              'unauthorized': kb.answer('报销', 'guest')}
    kb.upsert('差旅政策', '差旅报销需要发票，提交期限为14天。', ['employee'], version=2)
    result['updated'] = kb.answer('报销', 'employee')
    kb.delete('差旅政策')
    result['deleted'] = kb.answer('报销', 'employee')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
