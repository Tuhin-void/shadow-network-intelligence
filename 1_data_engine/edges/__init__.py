"""
Edges Package - Graph edge definitions
"""
from .edge_factory import EdgeFactory, EdgeType, GraphEdge
from .relationships import RELATIONSHIP_TYPES, RELATIONSHIP_WEIGHTS

__all__ = [
    "EdgeFactory",
    "EdgeType",
    "GraphEdge",
    "RELATIONSHIP_TYPES",
    "RELATIONSHIP_WEIGHTS",
]