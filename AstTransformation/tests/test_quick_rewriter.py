import unittest

import ast
from ast_transform import astor_fork

from ast_transform import rewriter
from ast_transform import splitter_analyzer
from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from ast_transform import common
from unittest.mock import patch
import io

config = common.Config()
config.awaitable_functions = ["search_email", "search_teams", "search_meetings"]
config.module_blacklist = None




def walk_groups(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = analyzer2.critical_node_names
    crit = analyzer2.critical_nodes
    grps = analyzer2.concurrency_groups
    for c in crit:
        try:
            gn = analyzer2.critical_node_to_group[c].name
            code = astor_fork.to_source(c).strip()
            nodec = analyzer2.node_lookup[c]
            result = " ".join([named[item] for item in nodec.dependency])

            print(named[c] + " => " + gn + " used by (" + result + ")" + " = " + code)
        except Exception:
            pass

    print()

    for n in grps:
        result = " ".join(sorted([item.name for item in n.depends_on_group]))
        resultn = " ".join(sorted([named[item] for item in n.grouped_critical_nodes]))
        print(n.name + " <= (" + resultn + ") : uses " + result)

    print()


def walk_nodes(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = analyzer2.critical_node_names
    crit = analyzer2.critical_nodes
    for c in crit:
        try:
            gn = analyzer2.critical_node_to_group[c].name
            code = astor_fork.to_source(c).strip()
            print(gn + " = " + code)
        except Exception:
            pass
    for n in analyzer2.node_lookup.keys():
        nodec = analyzer2.node_lookup[n]
        if not nodec.dependency_visited:
            continue
        try:
            code = astor_fork.to_source(n).strip()
            result2 = " ".join([named[item] for item in nodec.dependency])
            print(nodec.assigned_concurrency_group.name + ": " + result2 + " " + code)
        except Exception:
            pass
    pass


class TestQRAnalyzerModule(unittest.TestCase):
    def get(self, code):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            print(code)
            print()

            tree = ast.parse(code)
            analyzer1 = variables_analyzer.Scan(tree, config)
            analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
            analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
            walk_groups(analyzer3)
            walk_nodes(analyzer3)
            rewrite= rewriter.Scan(tree, analyzer3)
            result = astor_fork.to_source(rewrite).strip()
            print('')
            print(result)
            result = mock_stdout.getvalue().strip()
            return result

##########################
    def test_critical_if_split(self):
        source_code = """
n=search_teams(0)
m = search_teams(n)
if n==3:
    a=search_email(1)
else:
    if m==3:
        a=search_email(2)
    else:
        a=search_email(3)
return search_teams(a)
"""

        expected = """
n=search_teams(0)
m = search_teams(n)
if n==3:
    a=search_email(1)
else:
    if m==3:
        a=search_email(2)
    else:
        a=search_email(3)
return search_teams(a)


C0 => G0 used by (C1 C2 C3 C4) = search_teams(0)
C1 => G1 used by (C3 C4) = search_teams(n)
C2 => G1 used by (C5) = search_email(1)
C3 => G2 used by (C5) = search_email(2)
C4 => G2 used by (C5) = search_email(3)
C5 => G3 used by (C6) = search_teams(a)
C6 => G4 used by () = return search_teams(a)

G0 <= (C0) : uses 
G1 <= (C1 C2) : uses G0
G2 <= (C3 C4) : uses G0 G1
G3 <= (C5) : uses G1 G2 G_a
G4 <= (C6) : uses G3
G_a <= () : uses G1 G2

G0 = search_teams(0)
G1 = search_teams(n)
G1 = search_email(1)
G2 = search_email(2)
G2 = search_email(3)
G3 = search_teams(a)
G4 = return search_teams(a)
G1: C1 C2 C3 C4 n = search_teams(0)
G0: C1 C2 C3 C4 search_teams(0)
G0: C0 search_teams
G0: C0 0
G2: C3 C4 m = search_teams(n)
G1: C3 C4 search_teams(n)
G1: C1 search_teams
G1: C1 n
G1: C2 C3 C4 (n == 3)
G1: C2 C3 C4 n
G1: C2 C3 C4 3
G_a: C5 a = search_email(1)
G1: C5 search_email(1)
G1: C2 search_email
G1: C2 1
G2: C3 C4 (m == 3)
G2: C3 C4 m
G2: C3 C4 3
G_a: C5 a = search_email(2)
G2: C5 search_email(2)
G2: C3 search_email
G2: C3 2
G_a: C5 a = search_email(3)
G2: C5 search_email(3)
G2: C4 search_email
G2: C4 3
G4:  return search_teams(a)
G3: C6 search_teams(a)
G3: C5 search_teams
G3: C5 a

import orchestrator
orchestrator = orchestrator.Orchestrator()


def _program(orchestrator):
    _C0 = _C1 = _C2 = _C3 = _C4 = _C5 = _return_value = a = m = n = None

    def _concurrent_G0():
        nonlocal _C0
        _C0 = orchestrator.search_teams(0, _id='_C0')

    def _concurrent_G1():
        nonlocal _C0, _C1, _C2, n
        n = _C0.Result
        _C1 = orchestrator.search_teams(n, _id='_C1')
        if n == 3:
            _C2 = orchestrator.search_email(1, _id='_C2')

    def _concurrent_G2():
        nonlocal _C1, _C3, _C4, m
        m = _C1.Result
        if not n == 3 and m == 3:
            _C3 = orchestrator.search_email(2, _id='_C3')
        if not n == 3 and not m == 3:
            _C4 = orchestrator.search_email(3, _id='_C4')

    def _concurrent_G3():
        nonlocal _C5, a
        _C5 = orchestrator.search_teams(a, _id='_C5')

    def _concurrent_G4():
        nonlocal _C5, _return_value
        _return_value = _C5.Result

    def _concurrent_G_a():
        nonlocal _C2, _C3, _C4, a, m, n
        if n == 3:
            a = _C2.Result
        elif m == 3:
            a = _C3.Result
        else:
            a = _C4.Result
        orchestrator._complete('G_a')
    orchestrator._dispatch({_concurrent_G0: [], _concurrent_G1: ['_C0'], _concurrent_G2: ['_C0'], _concurrent_G3: ['G_a'], _concurrent_G4: ['_C5'], _concurrent_G_a: [['_C1', '_C2', '_C3', '_C4']]})
    return _return_value


orchestrator.Return(_program(orchestrator))"""


        result = self.get(source_code)
        print(result)
        self.assertEqual(result, expected.strip())
##########################


if __name__ == "__main__":
    unittest.main()