import re
from typing import List, Optional, Tuple
from .ast import *

class ParseError(Exception):
    def __init__(self, message: str, position: Optional[Tuple[int,int]] = None):
        self.message = message
        self.position = position
        super().__init__(message)

class FormulaParser:
    def __init__(self):
        # Order matters (longer first)
        self.tokens = [
            ('BICONDITIONAL', r'<->|↔'),
            ('IMPLIES',       r'->|→'),
            ('NECESSITY',     r'□|\[\]'),
            ('POSSIBILITY',   r'◊|<>'),
            ('FORALL',        r'∀|forall'),
            ('EXISTS',        r'∃|exists'),
            ('NEG',           r'~|!|¬'),
            ('AND',           r'&|∧'),
            ('OR',            r'\||∨'),
            ('LPAREN',        r'\('),
            ('RPAREN',        r'\)'),
            ('COMMA',         r','),
            # Uppercase identifiers (predicates / constants / PL atoms)
            ('UC_ID',         r'[A-Z][A-Za-z0-9_]*'),
            # Lowercase identifiers (variables / functions)
            ('LC_ID',         r'[a-z][A-Za-z0-9_]*'),
            ('SPACE',         r'\s+'),
        ]
        self.token_patterns = [(name, re.compile(pattern)) for name, pattern in self.tokens]
        self._current_logic = 'PL'

    def tokenize(self, text: str) -> List[tuple]:
        tokens = []
        i = 0
        line, col = 1, 1
        while i < len(text):
            matched = False
            for name, pat in self.token_patterns:
                m = pat.match(text, i)
                if m:
                    if name != 'SPACE':
                        tokens.append((name, m.group(), (line, col)))
                    span = m.end() - m.start()
                    i = m.end()
                    col += span
                    matched = True
                    break
            if not matched:
                raise ParseError(f"Unexpected character '{text[i]}'", (line, col))
            if i > 0 and text[i-1] == '\n':
                line += 1; col = 1
        return tokens

    # Public parse entry points
    def parse_propositional(self, text: str) -> Formula:
        self._current_logic = 'PL'
        return self._parse(text)

    def parse_modal(self, text: str) -> Formula:
        self._current_logic = 'MODAL'
        return self._parse(text)

    def parse_fol(self, text: str) -> Formula:
        self._current_logic = 'FOL'
        return self._parse(text)

    # Core expression parser (-> lowest precedence)
    def _parse(self, text: str) -> Formula:
        tokens = [t for t in self.tokenize(text) if t[0] != 'SPACE']
        if not tokens:
            raise ParseError("Empty formula")
        node, rest = self._parse_imp(tokens)
        if rest:
            kind, val, pos = rest[0]
            raise ParseError(f"Unexpected token '{val}'", pos)
        return node

    def _parse_imp(self, ts):
        left, ts = self._parse_or(ts)
        while ts and ts[0][0] in ('IMPLIES', 'BICONDITIONAL'):
            op = ts[0][0]; ts = ts[1:]
            right, ts = self._parse_or(ts)
            left = Implication(left, right) if op == 'IMPLIES' else Biconditional(left, right)
        return left, ts

    def _parse_or(self, ts):
        left, ts = self._parse_and(ts)
        while ts and ts[0][0] == 'OR':
            ts = ts[1:]
            right, ts = self._parse_and(ts)
            left = Disjunction(left, right)
        return left, ts

    def _parse_and(self, ts):
        left, ts = self._parse_prefix(ts)
        while ts and ts[0][0] == 'AND':
            ts = ts[1:]
            right, ts = self._parse_prefix(ts)
            left = Conjunction(left, right)
        return left, ts

    def _parse_prefix(self, ts):
        if not ts: raise ParseError("Unexpected end")
        t0, val, pos = ts[0]
        if t0 == 'NEG':
            sub, rest = self._parse_prefix(ts[1:])
            return Negation(sub), rest
        if t0 == 'NECESSITY':
            sub, rest = self._parse_prefix(ts[1:])
            return Necessity(sub), rest
        if t0 == 'POSSIBILITY':
            sub, rest = self._parse_prefix(ts[1:])
            return Possibility(sub), rest
        if t0 in ('FORALL', 'EXISTS'):
            if len(ts) < 2 or ts[1][0] != 'LC_ID':
                raise ParseError("Expected a variable after quantifier", pos)
            var = ts[1][1]
            body, rest = self._parse_prefix(ts[2:])
            if t0 == 'FORALL':
                return UniversalQuantifier(var, body), rest
            else:
                return ExistentialQuantifier(var, body), rest
        return self._parse_atom(ts)

    def _parse_atom(self, ts):
        if not ts: raise ParseError("Unexpected end")
        t0, val, pos = ts[0]
        if t0 == 'LPAREN':
            inner, rest = self._parse_imp(ts[1:])
            if not rest or rest[0][0] != 'RPAREN':
                raise ParseError("Expected ')'", pos)
            return inner, rest[1:]
        if t0 == 'UC_ID':
            # Disambiguate: UC with '(' => Predicate(...), else: PL Atom (or FOL 0-ary predicate)
            if len(ts) > 1 and ts[1][0] == 'LPAREN':
                name = ts[0][1]
                args, rest = self._parse_term_list(ts[2:])  # after '('
                if not rest or rest[0][0] != 'RPAREN':
                    raise ParseError("Expected ')'", ts[1][2])
                return Predicate(name, args), rest[1:]
            else:
                if self._current_logic == 'PL':
                    return Atom(val), ts[1:]
                else:
                    # interpret UC_ID as 0-ary predicate in FOL/MODAL contexts
                    return Predicate(val, []), ts[1:]
        raise ParseError(f"Unexpected token '{val}'", pos)

    def _parse_term_list(self, ts):
        args: List[Term] = []
        if ts and ts[0][0] == 'RPAREN':
            return args, ts
        while True:
            term, ts = self._parse_term(ts)
            args.append(term)
            if not ts or ts[0][0] != 'COMMA':
                break
            ts = ts[1:]
        return args, ts

    def _parse_term(self, ts):
        if not ts: raise ParseError("Unexpected end in term")
        t0, val, pos = ts[0]
        if t0 == 'LC_ID':
            # function or variable
            if len(ts) > 1 and ts[1][0] == 'LPAREN':
                name = ts[0][1]
                args, rest = self._parse_term_list(ts[2:])
                if not rest or rest[0][0] != 'RPAREN':
                    raise ParseError("Expected ')' after function args", pos)
                return Function(name, args), rest[1:]
            return Variable(val), ts[1:]
        if t0 == 'UC_ID':
            # treat UC as Constant in terms
            return Constant(val), ts[1:]
        raise ParseError(f"Unexpected token '{val}' in term", pos)
