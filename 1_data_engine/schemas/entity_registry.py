"""
Entity Registry - Central registry for all generated entities
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import defaultdict


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

    _edge_index: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    _entity_type_map: Dict[str, str] = field(default_factory=dict)

    def add_person(self, person) -> None:
        self.persons[person.id] = person
        self._entity_type_map[person.id] = "PERSON"

    def add_company(self, company) -> None:
        self.companies[company.id] = company
        self._entity_type_map[company.id] = "COMPANY"

    def add_account(self, account) -> None:
        self.accounts[account.id] = account
        self._entity_type_map[account.id] = "ACCOUNT"

    def add_address(self, address) -> None:
        self.addresses[address.id] = address
        self._entity_type_map[address.id] = "ADDRESS"

    def add_transaction(self, transaction) -> None:
        self.transactions[transaction.id] = transaction

    def add_edge(self, edge) -> None:
        self.edges[edge.id] = edge
        key = f"{edge.from_id}|{edge.relationship.value}"
        self._edge_index[key].append(edge.id)

    def add_fraud_ring(self, ring) -> None:
        self.fraud_rings[ring.id] = ring

    def get_entity(self, entity_id: str) -> Optional[Any]:
        """Get any entity by ID"""
        for collection in [self.persons, self.companies, self.accounts, self.addresses]:
            if entity_id in collection:
                return collection[entity_id]
        return None

    def get_entity_type(self, entity_id: str) -> Optional[str]:
        return self._entity_type_map.get(entity_id)

    def get_person(self, person_id: str) -> Optional[Any]:
        return self.persons.get(person_id)

    def get_company(self, company_id: str) -> Optional[Any]:
        return self.companies.get(company_id)

    def get_account(self, account_id: str) -> Optional[Any]:
        return self.accounts.get(account_id)

    def get_address(self, address_id: str) -> Optional[Any]:
        return self.addresses.get(address_id)

    def get_fraud_ring(self, ring_id: str) -> Optional[Any]:
        return self.fraud_rings.get(ring_id)

    def get_edges_from(self, entity_id: str) -> List[Any]:
        return [e for e in self.edges.values() if e.from_id == entity_id]

    def get_edges_to(self, entity_id: str) -> List[Any]:
        return [e for e in self.edges.values() if e.to_id == entity_id]

    def get_neighbors(self, entity_id: str) -> List[str]:
        neighbors = set()
        for e in self.edges.values():
            if e.from_id == entity_id:
                neighbors.add(e.to_id)
            if e.to_id == entity_id:
                neighbors.add(e.from_id)
        return list(neighbors)

    def get_all_person_ids(self) -> List[str]:
        return list(self.persons.keys())

    def get_all_company_ids(self) -> List[str]:
        return list(self.companies.keys())

    def get_all_account_ids(self) -> List[str]:
        return list(self.accounts.keys())

    def get_all_address_ids(self) -> List[str]:
        return list(self.addresses.keys())

    def get_all_edges(self) -> List[Any]:
        return list(self.edges.values())

    def get_fraud_edges(self) -> List[Any]:
        return [e for e in self.edges.values() if e.is_fraud_related]

    def get_fraud_entities(self) -> List[str]:
        entities = set()
        for ring in self.fraud_rings.values():
            entities.update(ring.entities)
        return list(entities)

    def get_entity_count(self) -> int:
        return (
            len(self.persons)
            + len(self.companies)
            + len(self.accounts)
            + len(self.addresses)
        )

    def get_edge_count(self) -> int:
        return len(self.edges)

    def get_fraud_ring_count(self) -> int:
        return len(self.fraud_rings)

    def to_dict(self) -> dict:
        return {
            "entity_counts": {
                "persons": len(self.persons),
                "companies": len(self.companies),
                "accounts": len(self.accounts),
                "addresses": len(self.addresses),
                "transactions": len(self.transactions),
                "edges": len(self.edges),
                "fraud_rings": len(self.fraud_rings),
            },
            "total_entities": self.get_entity_count(),
        }