"""
knowledge_graph.py  —  C7 Knowledge Graph Scorer
Zero ML. Zero LLM. NetworkX graph traversal.

Usage:
    from knowledge_graph import KnowledgeGraphScorer
    kg = KnowledgeGraphScorer()
    r  = kg.score_answer("OOP", "Polymorphism allows objects of different types...")
    # r = {'score':0.45, 'found_nodes':[...], 'covered_edges':[...],
    #       'missing_key':[...], 'kg_label':'Surface'}
"""

import re
import networkx as nx
from typing import Dict, List

# ── GRAPH EDGES ───────────────────────────────────────────────
GRAPH_EDGES = {
    "OOP": [
        ("OOP","encapsulation","has_pillar"),
        ("OOP","inheritance","has_pillar"),
        ("OOP","polymorphism","has_pillar"),
        ("OOP","abstraction","has_pillar"),
        ("polymorphism","method_overriding","implemented_via"),
        ("polymorphism","method_overloading","implemented_via"),
        ("inheritance","parent_class","involves"),
        ("inheritance","child_class","involves"),
        ("inheritance","code_reuse","enables"),
        ("encapsulation","access_modifier","uses"),
        ("encapsulation","getter_setter","uses"),
        ("abstraction","interface","implemented_via"),
        ("abstraction","abstract_class","implemented_via"),
        ("SOLID","single_responsibility","contains"),
        ("SOLID","open_closed","contains"),
        ("SOLID","liskov_substitution","contains"),
        ("SOLID","interface_segregation","contains"),
        ("SOLID","dependency_inversion","contains"),
        ("design_pattern","singleton","example"),
        ("design_pattern","factory","example"),
        ("design_pattern","observer","example"),
        ("composition","inheritance","alternative_to"),
    ],
    "Python": [
        ("Python","GIL","has_constraint"),
        ("GIL","threading","affects"),
        ("GIL","multiprocessing","workaround"),
        ("decorator","function","wraps"),
        ("decorator","higher_order","is_a"),
        ("generator","yield","uses"),
        ("generator","lazy_evaluation","enables"),
        ("generator","memory_efficiency","provides"),
        ("list_comprehension","for_loop","alternative_to"),
        ("context_manager","with_statement","uses"),
        ("context_manager","resource_cleanup","ensures"),
        ("mutable","list","example"),
        ("mutable","dict","example"),
        ("immutable","tuple","example"),
        ("immutable","string","example"),
        ("closure","inner_function","involves"),
        ("closure","enclosing_scope","captures"),
        ("asyncio","coroutine","uses"),
        ("asyncio","event_loop","runs_on"),
        ("asyncio","await","uses"),
    ],
    "ML": [
        ("ML","supervised","type"),
        ("ML","unsupervised","type"),
        ("ML","reinforcement","type"),
        ("supervised","classification","task"),
        ("supervised","regression","task"),
        ("overfitting","high_variance","causes"),
        ("overfitting","regularization","prevented_by"),
        ("overfitting","dropout","prevented_by"),
        ("overfitting","cross_validation","detected_by"),
        ("bias_variance","underfitting","high_bias_causes"),
        ("bias_variance","overfitting","high_variance_causes"),
        ("gradient_descent","learning_rate","controlled_by"),
        ("gradient_descent","loss_function","minimizes"),
        ("neural_network","backpropagation","trained_by"),
        ("neural_network","activation_function","uses"),
        ("random_forest","decision_tree","ensemble_of"),
        ("random_forest","bagging","uses"),
        ("SVM","hyperplane","finds"),
        ("SVM","kernel_trick","uses"),
        ("precision","true_positive","uses"),
        ("recall","false_negative","considers"),
        ("F1","precision","combines"),
        ("F1","recall","combines"),
    ],
    "DSA": [
        ("array","index","accessed_by"),
        ("array","O1_access","provides"),
        ("linked_list","node","made_of"),
        ("linked_list","pointer","uses"),
        ("stack","LIFO","follows"),
        ("stack","push","operation"),
        ("stack","pop","operation"),
        ("queue","FIFO","follows"),
        ("tree","root","has"),
        ("tree","binary_tree","type"),
        ("binary_search_tree","in_order_sorted","property"),
        ("graph","vertex","has"),
        ("graph","edge","has"),
        ("BFS","queue","uses"),
        ("DFS","stack","uses"),
        ("hash_table","hash_function","uses"),
        ("hash_table","collision","handles"),
        ("dynamic_programming","memoization","technique"),
        ("dynamic_programming","overlapping_subproblems","requires"),
        ("big_O","time_complexity","measures"),
        ("big_O","space_complexity","measures"),
    ],
    "DBMS": [
        ("ACID","atomicity","contains"),
        ("ACID","consistency","contains"),
        ("ACID","isolation","contains"),
        ("ACID","durability","contains"),
        ("normalization","1NF","level"),
        ("normalization","2NF","level"),
        ("normalization","3NF","level"),
        ("normalization","redundancy_reduction","achieves"),
        ("index","B_tree","implemented_as"),
        ("index","faster_lookup","provides"),
        ("primary_key","unique","must_be"),
        ("primary_key","not_null","must_be"),
        ("foreign_key","referential_integrity","enforces"),
        ("transaction","ACID","must_satisfy"),
        ("JOIN","INNER","type"),
        ("JOIN","LEFT","type"),
        ("JOIN","RIGHT","type"),
        ("deadlock","circular_wait","caused_by"),
        ("deadlock","timeout","resolved_by"),
    ],
    "CN": [
        ("OSI","7_layers","has"),
        ("OSI","physical_layer","contains"),
        ("OSI","transport_layer","contains"),
        ("OSI","application_layer","contains"),
        ("TCP","connection_oriented","is"),
        ("TCP","three_way_handshake","uses"),
        ("TCP","reliable","is"),
        ("UDP","connectionless","is"),
        ("UDP","faster","is"),
        ("DNS","domain_to_IP","resolves"),
        ("HTTP","stateless","is"),
        ("HTTPS","TLS","uses"),
        ("HTTPS","encryption","provides"),
        ("IP","IPv4","version"),
        ("IP","IPv6","version"),
        ("subnet","IP_range","defines"),
        ("router","routing_table","uses"),
        ("firewall","packet_filtering","does"),
    ],
    "OS": [
        ("process","PCB","has"),
        ("process","memory_space","has"),
        ("thread","lightweight","is"),
        ("thread","shared_memory","uses"),
        ("deadlock","mutual_exclusion","requires"),
        ("deadlock","hold_and_wait","requires"),
        ("deadlock","no_preemption","requires"),
        ("deadlock","circular_wait","requires"),
        ("virtual_memory","paging","uses"),
        ("virtual_memory","page_fault","can_cause"),
        ("scheduling","FCFS","algorithm"),
        ("scheduling","round_robin","algorithm"),
        ("scheduling","priority","algorithm"),
        ("mutex","mutual_exclusion","ensures"),
        ("semaphore","signaling","used_for"),
    ],
    "System Design": [
        ("CAP","consistency","property"),
        ("CAP","availability","property"),
        ("CAP","partition_tolerance","property"),
        ("load_balancer","horizontal_scaling","enables"),
        ("load_balancer","round_robin","algorithm"),
        ("caching","Redis","tool"),
        ("caching","cache_invalidation","challenge"),
        ("caching","TTL","strategy"),
        ("microservices","API_gateway","uses"),
        ("microservices","service_discovery","needs"),
        ("microservices","monolith","alternative_to"),
        ("database_sharding","horizontal_partition","is"),
        ("CDN","edge_server","uses"),
        ("CDN","latency_reduction","provides"),
        ("message_queue","async","enables"),
        ("message_queue","Kafka","example"),
        ("message_queue","RabbitMQ","example"),
        ("consistent_hashing","virtual_node","uses"),
        ("circuit_breaker","fault_tolerance","provides"),
        ("CQRS","read_model","separates"),
        ("CQRS","write_model","separates"),
    ],
    "HR": [
        ("STAR","situation","step"),
        ("STAR","task","step"),
        ("STAR","action","step"),
        ("STAR","result","step"),
        ("teamwork","communication","requires"),
        ("teamwork","collaboration","requires"),
        ("conflict_resolution","listening","requires"),
        ("conflict_resolution","empathy","requires"),
        ("leadership","delegation","involves"),
        ("leadership","decision_making","involves"),
        ("growth_mindset","feedback","accepts"),
        ("growth_mindset","learning","values"),
    ],
}

# Abbreviation/stem aliases only — full words matched via node name directly
ALIASES = {
    # abbreviations
    "gil":"GIL", "bfs":"BFS", "dfs":"DFS", "osi":"OSI",
    "tcp":"TCP", "udp":"UDP", "dns":"DNS", "cdn":"CDN",
    "ttl":"TTL", "cqrs":"CQRS", "acid":"ACID",
    "svm":"SVM", "f1 score":"F1", "f1-score":"F1",
    "1nf":"1NF", "2nf":"2NF", "3nf":"3NF",
    "pcb":"PCB", "fcfs":"FCFS",
    # stems / common variations
    "overfit":"overfitting", "underfit":"underfitting",
    "regulariz":"regularization", "normaliz":"normalization",
    "backprop":"backpropagation",
    "hash map":"hash_table", "hashmap":"hash_table",
    "linked list":"linked_list", "binary search tree":"binary_search_tree",
    "dynamic programming":"dynamic_programming",
    "big o":"big_O", "time complex":"big_O",
    "list comp":"list_comprehension",
    "context manager":"context_manager",
    "design pattern":"design_pattern",
    "load balanc":"load_balancer",
    "message queue":"message_queue",
    "consistent hash":"consistent_hashing",
    "circuit breaker":"circuit_breaker",
    "random forest":"random_forest",
    "decision tree":"decision_tree",
    "neural network":"neural_network",
    "gradient descent":"gradient_descent",
    "learning rate":"learning_rate",
    "loss function":"loss_function",
    "activation function":"activation_function",
    "kernel trick":"kernel_trick",
    "cross valid":"cross_validation",
    "bias variance":"bias_variance",
    "primary key":"primary_key",
    "foreign key":"foreign_key",
    "b tree":"B_tree", "b-tree":"B_tree",
    "referential integrity":"referential_integrity",
    "three way handshake":"three_way_handshake",
    "three-way handshake":"three_way_handshake",
    "virtual memory":"virtual_memory",
    "page fault":"page_fault",
    "round robin":"round_robin",
    "horizontal scaling":"horizontal_scaling",
    "cache invalidation":"cache_invalidation",
    "api gateway":"API_gateway",
    "service discovery":"service_discovery",
    "database sharding":"database_sharding",
    "event sourcing":"event_sourcing",
    "star method":"STAR", "star framework":"STAR",
    "conflict resolution":"conflict_resolution",
    "growth mindset":"growth_mindset",
    "open closed":"open_closed",
    "single responsibility":"single_responsibility",
    "dependency inversion":"dependency_inversion",
    "interface segregation":"interface_segregation",
    "liskov":"liskov_substitution",
    "getter setter":"getter_setter",
    "abstract class":"abstract_class",
    "access modifier":"access_modifier",
    "code reuse":"code_reuse",
    "method overrid":"method_overriding",
    "method overload":"method_overloading",
    "parent class":"parent_class",
    "child class":"child_class",
    "inner function":"inner_function",
    "event loop":"event_loop",
    "lazy eval":"lazy_evaluation",
    "memory effici":"memory_efficiency",
    "resource cleanup":"resource_cleanup",
    "enclosing scope":"enclosing_scope",
    "higher order":"higher_order",
}


class KnowledgeGraphScorer:

    def __init__(self):
        self.graphs: Dict[str, nx.DiGraph] = {}
        for skill, edges in GRAPH_EDGES.items():
            G = nx.DiGraph()
            for src, dst, rel in edges:
                G.add_edge(src, dst, relation=rel)
            self.graphs[skill] = G

    def _find_nodes(self, text: str) -> set:
        """Match graph nodes in text via direct name match + aliases."""
        t = text.lower()
        found = set()

        # 1. Direct node name match (underscores → spaces)
        for skill_graph in self.graphs.values():
            for node in skill_graph.nodes():
                name = node.replace('_', ' ').lower()
                if name in t:
                    found.add(node)

        # 2. Alias match for abbreviations and stems
        for alias, node in sorted(ALIASES.items(), key=lambda x: -len(x[0])):
            if alias.lower() in t:
                found.add(node)

        return found

    def score_answer(self, skill: str, answer: str) -> dict:
        G = self.graphs.get(skill)
        if G is None or not answer.strip():
            return {'score':0.0,'found_nodes':[],'covered_edges':[],
                    'missing_key':[],'kg_label':'Minimal'}

        found = self._find_nodes(answer)

        covered = [
            f"{s}→{d}"
            for s, d in G.edges()
            if s in found and d in found
        ]

        total  = G.number_of_edges()
        score  = len(covered) / total if total > 0 else 0.0

        degree  = dict(G.degree())
        missing = sorted(
            [n for n in G.nodes() if n not in found],
            key=lambda n: -degree.get(n, 0)
        )[:3]

        label = 'Deep' if score >= 0.35 else ('Surface' if score >= 0.12 else 'Minimal')

        return {
            'score':         round(score, 4),
            'found_nodes':   sorted(found),
            'covered_edges': covered,
            'missing_key':   [m.replace('_',' ') for m in missing],
            'kg_label':      label,
        }

    def get_graph_stats(self) -> dict:
        return {s: {'nodes': G.number_of_nodes(), 'edges': G.number_of_edges()}
                for s, G in self.graphs.items()}


if __name__ == '__main__':
    kg = KnowledgeGraphScorer()

    print("Graph stats:")
    for s, st in kg.get_graph_stats().items():
        print(f"  {s:<16} nodes={st['nodes']:>3}  edges={st['edges']:>3}")

    tests = [
        ("OOP",
         "OOP has four pillars: encapsulation hides data using private access modifiers, "
         "inheritance enables code reuse through parent and child classes, polymorphism "
         "allows method overriding, and abstraction uses interfaces and abstract classes.",
         "Strong OOP"),
        ("OOP", "OOP is about classes and objects.", "Weak OOP"),
        ("ML",
         "The bias-variance tradeoff: high bias causes underfitting and high variance causes "
         "overfitting. Cross-validation detects overfitting. Regularization and dropout prevent it. "
         "Gradient descent minimizes the loss function with a learning rate.",
         "Strong ML"),
        ("System Design",
         "CAP theorem: consistency, availability, partition tolerance. Load balancers use "
         "round robin for horizontal scaling. Redis caching with TTL-based cache invalidation. "
         "Microservices use an API gateway and service discovery.",
         "Strong SD"),
        ("Python",
         "The GIL prevents threading parallelism so we use multiprocessing. "
         "Decorators wrap functions. Generators use yield for lazy evaluation and memory efficiency. "
         "Context managers with the with statement ensure resource cleanup.",
         "Strong Python"),
        ("DSA",
         "Binary search tree has in-order sorted property. BFS uses a queue. DFS uses a stack. "
         "Hash table uses a hash function and handles collision. "
         "Dynamic programming uses memoization for overlapping subproblems. Big O measures time complexity.",
         "Strong DSA"),
    ]

    print("\nTest results:")
    for skill, ans, label in tests:
        r = kg.score_answer(skill, ans)
        print(f"\n  [{label}]  score={r['score']:.3f} ({r['kg_label']})")
        print(f"  Found: {r['found_nodes']}")
        print(f"  Edges: {r['covered_edges'][:5]}{'...' if len(r['covered_edges'])>5 else ''}")
        print(f"  Missing: {r['missing_key']}")
