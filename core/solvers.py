import itertools
import time
from typing import List, Dict, Set, Optional, Tuple, Any
from .ast import *

# ================================
# Result wrapper
# ================================
class SolverResult:
    def __init__(self, status: str, message: str = "", artifacts: Dict[str, Any] = None):
        self.status = status  # 'VALID' | 'INVALID' | 'UNKNOWN' | 'ERROR'
        self.message = message
        self.artifacts = artifacts or {}

def _now() -> float:
    try:
        return time.perf_counter()
    except Exception:
        return time.time()

# ===================================
# Propositional (truth tables)
# ===================================
class PropositionalSolver:
    def __init__(self, timeout_seconds: float = 8.0):
        self.timeout = timeout_seconds

    def solve(self, premises: List[Formula], conclusion: Formula) -> SolverResult:
        start = _now()
        try:
            # Variables = pretty-printed propositional atoms only
            atom_names = sorted({str(a) for f in premises+[conclusion] for a in get_atoms(f)})
            if not atom_names:
                return SolverResult('ERROR', 'No propositional atoms found.')

            rows = []
            variables = list(atom_names)
            counterexamples = 0

            for bits in itertools.product([False, True], repeat=len(variables)):
                if _now() - start > self.timeout:
                    return SolverResult('UNKNOWN', 'Truth-table timeout.')

                asg = dict(zip(variables, bits))
                prem_true = all(self._eval_as_pl(p, asg) for p in premises)
                concl_true = self._eval_as_pl(conclusion, asg)

                is_cex = prem_true and (not concl_true)
                if is_cex: counterexamples += 1

                rows.append({
                    "values": asg,
                    "is_counterexample": is_cex
                })

            if counterexamples:
                return SolverResult('INVALID', 'Counterexample(s) found in truth table.', {
                    "truth_table": rows
                })
            else:
                return SolverResult('VALID', 'No counterexamples in truth table.', {
                    "truth_table": rows
                })

        except Exception as e:
            return SolverResult('ERROR', f'Propositional solver error: {e!r}')

    def _eval_as_pl(self, f: Formula, env: Dict[str,bool]) -> bool:
        # Modal/FOL nodes treated as atomic by name (skeleton) if they appear
        if isinstance(f, Atom):
            return bool(env.get(str(f), False))
        if isinstance(f, Predicate):
            return bool(env.get(f.name, False))  # 0-ary predicate as atom name
        if isinstance(f, Negation): return not self._eval_as_pl(f.formula, env)
        if isinstance(f, Conjunction): return self._eval_as_pl(f.left, env) and self._eval_as_pl(f.right, env)
        if isinstance(f, Disjunction): return self._eval_as_pl(f.left, env) or self._eval_as_pl(f.right, env)
        if isinstance(f, Implication): return (not self._eval_as_pl(f.left, env)) or self._eval_as_pl(f.right, env)
        if isinstance(f, Biconditional): return self._eval_as_pl(f.left, env) == self._eval_as_pl(f.right, env)
        # Necessity/Possibility/Quantifiers → atomic
        return bool(env.get(str(f), False))

# ===================================
# Modal (Kripke search: K/T/S4/S5)
# ===================================
class ModalSolver:
    def __init__(self, timeout_seconds: float = 8.0, max_worlds: int = 3):
        self.timeout = timeout_seconds
        self.max_worlds = max(1, min(5, int(max_worlds)))

    def solve(self, premises: List[Formula], conclusion: Formula, modal_frame: str = "K") -> SolverResult:
        start = _now()
        try:
            frame = modal_frame.upper().strip()
            if frame not in {"K","T","S4","S5"}:
                frame = "K"

            # propositional skeleton short-circuit (sound in all normal modal logics)
            if self._skel_entails(premises, conclusion, start):
                # For UX: include a minimal frame preview even on propositional validity
                preview = self._export(frame, ["w0"], self._minimal_R(["w0"], frame), {"w0": {}})
                return SolverResult('VALID', 'Valid by propositional consequence.', {
                    "kripke": preview
                })

            atoms = sorted({str(a) for f in premises+[conclusion] for a in get_atoms(f)})

            # enumerate models up to bound
            for n in range(1, self.max_worlds+1):
                worlds = [f"w{i}" for i in range(n)]
                for R in self._relations(worlds, frame, start):
                    if _now() - start > self.timeout:
                        return SolverResult('UNKNOWN', 'Modal search timeout.', {
                            "kripke": self._preview(frame, worlds, R, atoms)
                        })
                    for val in self._valuations(worlds, atoms, start):
                        model = {"frame": frame, "worlds": worlds, "R": R, "val": val, "root":"w0"}
                        if self._holds_all(model, "w0", premises) and (not self._holds(model, "w0", conclusion)):
                            # Countermodel found: attach evaluation map for visualization
                            labels, truth = self._collect_eval(model, premises, conclusion)
                            exported = self._export(frame, worlds, R, val)
                            exported["formulas"] = labels
                            exported["truth"] = truth
                            return SolverResult('INVALID', 'Countermodel found.', {
                                "kripke": exported
                            })

            # No countermodel found up to bound -> treat as valid; include symbolic preview
            preview = self._export(frame, ["w0"], self._minimal_R(["w0"], frame), {"w0": {}})
            return SolverResult('VALID', f'No countermodel up to {self.max_worlds} worlds.', {
                "kripke": preview
            })

        except Exception as e:
            return SolverResult('ERROR', f'Modal solver error: {e!r}')

    # ---- semantics
    def _holds_all(self, model, w, fs): return all(self._holds(model, w, f) for f in fs)

    def _holds(self, model, w, f: Formula) -> bool:
        if isinstance(f, Atom):
            return bool(model["val"][w].get(str(f), False))
        if isinstance(f, Predicate):
            # treat 0-ary predicate as PL atom name
            return bool(model["val"][w].get(f.name, False))
        if isinstance(f, Negation):
            return not self._holds(model, w, f.formula)
        if isinstance(f, Conjunction):
            return self._holds(model, w, f.left) and self._holds(model, w, f.right)
        if isinstance(f, Disjunction):
            return self._holds(model, w, f.left) or self._holds(model, w, f.right)
        if isinstance(f, Implication):
            return (not self._holds(model, w, f.left)) or self._holds(model, w, f.right)
        if isinstance(f, Biconditional):
            return self._holds(model, w, f.left) == self._holds(model, w, f.right)
        if isinstance(f, Necessity):
            succs = [v for (u,v) in model["R"] if u==w]
            return all(self._holds(model, v, f.formula) for v in succs)
        if isinstance(f, Possibility):
            succs = [v for (u,v) in model["R"] if u==w]
            return any(self._holds(model, v, f.formula) for v in succs)
        # Quantifiers treated as atomic in modal solver
        return bool(model["val"][w].get(str(f), False))

    # ---- enumeration
    def _relations(self, worlds: List[str], frame: str, start: float):
        base_pairs = [(u,v) for u in worlds for v in worlds]
        seen = set()
        for mask in range(1 << (len(base_pairs))):
            if _now()-start > self.timeout: break
            R = set()
            for i,(u,v) in enumerate(base_pairs):
                if (mask>>i)&1: R.add((u,v))
            # enforce frame closure
            if frame in {"T","S4","S5"}:
                for w in worlds: R.add((w,w))
            changed = True
            while changed:
                changed = False
                if frame in {"S4","S5"}:
                    new = {(a,c) for (a,b) in R for (b2,c) in R if b==b2} - R
                    if new: R|=new; changed=True
                if frame == "S5":
                    new = {(b,a) for (a,b) in R} - R
                    if new: R|=new; changed=True
            key = tuple(sorted(R))
            if key in seen: continue
            seen.add(key)
            yield R

    def _valuations(self, worlds: List[str], atoms: List[str], start: float):
        if not atoms:
            yield {w:{} for w in worlds}; return
        total_bits = len(worlds)*len(atoms)
        for bits in itertools.product([False,True], repeat=total_bits):
            if _now()-start > self.timeout: break
            val = {w:{} for w in worlds}
            for wi,w in enumerate(worlds):
                for ai,a in enumerate(atoms):
                    val[w][a] = bool(bits[wi*len(atoms)+ai])
            yield val

    def _skel_entails(self, premises, conclusion, start):
        forms = list(dict.fromkeys([str(f) for f in premises] + [str(conclusion)]))
        for bits in itertools.product([False,True], repeat=len(forms)):
            if _now()-start > self.timeout: return False
            env = dict(zip(forms, bits))
            if all(env[str(p)] for p in premises) and not env[str(conclusion)]:
                return False
        return True

    # ---- export / preview
    def _export(self, frame, worlds, R, val):
        edges = []
        for (u,v) in sorted(R):
            props = ["accessible"]
            if u==v: props.append("reflexive")
            if (v,u) in R and u!=v: props.append("symmetric")
            if any((u,x) in R and (x,v) in R for x in worlds if x not in (u,v)):
                props.append("transitive")
            edges.append({"from":u,"to":v,"properties":props})
        return {
            "frame": frame,
            "worlds": [{"id":w, "is_root":(w=="w0"), "valuation": val.get(w,{})} for w in worlds],
            "edges": edges
        }

    def _preview(self, frame, worlds, R, atoms):
        return self._export(frame, worlds, R, {w:{a:False for a in atoms} for w in worlds})

    def _minimal_R(self, worlds: List[str], frame: str) -> Set[Tuple[str,str]]:
        # Provide a tiny canonical relation for display when we don't have a concrete model
        R = set()
        if frame in {"T","S4","S5"}:
            for w in worlds:
                R.add((w,w))
        return R

    def _collect_eval(self, model, premises: List[Formula], conclusion: Formula):
        labels: Dict[str,str] = {}
        for i,p in enumerate(premises,1):
            labels[f"P{i}"] = str(p)
        labels["C"] = str(conclusion)
        truth: Dict[str, Dict[str,bool]] = {}
        for w in model["worlds"]:
            world_map: Dict[str,bool] = {}
            for i,p in enumerate(premises,1):
                world_map[f"P{i}"] = self._holds(model, w, p)
            world_map["C"] = self._holds(model, w, conclusion)
            truth[w] = world_map
        return labels, truth

# ===================================
# FOL (bounded finite model search)
# ===================================
class FOLSolver:
    """
    Tries to find a finite countermodel up to a given domain size by
    enumerating predicate interpretations that occur in the signature.
    Functions/constants are not interpreted (if present, we return UNKNOWN).
    """
    def __init__(self, timeout_seconds: float = 8.0, max_structures: int = 5000):
        self.timeout = timeout_seconds
        self.max_structures = max_structures

    def solve(self, premises: List[Formula], conclusion: Formula,
              domain_size: int = 2, term_depth: int = 1) -> SolverResult:
        start = _now()
        try:
            # simple safeguards
            if domain_size < 1: domain_size = 1
            if domain_size > 3: domain_size = 3

            # block if functions/constants present (out of scope)
            if any(has_functions_or_constants(f) for f in premises+[conclusion]):
                return SolverResult('UNKNOWN', 'FOL functions/constants not supported in this build.', {
                    "structure": self._sample_structure(domain_size, {})
                })

            sig = {}
            for f in premises+[conclusion]:
                for k,v in get_signature(f).items():
                    sig[k] = max(sig.get(k,0), v)

            domain = tuple(f"d{i}" for i in range(domain_size))
            tuples_by_pred: Dict[Tuple[str,int], List[Tuple[Any,...]]] = {}
            for name, ar in sig.items():
                tuples = list(itertools.product(domain, repeat=ar))
                tuples_by_pred[(name,ar)] = tuples

            # Enumerate structures
            preds = list(tuples_by_pred.keys())
            if len(preds) == 0:
                # purely logical validity w/o predicates
                if self._all_true_in_all_assignments(premises, conclusion, domain):
                    return SolverResult('VALID', 'Valid (no predicates in signature).', {
                        "structure": self._sample_structure(domain_size, {})
                    })
                else:
                    return SolverResult('UNKNOWN', 'No predicate symbols to vary; cannot refute.', {
                        "structure": self._sample_structure(domain_size, {})
                    })

            count = 0
            for interp_bits in self._enumerate_interpretations(preds, tuples_by_pred, start):
                count += 1
                if count > self.max_structures:
                    return SolverResult('UNKNOWN', 'Search cap hit before finding countermodel.', {
                        "structure": self._sample_structure(domain_size, interp_bits)
                    })
                struct = {"domain": domain, "pred": interp_bits}
                if self._premises_true_conclusion_false(struct, premises, conclusion):
                    return SolverResult('INVALID', 'Finite countermodel found.', {
                        "structure": self._viz_structure(struct)
                    })

            # no countermodel up to bound
            return SolverResult('VALID', f'No countermodel up to domain size {domain_size}.', {
                "structure": self._viz_structure({"domain":domain, "pred": {}})
            })

        except Exception as e:
            return SolverResult('ERROR', f'FOL solver error: {e!r}')

    # ---- model enumeration
    def _enumerate_interpretations(self, preds, tuples_by_pred, start):
        # For each predicate choose which tuples are true
        spaces = []
        for (name, ar) in preds:
            tuples = tuples_by_pred[(name,ar)]
            # iterate over all subsets of tuples
            spaces.append([set(s) for r in range(len(tuples)+1) for s in itertools.combinations(tuples, r)])
        for choice in itertools.product(*spaces):
            if _now() - start > self.timeout: break
            yield {preds[i]: choice[i] for i in range(len(preds))}

    # ---- evaluation
    def _holds(self, struct, env: Dict[str,Any], f: Formula) -> bool:
        if isinstance(f, Predicate):
            name, ar = f.name, len(f.args)
            tup = tuple(self._eval_term(struct, env, t) for t in f.args)
            true_set = struct["pred"].get((name,ar), set())
            return tup in true_set
        if isinstance(f, Negation):
            return not self._holds(struct, env, f.formula)
        if isinstance(f, Conjunction):
            return self._holds(struct, env, f.left) and self._holds(struct, env, f.right)
        if isinstance(f, Disjunction):
            return self._holds(struct, env, f.left) or self._holds(struct, env, f.right)
        if isinstance(f, Implication):
            return (not self._holds(struct, env, f.left)) or self._holds(struct, env, f.right)
        if isinstance(f, Biconditional):
            return self._holds(struct, env, f.left) == self._holds(struct, env, f.right)
        if isinstance(f, UniversalQuantifier):
            var = f.variable
            for d in struct["domain"]:
                env[var] = d
                if not self._holds(struct, env, f.formula): return False
            return True
        if isinstance(f, ExistentialQuantifier):
            var = f.variable
            for d in struct["domain"]:
                env[var] = d
                if self._holds(struct, env, f.formula): return True
            return False
        if isinstance(f, Atom):
            # treat as 0-ary predicate by its name
            return ((f.name,0) in struct["pred"]) and (() in struct["pred"][(f.name,0)])
        if isinstance(f, (Necessity, Possibility)):
            # not applicable in FOL solver
            return False
        return False

    def _eval_term(self, struct, env, t):
        if isinstance(t, Variable): return env.get(t.name)
        if isinstance(t, Constant): return t.name  # treat as distinct symbol
        if isinstance(t, Function): return None    # functions unsupported
        return t

    def _premises_true_conclusion_false(self, struct, premises, conclusion) -> bool:
        env: Dict[str,Any] = {}
        return all(self._holds(struct, env, p) for p in premises) and (not self._holds(struct, env, conclusion))

    def _all_true_in_all_assignments(self, premises, conclusion, domain):
        # degenerate case: no predicates -> quantifier truth reduces to vacuity over domain
        struct = {"domain": domain, "pred": {}}
        env: Dict[str,Any] = {}
        return all(self._holds(struct, env, p) for p in premises) and self._holds(struct, env, conclusion)

    # ---- viz helpers
    def _viz_structure(self, struct):
        domain = list(struct["domain"])
        preds = {}
        for (name, ar), tuples in struct["pred"].items():
            preds.setdefault(name, {"arity": ar, "tuples": []})
            preds[name]["tuples"] = [list(t) for t in tuples]
        return {"domain": domain, "predicates": preds, "functions": {}}

    def _sample_structure(self, n, pred_map):
        return self._viz_structure({"domain": tuple(f"d{i}" for i in range(n)), "pred": pred_map})
