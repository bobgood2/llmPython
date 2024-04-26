import ast
from . import Util
from . import scope_analyzer

class CriticalNodeDepenencyGroup():
    def __init__(self):
        self.node_dependencies=[]
        self.group_dependencies=[]
        self.recursive_group_dependencies=[]
        self.grouped_critical_nodes=[]
        self.name=""
    
    def recursive_set(self, node):
        if self != node:
            self.recursive_group_dependencies.append(node)
        for child in node.group_dependencies:
            self.recursive_set(child)

class SplitterAnalyzer(scope_analyzer.ScopeAnalyzer):
    def __init__(self, copy):
        super().__init__(copy) 
        self.critical_dependency_groups = []
        self.critical_node_to_group = {}
        
    def create_critical_dependency_groups(self):
        groups={}
        for critical_node in self.critical_nodes:
            groups[critical_node]=CriticalNodeDepenencyGroup()
        for critical_node in self.critical_nodes:
            nodec = self.nodelookup[critical_node]
            for dependent in nodec.dependency:
                groups[dependent].node_dependencies.append(critical_node)
            groups[critical_node].grouped_critical_nodes.append(critical_node)
 
        # group multiple critical nodes if they share the same dependency
        grouped_list = []
        for critical_node in self.critical_nodes:
            item = groups[critical_node]
            ingroup=None
            for item2 in grouped_list:
                if (item.node_dependencies == item2.node_dependencies):
                    ingroup=item2
                    break
                
            if ingroup:
                ingroup.grouped_critical_nodes.append(critical_node)
                self.critical_node_to_group[critical_node] = ingroup
            else:
                item.name = "G"+str(len(grouped_list))
                grouped_list.append(item) 
                self.critical_node_to_group[critical_node] = item
                
        for group in grouped_list:
            for node_dependency in group.node_dependencies:
                group_dependency = self.critical_node_to_group[node_dependency]
                if group_dependency not in group.group_dependencies:
                    group.group_dependencies.append(group_dependency)
                    
        for group in grouped_list:
            group.recursive_set(group)
                
        self.critical_dependency_groups = grouped_list                   
        
    
    def assign_nodes_tocreate_critical_dependency_groups(self):
        for node in self.nodelookup.keys():
            nodec = self.nodelookup[node]
            groups = []
            for c in nodec.dependency:
                g = self.critical_node_to_group[c]
                if g not in groups:
                    groups.append(g)
                    
            trimmed_groups = []
            for g in groups:
                s = ' '.join([item.name for item in g.recursive_group_dependencies])
                isCovered=False
                for g2 in groups:
                    if g2 != g and g2 in g.recursive_group_dependencies:
                        isCovered = True
                if not isCovered:
                    trimmed_groups.append(g)

            if len(trimmed_groups)>1:
                raise ValueError

            nodec.concurrency_groups = trimmed_groups
            
 
def Scan(tree, parent=None):
    analyzer = SplitterAnalyzer(parent)
    analyzer.create_critical_dependency_groups()
    analyzer.assign_nodes_tocreate_critical_dependency_groups()
    return analyzer

