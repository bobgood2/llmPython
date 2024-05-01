
import ast
from multiprocessing import Value
from tkinter import SEL
from ast_transform import astor
from ast_transform import rewriter

class VerificationVisitor(ast.NodeVisitor):

    # functionDef entry point if arguments != None
    def __init__(self, node, config, arguments=None, level = 0):
        self.arguments = arguments      # arguments to this functionDef, or null
        self.assignments = {}           # all variables assigned to 
        self.statements = []            # all statements without assignments, or if or loops
        self.async_calls = set([])      # all calls to orchestrator functions
        self.names=set([])              # list of symbols used
        self.awaitednames=set([])       # list of symbols used with await
        self.async_names = set([])      # all variables that require await        
        self.nonlocals=set([])            # list of symbols that are nonlocal
        self.initialized=set([])        # list of symbols set to None before anything else
        self.defs = {}                  # nodes of all functions defined
        self.children = {}              # child VerificationVisitor for each function defined
        self.add_tasks = []             # every call to orcgestrator add_tasks is logged here
        self.called_functions= []       # every paramaterless call to a local function is is logged here
        self.config=config
        if level==0:
            self.inLocalFunction=False
            self.visit(node)
            if len(self.defs) != 1:
                raise ValueError("top level requires exactly one function defined for the program")
            funcDefName = next(iter(self.defs.keys()))
            funcDef = self.defs[funcDefName]
            self.children[funcDefName] = VerificationVisitor(funcDef.body, config, funcDef.args, 1)

        elif level==1:
            self.inLocalFunction=False
            for sub in node:
                self.visit(sub)

            for funcDefName in self.defs.keys():
                funcDef = self.defs[funcDefName]
                self.children[funcDefName] = VerificationVisitor(funcDef.body, config, funcDef.args, 2)
        else:
            self.inLocalFunction=True
            for sub in node:
                self.visit(sub)
     
    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            id = node.attr
            if node.attr == rewriter.Rewriter.resultName:
                self.awaitednames.add(node.value.id)
                return
    
        self.generic_visit(node)

    def visit_Await(self, node):
        if isinstance(node.value, ast.Name):
            if self.inLocalFunction:
                if node.value.id not in self.nonlocals:
                    raise ValueError("symbol not nonlocal")
            self.awaitednames.add(node.value.id)
        elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and not node.value.args:
            pass
        else:
            raise ValueError("can only await ast.Name or empty function calls")
    
    def visit_Name(self, node):
        if node.id == rewriter.Rewriter.orchestrator:
            return
        if node.id == "asyncio":
            return
        if node.id == "str":
            return
        if node.id in self.defs:
            return
        if self.inLocalFunction:
            if node.id not in self.nonlocals:
                raise ValueError("symbol not nonlocal")
           
        self.names.add(node.id)
               
    def visit_Nonlocal(self, node):
        if not self.inLocalFunction:
            raise ValueError("nonlocal must be inside function def")
        for n in node.names:
            if n in self.names:
                raise ValueError("nonlocals first")
            if n in self.awaitednames:
                raise ValueError("nonlocals first")
            self.nonlocals.add(n)
            
    def visit_Expr(self, node):
        self.statements.append(node)
        self.statement = node
        self.generic_visit(node)
            
          
    def visit_Assign(self, node):
        self.statement = node
        if isinstance(node.value, ast.Call):
            self.visit_Call(node.value)
            if self.is_orchestrator_call:
                symbol = node.targets[0].id
                self.awaitednames.add(symbol)
                self.assignments[symbol] = node.targets
                return

        if len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            id = node.targets[0].id
            initialized=False
            if isinstance(node.value, ast.Constant):
                if node.value.value==None:
                    id = node.targets[0].id
                    if (id not in self.names):
                        self.initialized.add(id)
                        initialized=True
            if not initialized:
                self.assignments[id] = node.targets
            else:
                return
        else:
            raise ValueError("assignment to tuple")
        self.generic_visit(node)

    def IsTaskCall(self, node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    if self.config.useAsync:
                        if node.func.attr == "create_task" and node.func.value.id=="asyncio":
                            return True
                    else:
                        if node.func.attr == rewriter.Rewriter.taskFunction and node.func.value.id==rewriter.Rewriter.orchestrator:
                            return True
                    
        return False
        
    def visit_Call(self, node):
        self.is_orchestrator_call=False
        isAssignChild= False
        isExprChild= False
        if isinstance(self.statement, ast.Assign):
            if self.IsTaskCall(self.statement.value):
                child = self.statement.value.args[0]
                isAssignChild = child == node

        elif isinstance(self.statement, ast.Expr):
            isExprChild = self.statement.value == node
            
        if (isinstance(node.func, ast.Attribute) 
            and isinstance(node.func.value, ast.Name) 
            and node.func.value.id==rewriter.Rewriter.orchestrator):

            name = node.func.attr
            self.async_calls.add(name)
            
            if not isAssignChild and not isExprChild and name!=rewriter.Rewriter.orchestratorClass and name!=rewriter.Rewriter.taskClass:
                raise ValueError("orchestrator functions must be assigned as task or in expr statements")
            
            if name == rewriter.Rewriter.functionAddTask:
                self.add_tasks.append([node.args[0].id, node.args[1].id])
                return;
            for arg in node.args:
                if not isinstance(arg, ast.Name) and not isinstance(arg, ast.Constant):
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == rewriter.Rewriter.programFunction:
                        # allow orchestrator.Return(_program())
                        pass
                    elif name==rewriter.Rewriter.taskFunction:
                        # Task() is allowed
                        pass
                    else:
                        raise ValueError("orchestrator function arguments must be ast.Name")
            for kw in node.keywords:
                if not isinstance(kw.value, ast.Name) and not isinstance(kw.value, ast.Constant):
                    raise ValueError("orchestrator function arguments must be ast.Name")

            if isAssignChild:
                if len(self.statement.targets)==1:
                    target = self.statement.targets[0]
                    if isinstance(target, ast.Name):
                        self.async_names.add(target.id)
                        self.is_orchestrator_call=True
                    else:
                        raise ValueError("orchestrator values must be set to name")
                else:
                    raise ValueError("orchestrator values cannot be set to tuple")
        elif isinstance(node.func, ast.Name) and not node.args and not node.keywords:
                self.called_functions.append(node.func.id)
                return
        self.generic_visit(node)
            
    def visit_FunctionDef(self, node):
        self.defs[node.name] = node
        if self.inLocalFunction:
            raise ValueError("no recursive function definitions")

    def visit_AsyncFunctionDef(self, node):
        self.defs[node.name] = node
        if self.inLocalFunction:
            raise ValueError("no recursive function definitions")

    def checkawait(self):
        names=set(self.names)                     # list of symbols used
        awaitednames=set(self.awaitednames)       # list of symbols used with await
        async_names = set( self.async_names)      # all variables that require await        
        for childname in self.children:
            child = self.children[childname]
            names |= child.names
            awaitednames |= child.awaitednames
            async_names |= child.async_names
        for name in names:
            if name in async_names:
                raise ValueError("symbol is missing await")
        for name in awaitednames:
            if name not in async_names:
                raise ValueError("symbol should not be awaited")

    def validateAssignment(self, isExpected, expected):
        if (expected in self.assignments.keys()):
            if not isExpected:
                raise ValueError("assignment seen where not expected")
        else:
            if isExpected:
                raise ValueError("assignment not seen where expected")
        
    def validateFunction(self, isExpected, expected):
        if (expected in self.async_calls):
            if not isExpected:
                raise ValueError("function seen where not expected")
        else:
            if isExpected:
                raise ValueError("function not seen where expected")
        

    def validate(self, isExpected, expected):
        for item in expected:
            if isinstance(item, list):
                for sub in item:
                    self.validateFunction(isExpected, sub)
            else:
                self.validateAssignment(isExpected, item)
            
    def validateAll(self, expected):
        for group in expected.keys():
            child = self
            if group!=...:
                child = self.children[group]
            for group2 in expected.keys():
                child2 = self
                if group2!=...:
                    child2 = self.children[group2]
                child2.validate(child==child2, expected[group])

    def validateBase(self, validate):
        child = next(iter(self.children.values()))
        child.checkawait()
        child.validateAll(validate)

class CodeVerification:
    def __init__(self,tree, config, validate):
        self.root = VerificationVisitor(tree, config)
        self.root.validateBase(validate)
        
        
            
            
        
        