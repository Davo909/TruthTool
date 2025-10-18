from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sys, os

# add ./core to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

from core.parser import FormulaParser
from core.solvers import PropositionalSolver, ModalSolver, FOLSolver

app = Flask(__name__)
CORS(app)

# CSP (kept permissive enough for local fonts/js)
@app.after_request
def after_request(resp):
    resp.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    return resp

parser = FormulaParser()
pl_solver = PropositionalSolver()
modal_solver = ModalSolver()
fol_solver = FOLSolver()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/solve', methods=['POST'])
def solve_argument():
    try:
        data = request.get_json(force=True)
        premises_text = data.get('premises', [])
        conclusion_text = data.get('conclusion', '')
        logic = data.get('logic', 'PL')
        settings = data.get('settings', {})

        # Parse
        premises, conclusion = [], None
        if logic == 'PL':
            premises = [parser.parse_propositional(p) for p in premises_text]
            conclusion = parser.parse_propositional(conclusion_text)
            result = pl_solver.solve(premises, conclusion)

        elif logic == 'MODAL':
            premises = [parser.parse_modal(p) for p in premises_text]
            conclusion = parser.parse_modal(conclusion_text)
            frame = settings.get('modalFrame', 'K')
            result = modal_solver.solve(premises, conclusion, frame)

        elif logic == 'FOL':
            premises = [parser.parse_fol(p) for p in premises_text]
            conclusion = parser.parse_fol(conclusion_text)
            dom = int(settings.get('domainSize', 2) or 2)
            depth = int(settings.get('termDepth', 1) or 1)
            result = fol_solver.solve(premises, conclusion, dom, depth)

        else:
            return jsonify({'error': 'Invalid logic type.'}), 400

        return jsonify({'success': True, 'result': {
            'status': result.status,
            'message': result.message,
            'artifacts': result.artifacts
        }})

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/examples', methods=['GET'])
def examples():
    # New modal examples below are crafted so that
    # any countermodel requires at least THREE worlds.
    # Tip shown in descriptions helps users know what to expect.
    return jsonify({
        "propositional": [
            {"name":"Modus Ponens","premises":["(P -> Q)","P"],"conclusion":"Q","description":"Classic valid form."},
            {"name":"Affirming the Consequent (Fallacy)","premises":["(P -> Q)","Q"],"conclusion":"P","description":"Invalid."},
            {"name":"Disjunctive Syllogism","premises":["(P | Q)","~P"],"conclusion":"Q","description":"Valid with disjunction."}
        ],
        "modal": [
            {
                "name":"Distribution (K) — Valid",
                "premises":["□(P -> Q)"],
                "conclusion":"(□P -> □Q)",
                "description":"Valid in K/T/S4/S5."
            },
            {
                "name":"T (Reflexive) — Valid in T",
                "premises":["□P"],
                "conclusion":"◊P",
                "description":"Valid in T/S4/S5 (not in K).",
                "settings":{"modalFrame":"T"}
            },
            {
                "name":"S5 Axiom (5) — Valid in S5",
                "premises":["◊□G"],
                "conclusion":"□G",
                "description":"Characteristic of S5.",
                "settings":{"modalFrame":"S5"}
            },

            # --------- New: Many-world countermodels (≥ 3) ----------
            {
                "name":"(Many worlds) Branching possibilities don’t combine",
                "premises":["◊P","◊Q"],
                "conclusion":"◊(P ∧ Q)",
                "description":"Invalid in K/T/S4/S5. Countermodel needs ≥3 worlds: w0 sees w1 with P, w2 with Q, but no world with P∧Q.",
                "settings":{"modalFrame":"K"}
            },
            {
                "name":"(Many worlds) Positive introspection for ◊ fails in K",
                "premises":["◊◊P"],
                "conclusion":"◊P",
                "description":"Invalid in K. Minimal countermodel uses a chain w0 → w1 → w2 with P only at w2; needs ≥3 worlds.",
                "settings":{"modalFrame":"K"}
            },
            {
                "name":"(Many worlds) 4 is not a K-axiom",
                "premises":["□P"],
                "conclusion":"□□P",
                "description":"Invalid in K. To falsify, use a 3-world chain w0 → w1 → w2 with P true at all w0-successors but failing at some w1-successor.",
                "settings":{"modalFrame":"K"}
            },
            {
                "name":"(Many worlds) Necessity of disjunction doesn’t split",
                "premises":["□(P ∨ Q)"],
                "conclusion":"(□P ∨ □Q)",
                "description":"Invalid in K/T/S4/S5. Needs ≥3 worlds: w0 has two successors—one with P∧¬Q, another with ¬P∧Q.",
                "settings":{"modalFrame":"K"}
            }
            # Note: Harder examples like ◊□P ∧ ◊□Q ⟹ ◊□(P ∧ Q) typically require ≥5 worlds to refute in K.
            # With the default 3-world search bound, they will appear 'valid up to 3 worlds', so we omit them here.
        ],
        "fol": [
            {"name":"∀-Elim","premises":["∀x P(x)"],"conclusion":"P(a)","description":"Universal instantiation (valid)."},
            {"name":"∃-Intro","premises":["P(a)"],"conclusion":"∃x P(x)","description":"Existential generalization (valid)."},
            {"name":"Scope swap (invalid)","premises":["∃x ∀y R(x,y)"],"conclusion":"∀y ∃x R(x,y)","description":"Not generally valid."}
        ]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
