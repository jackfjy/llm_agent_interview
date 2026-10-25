"""Pure tool dispatch shared by offline tests and the official MCP server."""
import ast
import math
import operator

BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: operator.truediv}
UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
WEATHER = {'南京': (22, '晴'), '北京': (18, '多云')}


def calculate(expression):
    if not isinstance(expression, str) or not 0 < len(expression) <= 200:
        raise ValueError('expression must contain 1–200 characters')
    tree = ast.parse(expression, mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 64:
        raise ValueError('expression has too many nodes')

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.BinOp) and type(node.op) in BINARY:
            value = BINARY[type(node.op)](visit(node.left), visit(node.right))
        elif isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
            value = UNARY[type(node.op)](visit(node.operand))
        else:
            raise ValueError('only numbers, parentheses and + - * / are allowed')
        if not math.isfinite(value) or abs(value) > 1_000_000_000:
            raise ValueError('intermediate magnitude must be <= 1e9')
        return value

    return visit(tree.body)


def dispatch(name, arguments):
    try:
        if not isinstance(arguments, dict):
            raise ValueError('arguments must be an object')
        if name == 'calculate' and set(arguments) == {'expression'}:
            result = calculate(arguments['expression'])
        elif name == 'get_weather' and set(arguments) == {'city'}:
            city = arguments['city']
            if not isinstance(city, str) or city not in WEATHER:
                raise ValueError('unknown fixture city')
            temperature, condition = WEATHER[city]
            result = {'city': city, 'temperature_c': temperature,
                      'condition': condition, 'fixture': True}
        else:
            raise ValueError('unknown tool or invalid arguments')
        return {'ok': True, 'result': result}
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, RecursionError) as exc:
        return {'ok': False, 'error': str(exc)}
