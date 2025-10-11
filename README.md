# TruthTool - Proof + Countermodel Studio

A browser-based studio that decides arguments by either constructing proofs or exhibiting countermodels across **propositional**, **bounded first-order**, and **modal (K/T/S4)** logics. Built with Python Flask backend and HTML/CSS/JavaScript frontend.

## Features

### What users can do

* **Write arguments** in a compact formal syntax:
  * Propositional: `~ ! ¬`, `& ∧`, `| ∨`, `->`, `<->`, with parentheses
  * First-order: predicates `P(x)`, functions `f(x)`, constants `a`, quantifiers `∀x`, `∃y`
  * Modal: `□φ`, `◊φ` (or `[]`, `<>`), with logic selector K/T/S4

* **Validate** `Γ ⟹ C` (premises ⇒ conclusion). The system:
  1. Tries to prove validity (truth table method for propositional)
  2. Else finds a countermodel (truth assignment)
  3. Else reports "unknown within bounds/time" with a clear explanation

* **Explore artifacts**:
  * **Truth tables** (PL) with row highlighting for counterexamples
  * **Kripke models** (nodes as worlds, edges for accessibility)
  * **Finite structures** for FOL (domain + predicate/function tables)

* **Tweak semantics**: choose modal frame (K, T, S4), and bounded FOL parameters (domain size *n*, term depth *k*)

* Includes built-in examples: Modus Ponens, Affirming the Consequent, modal puzzles, scope ambiguities in FOL, and more

## Installation & Usage

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Open your browser:**
   Navigate to `http://localhost:5000`

## Core Algorithms

### 1) Propositional validity via Truth Table

* Generate all possible truth value assignments for variables
* Check if premises are all true under any assignment where conclusion is false
* All premises true + conclusion false = INVALID (with counterexample)
* No such assignment = VALID

### 2) Bounded first-order countermodels (*coming soon*)

* Normalization: α-rename, drive quantifiers out (prenex), Skolemize ∃ under ∀
* Finite domain of size *n* with **grounding bound *k*
* Reduce to propositional and reuse truth table method

### 3) Modal logic K/T/S4 via labeled tableaux 

* Maintain sets of labeled formulas `@w φ` and relations `R(w,u)`
* Frame conditions: T adds reflexivity, S4 adds reflexivity + transitivity
* All branches closed ⇒ valid. Open branch ⇒ extract Kripke model

## Syntax Examples

### Propositional Logic
```
P                    # Atomic proposition
~P                   # Negation
(P & Q)              # Conjunction
(P | Q)              # Disjunction
(P -> Q)             # Implication
(P <-> Q)            # Biconditional
((P -> Q) & (Q -> P)) # Complex formula
```

### Modal Logic 
```
□P                   # Necessity
◊P                   # Possibility
(□P -> ◊P)          # Modal implication
```

### First-Order Logic 
```
P(x)                 # Predicate
f(x)                 # Function
∀x P(x)              # Universal quantifier
∃x P(x)              # Existential quantifier
```

## Testing

Run the test suite:
```bash
python test_core.py
```

## Examples

The application includes curated examples:

* **Modus Ponens**: `(P -> Q); P ⟹ Q` → VALID
* **Affirming the Consequent (Fallacy)**: `(P -> Q); Q ⟹ P` → INVALID with counterexample
* **Disjunctive Syllogism**: `(P | Q); ~P ⟹ Q` → VALID

## Project Structure

```
TruthTool/
├─ app.py                 # Flask application
├─ core/                  # Core logic engine
│  ├─ __init__.py
│  ├─ ast.py             # AST definitions
│  ├─ parser.py          # Formula parser
│  └─ solvers.py         # Solver implementations
├─ templates/
│  └─ index.html         # Main HTML template
├─ static/
│  ├─ css/
│  │  └─ style.css       # Styles
│  └─ js/
│     └─ app.js          # Frontend logic
├─ requirements.txt      # Python dependencies
└─ README.md            # This file
```

## License

MIT License 
