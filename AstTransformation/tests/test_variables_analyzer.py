from symtable import SymbolTable
import unittest

import ast
from ast_transform import astor_fork
from ast_transform import scope_analyzer
from ast_transform import common
from ast_transform import variables_analyzer
from unittest.mock import patch
import io



def Nodes(list):
    last = list[-1]

    return "#" + str(last.lineno)


attr = [
    common.SymbolTableEntry.ATTR_READ,
    common.SymbolTableEntry.ATTR_WRITE,
    common.SymbolTableEntry.ATTR_READ_WRITE,
    common.SymbolTableEntry.ATTR_DECLARED,
    common.SymbolTableEntry.ATTR_AMBIGUOUS,
]

rename = {
    "read": "r",
    "write": "w",
    "readwrite": "rw",
    "declared": ":",
    "ambiguous": "m",
}


def walk(t, pre=""):
    for name in t.keys():
        v = t[name]
        print(f"{pre}{name}")
        if v.child:
            walk(v.child, pre + ". ")
        if v.redirect:
            print(f"{pre}| redirect")
        if v.notLocal == True:
            print(f"{pre}| notlocal")
        for x in attr:
            if v[x]:
                for y in v[x]:
                    print(f"{pre}| {rename[x]} {Nodes(y)}")


config = common.Config()
config.awaitable_functions = []
config.module_blacklist = None
config.use_async = False


class TestVariablesAnalyzerModule(unittest.TestCase):
    @patch("sys.stdout", new_callable=io.StringIO)
    def check(self,source_code,expected, mock_stdout):
        # Test your function here
        tree = ast.parse(source_code)

        analyzer1 = variables_analyzer.Scan(tree, config)
        walk(analyzer1.symbol_table)
        result = mock_stdout.getvalue().strip()
        self.assertEqual(result, expected.strip())

##############
    def test_ifreuse(self):
        source_code = """
a=None
if n:
    a=search_email()
else:
    a=search_teams()

"""

        expected = """
a
| w #2
| w #4
| w #6
n
| r #3
search_email
| r #4
search_teams
| r #6"""
        self.check(source_code,expected)        
##############
    def test_simple(self):
        source_code = """
a=[search_email(9,0), 2]
b=a[1]
return search_email(b)
"""

        expected = """
a
| r #3
| w #2
search_email
| r #2
| r #4
b
| r #4
| w #3"""
        self.check(source_code,expected)        

#######################
    def test_complex(self):
        source_code = """
m+=3
a.b+=a.m
class MyClass:
    def __init__(self):
        self.x=3

    def my_function(self):
        global m, y, kjj
        y=3
        y1=4
        self.x=4
        return lambda x: x ** y
        
        def mf2():
            nonlocal y1, y2
            y1+=3
            def mf2():
                nonlocal y2
                y1+=3
                y2+=3

    @staticmethod
    def other():
        return False
obj = MyClass()
func = obj.my_function()
print(func(3))
return a,m
"""

        expected = """
m
| r #29
| rw #2
a
| r #3
| r #3
| r #3
| r #29
| m #3
MyClass
. __init__
. x
. | w #6
. | w #12
. my_function
. . m
. . | redirect
. . y
. . | redirect
. . kjj
. . | redirect
. . y1
. . | notlocal
. . | w #11
. . | rw #17
. . lambda
. . . x
. . . | r #13
. . . | r #13
. . . | : #13
. . mf2
. . . y1
. . . | redirect
. . . y2
. . . | redirect
. . . mf2
. . . . y2
. . . . | redirect
. . . . y1
. . . . | rw #20
. . y2
. . | notlocal
. . | rw #21
. other
| r #26
y
| notlocal
| r #13
| w #10
kjj
obj
| r #27
| r #27
| w #26
func
| r #28
| w #27
print
| r #28"""
        self.check(source_code,expected)        
##############

if __name__ == "__main__":
    unittest.main()
