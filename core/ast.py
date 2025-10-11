from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class Position:
    line: int
    column: int

class ASTNode(ABC):
    """Base class for all AST nodes"""
    position: Optional[Position] = None

class Formula(ASTNode):
    """Base class for all formulas"""
    pass

# Propositional Logic AST
class Atom(Formula):
    def __init__(self, name: str):
        self.name = name
    
    def __str__(self):
        return self.name
    
    def __eq__(self, other):
        return isinstance(other, Atom) and self.name == other.name
    
    def __hash__(self):
        return hash(self.name)

class Negation(Formula):
    def __init__(self, formula: Formula):
        self.formula = formula
    
    def __str__(self):
        return f"~{self.formula}"

class Conjunction(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right
    
    def __str__(self):
        return f"({self.left} & {self.right})"

class Disjunction(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right
    
    def __str__(self):
        return f"({self.left} | {self.right})"

class Implication(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right
    
    def __str__(self):
        return f"({self.left} -> {self.right})"

class Biconditional(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right
    
    def __str__(self):
        return f"({self.left} <-> {self.right})"

# Modal Logic AST
class Necessity(Formula):
    def __init__(self, formula: Formula):
        self.formula = formula
    
    def __str__(self):
        return f"□{self.formula}"

class Possibility(Formula):
    def __init__(self, formula: Formula):
        self.formula = formula
    
    def __str__(self):
        return f"◊{self.formula}"

# First-Order Logic AST
class Term(ABC):
    pass

class Variable(Term):
    def __init__(self, name: str):
        self.name = name
    
    def __str__(self):
        return self.name

class Constant(Term):
    def __init__(self, name: str):
        self.name = name
    
    def __str__(self):
        return self.name

class Function(Term):
    def __init__(self, name: str, args: List[Term]):
        self.name = name
        self.args = args
    
    def __str__(self):
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({args_str})"

class Predicate(Formula):
    def __init__(self, name: str, args: List[Term]):
        self.name = name
        self.args = args
    
    def __str__(self):
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({args_str})"

class UniversalQuantifier(Formula):
    def __init__(self, variable: str, formula: Formula):
        self.variable = variable
        self.formula = formula
    
    def __str__(self):
        return f"∀{self.variable} {self.formula}"

class ExistentialQuantifier(Formula):
    def __init__(self, variable: str, formula: Formula):
        self.variable = variable
        self.formula = formula
    
    def __str__(self):
        return f"∃{self.variable} {self.formula}"

# Utility functions
def get_atoms(formula: Formula) -> set:
    """Extract all atomic propositions from a formula"""
    atoms = set()
    
    if isinstance(formula, Atom):
        atoms.add(formula)
    elif isinstance(formula, (Negation, Necessity, Possibility)):
        atoms.update(get_atoms(formula.formula))
    elif isinstance(formula, (Conjunction, Disjunction, Implication, Biconditional)):
        atoms.update(get_atoms(formula.left))
        atoms.update(get_atoms(formula.right))
    elif isinstance(formula, (UniversalQuantifier, ExistentialQuantifier)):
        atoms.update(get_atoms(formula.formula))
    elif isinstance(formula, Predicate):
        # For predicates, we treat them as atomic for propositional purposes
        atoms.add(Atom(formula.name))
    
    return atoms

def get_variables(formula: Formula) -> set:
    """Extract all variables from a formula"""
    variables = set()
    
    if isinstance(formula, Variable):
        variables.add(formula.name)
    elif isinstance(formula, (Negation, Necessity, Possibility)):
        variables.update(get_variables(formula.formula))
    elif isinstance(formula, (Conjunction, Disjunction, Implication, Biconditional)):
        variables.update(get_variables(formula.left))
        variables.update(get_variables(formula.right))
    elif isinstance(formula, (UniversalQuantifier, ExistentialQuantifier)):
        variables.add(formula.variable)
        variables.update(get_variables(formula.formula))
    elif isinstance(formula, Predicate):
        for arg in formula.args:
            variables.update(get_variables(arg))
    elif isinstance(formula, Function):
        for arg in formula.args:
            variables.update(get_variables(arg))
    
    return variables
