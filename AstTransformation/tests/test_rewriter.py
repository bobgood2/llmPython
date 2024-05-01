import unittest

import ast
from ast_transform import astor

from ast_transform import rewriter
from ast_transform import splitter_analyzer
from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from ast_transform import code_verification
from unittest.mock import patch
import io

config = scope_analyzer.Config()
config.awaitableFunctions= ["search_email", "search_teams","search_meetings"]
config.moduleBlackList=None
config.useAsync=False

source_code = """
pass
q=3
a=search_email(q,0)
sum=str(a)+'j'
sum += str(q)
sum2=sum + "q"
b=search_meetings(sum+"a") + search_teams(b=sum2+"b")
c=b
return c
"""


validate={"_concurrent_G0": ["q", "_1", ["search_email"]],
   "_concurrent_G1": ["a", "sum", "sum2", "_2", "_4", "_3", "_5",["search_meetings", "search_teams"]],
   "_concurrent_G2": ["b","c","_return_value"],
   }

class TestRewriterModule(unittest.TestCase):
    def test_split(self):
        self.check(source_code, validate)
        
        
    def check(self, code, validate):
        print(code)
        print()

        tree = ast.parse(code)
            
        analyzer1 = variables_analyzer.Scan(tree, config)
        analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
        analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
        rewrite= rewriter.Scan(tree, analyzer3)
        result = astor.to_source(rewrite).strip()
        print(result)

        with open("C:/repos/llmPython/LLmModule/test.py", 'w') as file:
            file.write(result)  
        verify = code_verification.CodeVerification(rewrite, config, validate)       
        
if __name__ == '__main__':
    unittest.main()