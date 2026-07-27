"""依赖分析 — Kahn 拓扑排序"""
from collections import deque
from app.engine.parser import RuleConfig


class CyclicDependencyError(Exception):
    """循环依赖异常"""

    def __init__(self, fields: list[str]):
        self.fields = fields
        super().__init__(f"检测到循环依赖: {fields}")


def topological_sort(rules: list[RuleConfig]) -> list[list[RuleConfig]]:
    """
    对规则进行拓扑排序，返回分层执行顺序。
    Level 0 的规则可并行执行，Level N 依赖前面所有层的输出。
    """
    field_to_rule = {r.field_name: r for r in rules}

    in_degree: dict[str, int] = {r.field_name: 0 for r in rules}
    graph: dict[str, list[str]] = {r.field_name: [] for r in rules}

    for rule in rules:
        for dep in rule.depends_on:
            if dep in field_to_rule:
                graph[dep].append(rule.field_name)
                in_degree[rule.field_name] += 1

    queue = deque([f for f, d in in_degree.items() if d == 0])
    levels: list[list[RuleConfig]] = []
    processed: set[str] = set()

    while queue:
        level = []
        for _ in range(len(queue)):
            field = queue.popleft()
            processed.add(field)
            level.append(field_to_rule[field])
            for neighbor in graph[field]:
                if neighbor not in processed:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        levels.append(level)

    total = sum(len(l) for l in levels)
    if total != len(rules):
        remaining = [f for f, d in in_degree.items() if d > 0]
        raise CyclicDependencyError(remaining)

    return levels
