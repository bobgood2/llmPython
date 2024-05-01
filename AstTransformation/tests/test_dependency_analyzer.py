from tkinter import EXCEPTION
import unittest

import ast
from ast_transform import astor

from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from unittest.mock import patch
import io

awaitable_functions = ["search_email", "search_teams","search_meetings"]

source_code2 = """
q=3
a=search_email(q)
sum=a*3
sum+=q
b=search_email(sum)  or search_teams(sum+1)
return b
"""

expected2="""
q=3
a=search_email(q)
sum=a*3
sum+=q
b=search_email(sum)  or search_teams(sum+1)
return b


C0 = search_email(q)
C1 = search_email(sum)
C2 = search_teams(sum + 1)
C3 = return b
C0 => C1 C2 search_email(q)
C0 search_email
C0 q
C0 C1 C2 q = 3
C0 C1 C2 3
 q
C1 => C3 search_email(sum)
C1 search_email
C1 sum
C1 C2 sum = a * 3
C1 C2 a * 3
C1 C2 a
C1 C2 a = search_email(q)
 a
C1 C2 3
 sum
C1 C2 sum += q
C1 C2 sum
C1 C2 q
C2 => C3 search_teams(sum + 1)
C2 search_teams
C2 sum + 1
C2 sum
C2 1
C3 =>  return b
C3 b
C3 b = search_email(sum) or search_teams(sum + 1)
C3 search_email(sum) or search_teams(sum + 1)
 b"""

source_code = """
a=search_email(q)
x=search_email(a)
return x
"""

expected="""
a=search_email(q)
x=search_email(a)
return x


C0 = search_email(q)
C1 = search_email(a)
C2 = return x
C0 => C1 search_email(q)
C0 search_email
C0 q
C1 => C2 search_email(a)
C1 search_email
C1 a
C1 a = search_email(q)
 a
C2 =>  return x
C2 x
C2 x = search_email(a)
 x"""



def walk(analyzer2: dependency_analyzer.DependencyAnalyzer):
    named = {}
    crit = analyzer2.critical_nodes
    num = 0
    for c in crit:
        named[c]= "C"+str(num)
        num+=1
        try:
            code = astor.to_source(c).strip()
            print(named[c] + " = "+code)
        except Exception:
            pass
    for n in analyzer2.nodelookup.keys():
        nodec = analyzer2.nodelookup[n]
        try:
            code = astor.to_source(n).strip()
            result = ' '.join([named[item] for item in nodec.dependency])
            if n in crit:
                result = named[n]+ " => "+result
            print(result+" "+code)
        except Exception:
            pass
    pass

config = scope_analyzer.Config()
config.awaitableFunctions= ["search_email", "search_teams","search_meetings"]
config.moduleBlackList=None
config.useAsync=False


class TestDependencyAnalyzerModule(unittest.TestCase):
    def test_simple(self):
        result=self.get(source_code)
        self.assertEqual(result, expected.strip())

    def test_parallel(self):
        result=self.get(source_code2)
        print(result)
        self.assertEqual(result, expected2.strip())

    def get(self, code):
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            print(code)
            print()

            tree = ast.parse(code)
            analyzer1 = variables_analyzer.Scan(tree, config)
            analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
            walk(analyzer2)
            result=mock_stdout.getvalue().strip()
            return result
        
if __name__ == '__main__':
    unittest.main()