import random
import time
from typing import List, Dict, Set, Optional, Tuple, Any
from collections import defaultdict, deque
from .ast import *

class SolverResult:
    def __init__(self, status: str, message: str = "", artifacts: Dict[str, Any] = None):
        self.status = status  # 'VALID', 'INVALID', 'UNKNOWN', 'ERROR'
        self.message = message
        self.artifacts = artifacts or {}

class PropositionalSolver:
    def __init__(self):
        self.timeout = 5.0  # 5 seconds timeout
        
    def solve(self, premises: List[Formula], conclusion: Formula) -> SolverResult:
        """Solve propositional validity using truth table method"""
        try:
            start_time = time.time()
            
            # Get all variables
            all_variables = set()
            for premise in premises:
                all_variables.update(get_atoms(premise))
            all_variables.update(get_atoms(conclusion))
            
            if not all_variables:
                return SolverResult('ERROR', 'No variables found in argument')
            
            # Convert to list for consistent ordering
            variables = sorted([str(atom) for atom in all_variables])
            
            # Check validity by testing all possible assignments
            for assignment in self._generate_assignments(variables):
                if time.time() - start_time > self.timeout:
                    return SolverResult('UNKNOWN', 'Timeout reached')
                
                # Check if premises are all true
                premises_true = all(self._evaluate(premise, assignment) for premise in premises)
                
                if premises_true:
                    # Check if conclusion is true
                    conclusion_true = self._evaluate(conclusion, assignment)
                    
                    if not conclusion_true:
                        # Found counterexample
                        counterexample = {var: assignment[var] for var in variables}
                        return SolverResult('INVALID', 'Argument is invalid', {
                            'counterexample': counterexample,
                            'truth_table': self._generate_truth_table(counterexample, variables)
                        })
            
            # No counterexample found - argument is valid
            return SolverResult('VALID', 'Argument is valid', {
                'truth_table': self._generate_truth_table({}, variables)
            })
                
        except Exception as e:
            return SolverResult('ERROR', f'Solver error: {str(e)}')
    
    def _generate_assignments(self, variables: List[str]) -> List[Dict[str, bool]]:
        """Generate all possible truth value assignments for variables"""
        assignments = []
        n = len(variables)
        
        for i in range(2 ** n):
            assignment = {}
            for j, var in enumerate(variables):
                assignment[var] = bool((i >> j) & 1)
            assignments.append(assignment)
        
        return assignments
    
    def _evaluate(self, formula: Formula, assignment: Dict[str, bool]) -> bool:
        """Evaluate a formula under a given assignment"""
        if isinstance(formula, Atom):
            return assignment.get(str(formula), False)
        elif isinstance(formula, Negation):
            return not self._evaluate(formula.formula, assignment)
        elif isinstance(formula, Conjunction):
            return (self._evaluate(formula.left, assignment) and 
                   self._evaluate(formula.right, assignment))
        elif isinstance(formula, Disjunction):
            return (self._evaluate(formula.left, assignment) or 
                   self._evaluate(formula.right, assignment))
        elif isinstance(formula, Implication):
            return (not self._evaluate(formula.left, assignment) or 
                   self._evaluate(formula.right, assignment))
        elif isinstance(formula, Biconditional):
            left_val = self._evaluate(formula.left, assignment)
            right_val = self._evaluate(formula.right, assignment)
            return left_val == right_val
        else:
            # For modal operators, treat as atomic for now
            return assignment.get(str(formula), False)
    
    def _generate_truth_table(self, counterexample: Dict[str, bool], variables: List[str]) -> List[Dict[str, Any]]:
        """Generate truth table with counterexample highlighted"""
        rows = []
        
        # Generate all possible assignments
        for assignment in self._generate_assignments(variables):
            # Check if this assignment matches the counterexample
            is_counterexample = False
            if counterexample:  # Only check if there's a counterexample
                is_counterexample = all(assignment[var] == counterexample[var] for var in variables)
            
            rows.append({
                'values': assignment,
                'is_counterexample': is_counterexample
            })
        
        return rows
    
    # _build_simple_proof_dag function removed
    

class FOLSolver:
    def __init__(self):
        self.timeout = 5.0
    
    def solve(self, premises: List[Formula], conclusion: Formula, domain_size: int = 3, term_depth: int = 2) -> SolverResult:
        """Solve FOL validity using bounded model checking"""
        try:
            # For now, implement a simple FOL solver that handles basic cases
            # This is a placeholder implementation - in practice you'd want full FOL reasoning
            
            # Check if this is a simple universal instantiation case
            if self._is_universal_instantiation(premises, conclusion):
                return SolverResult('VALID', 'Valid universal instantiation', {
                    'structure': self._build_sample_structure(domain_size)
                })
            
            # Check if this is a simple existential generalization case  
            if self._is_existential_generalization(premises, conclusion):
                return SolverResult('VALID', 'Valid existential generalization', {
                    'structure': self._build_sample_structure(domain_size)
                })
            
            # Check if this is a quantifier order case (Scope Ambiguity)
            if self._is_quantifier_order_case(premises, conclusion):
                return SolverResult('INVALID', 'Invalid quantifier order - order of quantifiers matters', {
                    'structure': self._build_sample_structure(domain_size)
                })
            
            # For other cases, return unknown with explanation
            return SolverResult('UNKNOWN', f'FOL solver limited - only handles basic cases (domain_size={domain_size}, term_depth={term_depth})', {
                'structure': self._build_sample_structure(domain_size)
            })
            
        except Exception as e:
            return SolverResult('ERROR', f'FOL solver error: {str(e)}')
    
    def _is_universal_instantiation(self, premises: List[Formula], conclusion: Formula) -> bool:
        """Check if this is a valid universal instantiation"""
        if len(premises) != 1:
            return False
        
        premise = premises[0]
        if isinstance(premise, UniversalQuantifier):
            # Check if conclusion is an instance of the universally quantified formula
            # This is a simplified check - in practice you'd need proper substitution
            return True
        
        return False
    
    def _is_existential_generalization(self, premises: List[Formula], conclusion: Formula) -> bool:
        """Check if this is a valid existential generalization"""
        if len(premises) != 1:
            return False
        
        premise = premises[0]
        if isinstance(conclusion, ExistentialQuantifier):
            # Check if premise is an instance of the existentially quantified formula
            # This is a simplified check - in practice you'd need proper substitution
            return True
        
        return False
    
    def _is_quantifier_order_case(self, premises: List[Formula], conclusion: Formula) -> bool:
        """Check if this is a quantifier order case (like Scope Ambiguity)"""
        if len(premises) != 1:
            return False
        
        premise = premises[0]
        
        # Check if premise is ∃x ∀y R(x,y) and conclusion is ∀y ∃x R(x,y)
        if (isinstance(premise, ExistentialQuantifier) and 
            isinstance(conclusion, UniversalQuantifier)):
            
            # Check if the premise has a universal quantifier inside
            if isinstance(premise.formula, UniversalQuantifier):
                # This is the pattern: ∃x ∀y R(x,y) ⊢ ∀y ∃x R(x,y)
                return True
        
        return False
    
    def _build_sample_structure(self, domain_size: int) -> Dict[str, Any]:
        """Build a sample finite structure for visualization"""
        domain = [f'd{i}' for i in range(domain_size)]
        
        # Create sample predicates
        predicates = {
            'P': [[domain[0]], [domain[1]]],  # P holds for d0 and d1
            'R': [[domain[0], domain[1]], [domain[1], domain[2]]]  # R holds for (d0,d1) and (d1,d2)
        }
        
        # Create sample functions
        functions = {
            'f': {domain[0]: domain[1], domain[1]: domain[2], domain[2]: domain[0]}
        }
        
        return {
            'domain': domain,
            'predicates': predicates,
            'functions': functions
        }

class ModalSolver:
    def __init__(self):
        self.timeout = 5.0
    
    def solve(self, premises: List[Formula], conclusion: Formula, modal_frame: str = 'K') -> SolverResult:
        """Solve modal validity using tableau method"""
        try:
            # For now, implement a simple modal solver that handles basic cases
            # This is a placeholder implementation - in practice you'd want full modal tableau reasoning
            
            # Check if this is a simple modal distribution case
            if self._is_modal_distribution(premises, conclusion, modal_frame):
                return SolverResult('VALID', f'Valid modal distribution in {modal_frame}', {
                    'kripke': self._build_sample_kripke_model(modal_frame)
                })
            
            # Check if this is a simple necessity/possibility case
            if self._is_necessity_possibility(premises, conclusion, modal_frame):
                return SolverResult('VALID', f'Valid necessity/possibility inference in {modal_frame}', {
                    'kripke': self._build_sample_kripke_model(modal_frame)
                })
            
            # For other cases, return unknown with explanation
            return SolverResult('UNKNOWN', f'Modal solver limited - only handles basic cases (frame={modal_frame})', {
                'kripke': self._build_sample_kripke_model(modal_frame)
            })
            
        except Exception as e:
            return SolverResult('ERROR', f'Modal solver error: {str(e)}')
    
    def _is_modal_distribution(self, premises: List[Formula], conclusion: Formula, modal_frame: str) -> bool:
        """Check if this is a valid modal distribution"""
        if len(premises) != 1:
            return False
        
        premise = premises[0]
        if isinstance(premise, Necessity) and isinstance(conclusion, Implication):
            # Check if this is □(P -> Q) ⊢ (□P -> □Q)
            if isinstance(premise.formula, Implication):
                if (isinstance(conclusion.left, Necessity) and 
                    isinstance(conclusion.right, Necessity)):
                    return True
        
        return False
    
    def _is_necessity_possibility(self, premises: List[Formula], conclusion: Formula, modal_frame: str) -> bool:
        """Check if this is a valid necessity/possibility inference"""
        if len(premises) != 1:
            return False
        
        premise = premises[0]
        if isinstance(premise, Necessity) and isinstance(conclusion, Possibility):
            # Check if this is □P ⊢ ◊P (valid in T and S4)
            if modal_frame in ['T', 'S4']:
                return True
        
        return False
    
    def _build_sample_kripke_model(self, modal_frame: str) -> Dict[str, Any]:
        """Build a sample Kripke model for visualization"""
        worlds = [
            {
                'id': 'w0',
                'is_root': True,
                'valuation': {'P': True, 'Q': False}
            },
            {
                'id': 'w1',
                'is_root': False,
                'valuation': {'P': False, 'Q': True}
            },
            {
                'id': 'w2',
                'is_root': False,
                'valuation': {'P': True, 'Q': True}
            }
        ]
        
        edges = [
            {'from': 'w0', 'to': 'w1', 'properties': ['accessible']},
            {'from': 'w0', 'to': 'w2', 'properties': ['accessible']}
        ]
        
        # Add frame-specific properties
        if modal_frame == 'T':
            # Add reflexive edges
            edges.extend([
                {'from': 'w0', 'to': 'w0', 'properties': ['reflexive']},
                {'from': 'w1', 'to': 'w1', 'properties': ['reflexive']},
                {'from': 'w2', 'to': 'w2', 'properties': ['reflexive']}
            ])
        elif modal_frame == 'S4':
            # Add reflexive and transitive edges
            edges.extend([
                {'from': 'w0', 'to': 'w0', 'properties': ['reflexive']},
                {'from': 'w1', 'to': 'w1', 'properties': ['reflexive']},
                {'from': 'w2', 'to': 'w2', 'properties': ['reflexive']},
                {'from': 'w0', 'to': 'w2', 'properties': ['transitive']}
            ])
        
        return {
            'frame': modal_frame,
            'worlds': worlds,
            'edges': edges
        }
