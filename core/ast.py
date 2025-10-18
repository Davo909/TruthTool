from abc import ABC
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass

@dataclass
class Position:
    line: int
    column: int

class ASTNode(ABC):
    position: Optional[Position] = None

class Formula(ASTNode):
    pass

# =======================
# Propositional AST
# =======================
class Atom(Formula):
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other) -> bool:
        return isinstance(other, Atom) and self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

class Negation(Formula):
    def __init__(self, formula: Formula):
        self.formula = formula
    def __str__(self): return f"~{self.formula}"

class Conjunction(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left, self.right = left, right
    def __str__(self): return f"({self.left} & {self.right})"

class Disjunction(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left, self.right = left, right
    def __str__(self): return f"({self.left} | {self.right})"

class Implication(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left, self.right = left, right
    def __str__(self): return f"({self.left} -> {self.right})"

class Biconditional(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left, self.right = left, right
    def __str__(self): return f"({self.left} <-> {self.right})"

# =======================
# Modal AST
# =======================
class Necessity(Formula):
    def __init__(self, formula: Formula):
        self.formula = formula
    def __str__(self): return f"□{self.formula}"

class Possibility(Formula):
    def __init__(self, formula: Formula):
        self.formula = formula
    def __str__(self): return f"◊{self.formula}"

# =======================
# FOL AST
# =======================
class Term(ABC): ...

class Variable(Term):
    def __init__(self, name: str):
        self.name = name
    def __str__(self): return self.name

class Constant(Term):
    def __init__(self, name: str):
        self.name = name
    def __str__(self): return self.name

class Function(Term):
    def __init__(self, name: str, args: List[Term]):
        self.name, self.args = name, args
    def __str__(self):
        args_str = ", ".join(str(a) for a in self.args)
        return f"{self.name}({args_str})"

class Predicate(Formula):
    def __init__(self, name: str, args: List[Term]):
        self.name, self.args = name, args
    def __str__(self):
        args_str = ", ".join(str(a) for a in self.args)
        return f"{self.name}({args_str})"

class UniversalQuantifier(Formula):
    def __init__(self, variable: str, formula: Formula):
        self.variable, self.formula = variable, formula
    def __str__(self): return f"∀{self.variable} {self.formula}"

class ExistentialQuantifier(Formula):
    def __init__(self, variable: str, formula: Formula):
        self.variable, self.formula = variable, formula
    def __str__(self): return f"∃{self.variable} {self.formula}"

# =======================
# Utilities
# =======================
def get_atoms(formula: Formula) -> set:
    """Atomic propositional letters (for PL truth tables)."""
    atoms = set()
    if isinstance(formula, Atom):
        atoms.add(formula)
    elif isinstance(formula, (Negation, Necessity, Possibility)):
        atoms |= get_atoms(formula.formula)
    elif isinstance(formula, (Conjunction, Disjunction, Implication, Biconditional)):
        atoms |= get_atoms(formula.left) | get_atoms(formula.right)
    elif isinstance(formula, (UniversalQuantifier, ExistentialQuantifier)):
        atoms |= get_atoms(formula.formula)
    elif isinstance(formula, Predicate):
        # treat predicate symbol name as an atom in PL skeletons
        atoms.add(Atom(formula.name))
    return atoms

def get_variables(formula: Formula) -> set:
    vars_ = set()
    if isinstance(formula, Variable):
        vars_.add(formula.name)
    elif isinstance(formula, (Negation, Necessity, Possibility)):
        vars_ |= get_variables(formula.formula)
    elif isinstance(formula, (Conjunction, Disjunction, Implication, Biconditional)):
        vars_ |= get_variables(formula.left) | get_variables(formula.right)
    elif isinstance(formula, (UniversalQuantifier, ExistentialQuantifier)):
        vars_.add(formula.variable)
        vars_ |= get_variables(formula.formula)
    elif isinstance(formula, Predicate):
        for t in formula.args:
            if isinstance(t, Variable):
                vars_.add(t.name)
    return vars_

def get_signature(formula: Formula) -> Dict[str, int]:
    """Predicate signature: name -> arity (for FOL finite model building)."""
    sig: Dict[str, int] = {}
    def visit(f: Formula):
        nonlocal sig
        if isinstance(f, Predicate):
            sig[f.name] = max(sig.get(f.name, 0), len(f.args))
        elif isinstance(f, (Negation, Necessity, Possibility)):
            visit(f.formula)
        elif isinstance(f, (Conjunction, Disjunction, Implication, Biconditional)):
            visit(f.left); visit(f.right)
        elif isinstance(f, (UniversalQuantifier, ExistentialQuantifier)):
            visit(f.formula)
    visit(formula)
    return sig

def has_functions_or_constants(formula: Formula) -> bool:
    found = False
    def visit_term(t: Term):
        nonlocal found
        if isinstance(t, Function):
            found = True
        elif isinstance(t, Constant):
            found = True
        elif isinstance(t, Variable):
            pass
        elif isinstance(t, Function):
            for a in t.args: visit_term(a)

    def visit(f: Formula):
        nonlocal found
        if isinstance(f, Predicate):
            for a in f.args: visit_term(a)
        elif isinstance(f, (Negation, Necessity, Possibility)):
            visit(f.formula)
        elif isinstance(f, (Conjunction, Disjunction, Implication, Biconditional)):
            visit(f.left); visit(f.right)
        elif isinstance(f, (UniversalQuantifier, ExistentialQuantifier)):
            visit(f.formula)

    visit(formula)
    return found
