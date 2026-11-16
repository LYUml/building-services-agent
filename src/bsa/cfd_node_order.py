"""Pinned SU2/VTK to Gmsh linear tetrahedron/prism node ordering.

Reference: Gmsh 4.15.2 GModelIO_SU2.cpp and MPrism.h::getVertexVTK.
Gmsh upstream is GPL-2.0-or-later; source URLs/hashes and attribution are
recorded in docs/CFD_NODE_ORDER.md. This implements the ordering convention,
not a mesh engine. Callers retain node-ID base and geometry/quality checks.
"""

_TETRA = (0, 1, 2, 3)
_PRISM = (0, 2, 1, 3, 5, 4)


def _convert(kind, values, conventions):
    if type(kind) is not int or kind not in conventions:
        raise ValueError('Only declared linear tetrahedron/prism cell types supported')
    target, permutation = conventions[kind]
    try:
        nodes = tuple(values)
    except TypeError as exc:
        raise ValueError('Explicit node identifiers required') from exc
    if (len(nodes) != len(permutation)
            or any(type(node) is not int or node < 0 for node in nodes)
            or len(set(nodes)) != len(nodes)):
        raise ValueError('Distinct nonnegative integer node IDs of the declared arity required')
    return target, tuple(nodes[i] for i in permutation)


def su2_to_gmsh(cell_type, nodes):
    """SU2/VTK 10 (tet4), 13 (prism6) to Gmsh 4, 6; no ID-base change."""
    return _convert(cell_type, nodes, {10: (4, _TETRA), 13: (6, _PRISM)})


def gmsh_to_su2(cell_type, nodes):
    """Inverse supported ordering, preserving identifiers; not geometry validation."""
    return _convert(cell_type, nodes, {4: (10, _TETRA), 6: (13, _PRISM)})
