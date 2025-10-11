from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS
import json
import sys
import os

# Add the core module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

from core.parser import FormulaParser
from core.solvers import PropositionalSolver, FOLSolver, ModalSolver

app = Flask(__name__)
CORS(app)

# Set up CSP headers to allow necessary functionality
@app.after_request
def after_request(response):
    # Set Content Security Policy to allow necessary functionality
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    return response

# Initialize parsers and solvers
parser = FormulaParser()
pl_solver = PropositionalSolver()
fol_solver = FOLSolver()
modal_solver = ModalSolver()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parse', methods=['POST'])
def parse_formula():
    try:
        data = request.json
        formula = data.get('formula', '')
        logic_type = data.get('logic', 'PL')
        
        if logic_type == 'PL':
            result = parser.parse_propositional(formula)
        elif logic_type == 'FOL':
            result = parser.parse_fol(formula)
        elif logic_type == 'MODAL':
            result = parser.parse_modal(formula)
        else:
            return jsonify({'error': 'Invalid logic type'}), 400
            
        return jsonify({'success': True, 'ast': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/solve', methods=['POST'])
def solve_argument():
    try:
        data = request.json
        premises = data.get('premises', [])
        conclusion = data.get('conclusion', '')
        logic = data.get('logic', 'PL')
        settings = data.get('settings', {})
        
        # Parse premises and conclusion
        parsed_premises = []
        for premise in premises:
            if logic == 'PL':
                parsed_premises.append(parser.parse_propositional(premise))
            elif logic == 'FOL':
                parsed_premises.append(parser.parse_fol(premise))
            elif logic == 'MODAL':
                parsed_premises.append(parser.parse_modal(premise))
        
        if logic == 'PL':
            parsed_conclusion = parser.parse_propositional(conclusion)
            result = pl_solver.solve(parsed_premises, parsed_conclusion)
        elif logic == 'FOL':
            parsed_conclusion = parser.parse_fol(conclusion)
            domain_size = settings.get('folDomainSize', 3)
            term_depth = settings.get('folTermDepth', 2)
            result = fol_solver.solve(parsed_premises, parsed_conclusion, domain_size, term_depth)
        elif logic == 'MODAL':
            parsed_conclusion = parser.parse_modal(conclusion)
            modal_frame = settings.get('modalFrame', 'K')
            result = modal_solver.solve(parsed_premises, parsed_conclusion, modal_frame)
        else:
            return jsonify({'error': 'Invalid logic type'}), 400
            
        # Convert SolverResult to dict for JSON serialization
        result_dict = {
            'status': result.status,
            'message': result.message,
            'artifacts': result.artifacts
        }
        return jsonify({'success': True, 'result': result_dict})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/examples', methods=['GET'])
def get_examples():
    examples = {
        'propositional': [
            {
                'name': 'Modus Ponens',
                'premises': ['(P -> Q)', 'P'],
                'conclusion': 'Q',
                'description': 'Classic valid argument form'
            },
            {
                'name': 'Affirming the Consequent (Fallacy)',
                'premises': ['(P -> Q)', 'Q'],
                'conclusion': 'P',
                'description': 'Common logical fallacy'
            },
            {
                'name': 'Disjunctive Syllogism',
                'premises': ['(P | Q)', '~P'],
                'conclusion': 'Q',
                'description': 'Valid argument using disjunction'
            }
        ],
        'modal': [
            {
                'name': 'Modal Distribution',
                'premises': ['□(P -> Q)'],
                'conclusion': '(□P -> □Q)',
                'description': 'Valid in K, T, S4'
            },
            {
                'name': 'Barcan Formula (Simplified)',
                'premises': ['□P'],
                'conclusion': '◊P',
                'description': 'Necessity implies possibility (valid in T, S4)'
            }
        ],
        'fol': [
            {
                'name': 'Universal Instantiation',
                'premises': ['∀x P(x)'],
                'conclusion': 'P(a)',
                'description': 'Valid FOL inference'
            },
            {
                'name': 'Scope Ambiguity',
                'premises': ['∃x ∀y R(x,y)'],
                'conclusion': '∀y ∃x R(x,y)',
                'description': 'Invalid - order of quantifiers matters'
            }
        ]
    }
    return jsonify(examples)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
