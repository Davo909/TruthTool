import re
from typing import List, Optional, Union
from .ast import *

class ParseError(Exception):
    def __init__(self, message: str, position: Optional[tuple] = None):
        self.message = message
        self.position = position
        super().__init__(message)

class FormulaParser:
    def __init__(self):
        # Token patterns (order matters - longer patterns first)
        self.tokens = [
            ('BICONDITIONAL', r'<->'),
            ('IMPLICATION', r'->'),
            ('NECESSITY', r'□|\[\]'),
            ('POSSIBILITY', r'◊|<>'),
            ('UNIVERSAL', r'∀|forall|forall'),
            ('EXISTENTIAL', r'∃|exists|exists'),
            ('NEGATION', r'~|!|¬'),
            ('CONJUNCTION', r'&|∧'),
            ('DISJUNCTION', r'\|'),
            ('LPAREN', r'\('),
            ('RPAREN', r'\)'),
            ('COMMA', r','),
            ('CONSTANT', r'[A-Z][A-Za-z0-9_]*'),
            ('PREDICATE', r'[A-Z][A-Za-z0-9_]*'),
            ('FUNCTION', r'[a-z][A-Za-z0-9_]+'),
            ('VARIABLE', r'[a-z]'),
            ('WHITESPACE', r'\s+'),
        ]
        
        # Compile regex patterns
        self.token_patterns = [(name, re.compile(pattern)) for name, pattern in self.tokens]
    
    def tokenize(self, text: str) -> List[tuple]:
        """Tokenize input text"""
        tokens = []
        position = 0
        line = 1
        col = 1
        
        while position < len(text):
            matched = False
            for token_name, pattern in self.token_patterns:
                match = pattern.match(text, position)
                if match:
                    if token_name != 'WHITESPACE':
                        tokens.append((token_name, match.group(), (line, col)))
                    position = match.end()
                    col += match.end() - match.start()
                    matched = True
                    break
            
            if not matched:
                raise ParseError(f"Unexpected character '{text[position]}' at position {position}")
            
            if text[position-1] == '\n':
                line += 1
                col = 1
        
        return tokens
    
    def parse_propositional(self, text: str) -> Formula:
        """Parse propositional logic formula"""
        self._current_logic = 'PL'
        tokens = self.tokenize(text)
        tokens = [t for t in tokens if t[0] != 'WHITESPACE']  # Remove whitespace
        
        if not tokens:
            raise ParseError("Empty formula")
        
        formula, remaining = self._parse_implication(tokens)
        if remaining:
            raise ParseError(f"Unexpected token '{remaining[0][1]}' at position {remaining[0][2]}")
        
        return formula
    
    def parse_modal(self, text: str) -> Formula:
        """Parse modal logic formula"""
        self._current_logic = 'MODAL'
        tokens = self.tokenize(text)
        tokens = [t for t in tokens if t[0] != 'WHITESPACE']
        
        if not tokens:
            raise ParseError("Empty formula")
        
        formula, remaining = self._parse_implication(tokens)
        if remaining:
            raise ParseError(f"Unexpected token '{remaining[0][1]}' at position {remaining[0][2]}")
        
        return formula
    
    def parse_fol(self, text: str) -> Formula:
        """Parse first-order logic formula"""
        self._current_logic = 'FOL'
        tokens = self.tokenize(text)
        tokens = [t for t in tokens if t[0] != 'WHITESPACE']
        
        if not tokens:
            raise ParseError("Empty formula")
        
        formula, remaining = self._parse_implication(tokens)
        if remaining:
            raise ParseError(f"Unexpected token '{remaining[0][1]}' at position {remaining[0][2]}")
        
        return formula
    
    def _parse_implication(self, tokens: List[tuple]) -> tuple:
        """Parse implication and biconditional (lowest precedence)"""
        left, remaining = self._parse_disjunction(tokens)
        
        while remaining and remaining[0][0] in ['IMPLICATION', 'BICONDITIONAL']:
            op = remaining[0][0]
            remaining = remaining[1:]
            right, remaining = self._parse_disjunction(remaining)
            
            if op == 'IMPLICATION':
                left = Implication(left, right)
            else:  # BICONDITIONAL
                left = Biconditional(left, right)
        
        return left, remaining
    
    def _parse_disjunction(self, tokens: List[tuple]) -> tuple:
        """Parse disjunction"""
        left, remaining = self._parse_conjunction(tokens)
        
        while remaining and remaining[0][0] == 'DISJUNCTION':
            remaining = remaining[1:]
            right, remaining = self._parse_conjunction(remaining)
            left = Disjunction(left, right)
        
        return left, remaining
    
    def _parse_conjunction(self, tokens: List[tuple]) -> tuple:
        """Parse conjunction"""
        left, remaining = self._parse_negation(tokens)
        
        while remaining and remaining[0][0] == 'CONJUNCTION':
            remaining = remaining[1:]
            right, remaining = self._parse_negation(remaining)
            left = Conjunction(left, right)
        
        return left, remaining
    
    def _parse_negation(self, tokens: List[tuple]) -> tuple:
        """Parse negation and modal operators"""
        if not tokens:
            raise ParseError("Unexpected end of input")
        
        if tokens[0][0] == 'NEGATION':
            remaining = tokens[1:]
            formula, remaining = self._parse_negation(remaining)
            return Negation(formula), remaining
        
        elif tokens[0][0] == 'NECESSITY':
            remaining = tokens[1:]
            formula, remaining = self._parse_negation(remaining)
            return Necessity(formula), remaining
        
        elif tokens[0][0] == 'POSSIBILITY':
            remaining = tokens[1:]
            formula, remaining = self._parse_negation(remaining)
            return Possibility(formula), remaining
        
        elif tokens[0][0] == 'UNIVERSAL':
            if len(tokens) < 2:
                raise ParseError("Expected variable after universal quantifier")
            variable = tokens[1][1]
            remaining = tokens[2:]
            formula, remaining = self._parse_implication(remaining)
            return UniversalQuantifier(variable, formula), remaining
        
        elif tokens[0][0] == 'EXISTENTIAL':
            if len(tokens) < 2:
                raise ParseError("Expected variable after existential quantifier")
            variable = tokens[1][1]
            remaining = tokens[2:]
            formula, remaining = self._parse_implication(remaining)
            return ExistentialQuantifier(variable, formula), remaining
        
        else:
            return self._parse_atom(tokens)
    
    def _parse_atom(self, tokens: List[tuple]) -> tuple:
        """Parse atomic formulas and parenthesized expressions"""
        if not tokens:
            raise ParseError("Unexpected end of input")
        
        if tokens[0][0] == 'LPAREN':
            remaining = tokens[1:]
            formula, remaining = self._parse_implication(remaining)
            if not remaining or remaining[0][0] != 'RPAREN':
                raise ParseError("Expected closing parenthesis")
            return formula, remaining[1:]
        
        elif tokens[0][0] == 'CONSTANT':
            # Check if this is actually a predicate with arguments
            if len(tokens) > 1 and tokens[1][0] == 'LPAREN':
                # This is a predicate, not a constant
                pred_name = tokens[0][1]
                remaining = tokens[1:]
                
                # Predicate with arguments
                remaining = remaining[1:]  # Skip '('
                args = []
                
                if remaining and remaining[0][0] != 'RPAREN':
                    while True:
                        arg, remaining = self._parse_term(remaining)
                        args.append(arg)
                        
                        if not remaining or remaining[0][0] != 'COMMA':
                            break
                        remaining = remaining[1:]  # Skip ','
                
                if not remaining or remaining[0][0] != 'RPAREN':
                    raise ParseError("Expected closing parenthesis")
                remaining = remaining[1:]
                
                return Predicate(pred_name, args), remaining
            else:
                # For propositional logic, treat single letters as atoms
                # For FOL, treat them as constants
                if hasattr(self, '_current_logic') and self._current_logic == 'PL':
                    return Atom(tokens[0][1]), tokens[1:]
                else:
                    return Constant(tokens[0][1]), tokens[1:]
        
        elif tokens[0][0] == 'PREDICATE':
            pred_name = tokens[0][1]
            remaining = tokens[1:]
            
            if remaining and remaining[0][0] == 'LPAREN':
                # Predicate with arguments
                remaining = remaining[1:]  # Skip '('
                args = []
                
                if remaining and remaining[0][0] != 'RPAREN':
                    while True:
                        arg, remaining = self._parse_term(remaining)
                        args.append(arg)
                        
                        if not remaining or remaining[0][0] != 'COMMA':
                            break
                        remaining = remaining[1:]  # Skip ','
                
                if not remaining or remaining[0][0] != 'RPAREN':
                    raise ParseError("Expected closing parenthesis")
                remaining = remaining[1:]
                
                return Predicate(pred_name, args), remaining
            else:
                # Predicate without arguments (propositional atom)
                return Atom(pred_name), remaining
        
        else:
            raise ParseError(f"Unexpected token '{tokens[0][1]}' at position {tokens[0][2]}")
    
    def _parse_term(self, tokens: List[tuple]) -> tuple:
        """Parse terms (variables, constants, functions)"""
        if not tokens:
            raise ParseError("Unexpected end of input")
        
        if tokens[0][0] == 'VARIABLE':
            return Variable(tokens[0][1]), tokens[1:]
        
        elif tokens[0][0] == 'CONSTANT':
            return Constant(tokens[0][1]), tokens[1:]
        
        elif tokens[0][0] == 'FUNCTION':
            func_name = tokens[0][1]
            remaining = tokens[1:]
            
            if not remaining or remaining[0][0] != 'LPAREN':
                raise ParseError("Expected opening parenthesis after function")
            
            remaining = remaining[1:]  # Skip '('
            args = []
            
            if remaining and remaining[0][0] != 'RPAREN':
                while True:
                    arg, remaining = self._parse_term(remaining)
                    args.append(arg)
                    
                    if not remaining or remaining[0][0] != 'COMMA':
                        break
                    remaining = remaining[1:]  # Skip ','
            
            if not remaining or remaining[0][0] != 'RPAREN':
                raise ParseError("Expected closing parenthesis")
            remaining = remaining[1:]
            
            return Function(func_name, args), remaining
        
        else:
            raise ParseError(f"Unexpected token '{tokens[0][1]}' in term at position {tokens[0][2]}")
