﻿using System;
using IronPython.Hosting;
using Microsoft.Scripting.Hosting;
using static IronPython.Modules._ast;

class Program
{
    static void Main() 
    {
        var code = @" 
pass
q = 3
a = search_email(q, 0)
sum = str(a) + 'j'
sum += str(q)
sum2 = sum + ""q""
b = search_meetings(sum + ""a"") + search_teams(b = sum2 + ""b"")
c = b
Return(c);
"; 
         
        var convert = @"
print 
import ast
from ast_transform import astor

from ast_transform import rewriter
from ast_transform import splitter_analyzer
from ast_transform import dependency_analyzer
from ast_transform import variables_analyzer
from ast_transform import scope_analyzer
from ast_transform import code_verification
tree = ast.parse(code)

config = scope_analyzer.Config()
config.awaitableFunctions= [""search_email"", ""search_teams"",""search_meetings""]
config.moduleBlackList=None
config.useAsync=False
            
analyzer1 = variables_analyzer.Scan(tree, config)
analyzer2 = dependency_analyzer.Scan(tree, analyzer1)
analyzer3 = splitter_analyzer.Scan(tree, analyzer2)
rewrite= rewriter.Scan(tree, analyzer3)
result = astor.to_source(rewrite).strip()
print(result) 
";
        var engine = Python.CreateEngine();
        var scope = engine.CreateScope();

        // Set variables in the scope
        scope.SetVariable("code", code);

        try
        {
            // Execute IronPython code with access to the variables in the scope
            engine.Execute(convert, scope); // Output: 42
        }
        catch (Exception ex)
        {
            Console.WriteLine(ex.ToString()); 
        }  
    }
}
