"""
Entity Registry - Central registry for all generated entities
"""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any


@dataclass
class EntityRegistry:
    """Central registry for all generated entities and edges"""

    persons: Dict[str, Any] = field(default_factory=dict)
    companies: Dict[str, Any] = field(default_factory=dict)
    accounts: Dict[str, Any] = field(default_factory=dict)
    addresses: Dict[str, Any] = field(default_factory=dict)
    devices: Dict[str, Any] = field(default_factory=dict)
    transactions: Dict[str, Any] = field(default_factory=dict)
    edges: Dict[str, Any] = field(default_factory=dict)
    fraud_rings: Dict[str, Any] = field(default_factory=dict)
    documents: Dict[str, Any] = field(default_factory=dict)

    _entity_type_map: Dict[str, str] = field(default_factory=dict)
    _edge_index: Dict[str, List[str]] = field(default_factory=dict)

    def add_person(self, person) -> None:
        self.persons[person.id] = person
        self._entity_type_map[person.id] = "Person"

    def add_company(self, company) -> None:
        self.companies[company.id] = company
        self._entity_type_map[company.id] = "Company"

    def add_account(self, account) -> None:
        self.accounts[account.id] = account
        self._entity_type_map[account.id] = "Account"

    def add_address(self, address) -> None:
        self.addresses[address.id] = address
        self._entity_type_map[address.id] = "Address"

    def add_device(self, device) -> None:
        self.devices[device.id] = device
        self._entity_type_map[device.id] = "Device"

    def add_transaction(self, transaction) -> None:
        self.transactions[transaction.id] = transaction

    def add_edge(self, edge) -> None:
        self.edges[edge.id] = edge
        key = f"{edge.from_id}|{edge.relationship}"
        if key not in self._edge_index:
            self._edge_index[key] = []
        self._edge_index[key].append(edge.id)

    def add_fraud_ring(self, ring) -> None:
        self.fraud_rings[ring.id] = ring

    def add_document(self, doc_id: str, document) -> None:
        self.documents[doc_id] = document

    def get_entity(self, entity_id: str) -> Optional[Any]:
        for collection in [self.persons, self.companies, self.accounts, self.addresses, self.devices]:
            if entity_id in collection:
                return collection[entity_id]
        return None

    def get_entity_type(self, entity_id: str) -> Optional[str]:
        return self._entity_type_map.get(entity_id)

    def get_edges_from(self, entity_id: str) -> List[Any]:
        return [e for e in self.edges.values() if e.from_id == entity_id]

    def get_edges_to(self, entity_id: str) -> List[Any]:
        return [e for e in self.edges.values() if e.to_id == entity_id]

    def get_neighbors(self, entity_id: str) -> Set[str]:
        neighbors = set()
        for e in self.edges.values():
            if e.from_id == entity_id:
                neighbors.add(e.to_id)
            if e.to_id == entity_id:
                neighbors.add(e.from_id)
        return neighbors

    def get_fraud_entities(self) -> Set[str]:
        entities = set()
        for ring in self.fraud_rings.values():
            entities.update(ring.entities)
        return entities

    def get_entity_count(self) -> int:
        return (
            len(self.persons)
            + len(self.companies)
            + len(self.accounts)
            + len(self.addresses)
            + len(self.devices)
        )

    def get_edge_count(self) -> int:
        return len(self.edges)

    def get_transaction_count(self) -> int:
        return len(self.transactions)

    def get_fraud_ring_count(self) -> int:
        return len(self.fraud_rings)

    def get_document_count(self) -> int:
        return len(self.documents)

    def to_dict(self) -> dict:
        return {
            "entity_counts": {
                "persons": len(self.persons),
                "companies": len(self.companies),
                "accounts": len(self.accounts),
                "addresses": len(self.addresses),
                "devices": len(self.devices),
                "transactions": len(self.transactions),
                "edges": len(self.edges),
                "fraud_rings": len(self.fraud_rings),
                "documents": len(self.documents),
            },
            "total_entities": self.get_entity_count(),
        }