"""Prior-art k=4 candidate reported as a three-violation potential."""

from kserver.potential.canonical_potential import Potential as CanonicalPotential


INDEX_MATRIX = [
    [-5, -5, -5, -5],
    [5, -1, -2, -2],
    [5, 1, 3, 4],
    [5, 2, -4, -4],
    [5, 2, 4, -3],
]

# Upper-triangular entries of the symmetric coefficient matrix in the paper,
# in the evaluator's canonical distance-vector order.
COEFS = [-1, 0, -1, 0, 1, 0, 0, -1, 0, 0]


class Potential(CanonicalPotential):
    def __init__(self, context, **kwargs):
        del kwargs
        super().__init__(context, n=5, index_matrix=INDEX_MATRIX, coefs=COEFS)
