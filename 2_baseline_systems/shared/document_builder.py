"""
Document builder - transforms 1_data_engine entities into RAG documents.
"""
import json
import logging
from pathlib import Path
from typing import Optional
from .schemas import ShadowDataset, Document, BenchmarkQuery
from .chunkers.recursive import RecursiveChunker

logger = logging.getLogger(__name__)


class DocumentBuilder:
    def __init__(self, dataset: ShadowDataset, chunk_size: int = 500, chunk_overlap: int = 50):
        self.dataset = dataset
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def build_all(self) -> list[Document]:
        docs = []
        docs.extend(self._build_entity_profiles())
        docs.extend(self._build_transaction_docs())
        docs.extend(self._build_authored_docs())
        logger.info(f"Built {len(docs)} documents")
        return docs

    def build_with_enrichment(self, jsonl_path: Optional[Path] = None) -> list[Document]:
        """Build the base entity corpus AND fold in the enriched intelligence
        corpus (if it exists). Backward-compatible: when `jsonl_path` is
        missing or empty, returns the same docs as `build_all()`.

        The enriched JSONL is produced by
        `scripts/semantic_intelligence_corpus.py`. Each line is a chunk-
        ready record with `doc_id`, `doc_type`, `primary_entity`,
        `related_entities`, `narrative`, plus topology metadata that we
        forward into `Document.metadata` so the vector store can filter."""
        docs = self.build_all()
        if jsonl_path is None:
            return docs
        path = Path(jsonl_path)
        if not path.exists():
            logger.info("enriched JSONL not found at %s — skipping", path)
            return docs
        enriched = list(self._load_jsonl_documents(path))
        logger.info("enriched corpus added: %d additional documents from %s",
                    len(enriched), path)
        docs.extend(enriched)
        return docs

    def _load_jsonl_documents(self, path: Path):
        """Yield Document records from the semantic-intelligence JSONL."""
        with path.open() as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning("skipping malformed JSONL line %d: %s", i, e)
                    continue
                doc_id = rec.get("doc_id") or f"ENR-{i:08d}"
                narrative = rec.get("narrative") or ""
                if not narrative:
                    continue
                yield Document(
                    id=str(doc_id),
                    text=narrative,
                    metadata={
                        "source":             "semantic_intelligence_corpus",
                        "doc_type":           rec.get("doc_type"),
                        "primary_entity":     rec.get("primary_entity"),
                        "related_entities":   rec.get("related_entities") or [],
                        "topology_tags":      rec.get("topology_tags") or [],
                        "risk_tags":          rec.get("risk_tags") or [],
                        "edge_types":         rec.get("edge_types") or [],
                        "ring_id":            rec.get("ring_id"),
                        "investigation_type": rec.get("investigation_type"),
                        "retrieval_keywords": rec.get("retrieval_keywords") or [],
                        "token_estimate":     rec.get("token_estimate"),
                    },
                )

    def _build_entity_profiles(self) -> list[Document]:
        docs = []
        for person in self.dataset.persons:
            doc = self._person_to_doc(person)
            if doc:
                docs.append(doc)
        for company in self.dataset.companies:
            doc = self._company_to_doc(company)
            if doc:
                docs.append(doc)
        for account in self.dataset.accounts:
            doc = self._account_to_doc(account)
            if doc:
                docs.append(doc)
        for address in self.dataset.addresses:
            doc = self._address_to_doc(address)
            if doc:
                docs.append(doc)
        return docs

    def _person_to_doc(self, person: dict) -> Optional[Document]:
        entity_id = person.get("id", "")
        if not entity_id:
            return None

        risk = person.get("risk_score", 0.0)
        risk_level = "LOW"
        if risk > 0.8:
            risk_level = "CRITICAL"
        elif risk > 0.6:
            risk_level = "HIGH"
        elif risk > 0.3:
            risk_level = "MEDIUM"

        flags = []
        if person.get("is_pep"):
            flags.append("PEP")
        if person.get("is_sanctioned"):
            flags.append("SANCTIONED")
        if person.get("is_watched"):
            flags.append("WATCHED")
        if person.get("is_mule"):
            flags.append("MULE")
        flags_str = f" [{', '.join(flags)}]" if flags else ""

        name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
        text = (
            f"Person {entity_id}: {name}. "
            f"Risk Score: {risk:.2f} ({risk_level}).{flags_str} "
            f"Nationality: {person.get('nationality', 'Unknown')}. "
            f"Tax ID: {person.get('tax_id', 'N/A')}. "
        )

        if person.get("email"):
            text += f"Email: {person['email']}. "
        if person.get("phone"):
            text += f"Phone: {person['phone']}. "

        edges = self.dataset.get_edges_for_entity(entity_id)
        rels = []
        for edge in edges[:5]:
            to_id = edge.get("to_id", "")
            rel = edge.get("relationship", "")
            rels.append(f"{rel} {to_id}")
        if rels:
            text += f"Relationships: {', '.join(rels)}."

        return Document(
            id=f"entity::{entity_id}",
            text=text.strip(),
            metadata={
                "doc_type": "entity_profile",
                "entity_type": "Person",
                "entity_id": entity_id,
                "risk_score": risk,
                "risk_level": risk_level,
                "fraud_ring_id": None,
            },
        )

    def _company_to_doc(self, company: dict) -> Optional[Document]:
        entity_id = company.get("id", "")
        if not entity_id:
            return None

        risk = company.get("risk_score", 0.0)
        risk_level = "LOW"
        if risk > 0.8:
            risk_level = "CRITICAL"
        elif risk > 0.6:
            risk_level = "HIGH"
        elif risk > 0.3:
            risk_level = "MEDIUM"

        flags = []
        if company.get("is_offshore"):
            flags.append("OFFSHORE")
        if company.get("is_shell"):
            flags.append("SHELL")
        if company.get("is_dormant"):
            flags.append("DORMANT")
        flags_str = f" [{', '.join(flags)}]" if flags else ""

        name = company.get("name", company.get("legal_name", "Unknown"))
        text = (
            f"Company {entity_id}: {name}. "
            f"Risk Score: {risk:.2f} ({risk_level}).{flags_str} "
            f"Industry: {company.get('industry', 'Unknown')}. "
            f"Type: {company.get('company_type', 'Unknown')}. "
            f"EIN: {company.get('ein', 'N/A')}. "
        )

        if company.get("registration_country"):
            text += f"Registered in: {company['registration_country']}. "
        if company.get("incorporation_date"):
            text += f"Incorporated: {company['incorporation_date']}. "
        if company.get("annual_revenue"):
            text += f"Revenue: ${company['annual_revenue']:,.0f}. "
        if company.get("employee_count"):
            text += f"Employees: {company['employee_count']}. "

        edges = self.dataset.get_edges_for_entity(entity_id)
        rels = []
        for edge in edges[:5]:
            to_id = edge.get("to_id", "")
            rel = edge.get("relationship", "")
            rels.append(f"{rel} {to_id}")
        if rels:
            text += f"Relationships: {', '.join(rels)}."

        return Document(
            id=f"entity::{entity_id}",
            text=text.strip(),
            metadata={
                "doc_type": "entity_profile",
                "entity_type": "Company",
                "entity_id": entity_id,
                "risk_score": risk,
                "risk_level": risk_level,
                "is_offshore": company.get("is_offshore", False),
                "is_shell": company.get("is_shell", False),
                "fraud_ring_id": None,
            },
        )

    def _account_to_doc(self, account: dict) -> Optional[Document]:
        entity_id = account.get("id", "")
        if not entity_id:
            return None

        risk = account.get("risk_score", 0.0)
        text = (
            f"Account {entity_id}: Type {account.get('account_type', 'Unknown')}. "
            f"Risk Score: {risk:.2f}. "
            f"Owner: {account.get('owner_id', 'Unknown')} ({account.get('owner_type', 'Unknown')}). "
        )
        if account.get("balance"):
            text += f"Balance: ${account['balance']:,.2f}. "
        if account.get("currency"):
            text += f"Currency: {account['currency']}. "
        if account.get("velocity_score"):
            text += f"Velocity Score: {account['velocity_score']:.2f}."

        return Document(
            id=f"entity::{entity_id}",
            text=text.strip(),
            metadata={
                "doc_type": "entity_profile",
                "entity_type": "Account",
                "entity_id": entity_id,
                "risk_score": risk,
                "fraud_ring_id": None,
            },
        )

    def _address_to_doc(self, address: dict) -> Optional[Document]:
        entity_id = address.get("id", "")
        if not entity_id:
            return None

        risk = address.get("risk_score", 0.0)
        flags = []
        if address.get("is_shell_location"):
            flags.append("SHELL_LOCATION")
        if address.get("is_known_fraud_hub"):
            flags.append("FRAUD_HUB")
        flags_str = f" [{', '.join(flags)}]" if flags else ""

        text = (
            f"Address {entity_id}: "
            f"{address.get('street_address', '')}, {address.get('city', '')}, "
            f"{address.get('state', '')} {address.get('postal_code', '')}, "
            f"{address.get('country', '')}. "
            f"Risk Score: {risk:.2f}.{flags_str}"
        )

        return Document(
            id=f"entity::{entity_id}",
            text=text.strip(),
            metadata={
                "doc_type": "entity_profile",
                "entity_type": "Address",
                "entity_id": entity_id,
                "risk_score": risk,
                "is_shell_location": address.get("is_shell_location", False),
                "fraud_ring_id": None,
            },
        )

    def _build_transaction_docs(self) -> list[Document]:
        docs = []
        for txn in self.dataset.transactions[:5000]:
            txn_id = txn.get("id", "")
            if not txn_id:
                continue
            amount = txn.get("amount", 0)
            text = (
                f"Transaction {txn_id}: "
                f"{txn.get('transaction_type', 'UNKNOWN')} "
                f"of ${amount:,.2f} {txn.get('currency', 'USD')} "
                f"from {txn.get('from_account', '?')} to {txn.get('to_account', '?')}. "
                f"Date: {txn.get('timestamp', 'Unknown')}. "
                f"Status: {txn.get('status', 'Unknown')}."
            )
            if txn.get("is_suspicious"):
                text += " FLAGGED AS SUSPICIOUS."
            docs.append(Document(
                id=f"txn::{txn_id}",
                text=text.strip(),
                metadata={
                    "doc_type": "transaction",
                    "transaction_id": txn_id,
                    "from_account": txn.get("from_account"),
                    "to_account": txn.get("to_account"),
                    "amount": amount,
                    "transaction_type": txn.get("transaction_type"),
                    "is_suspicious": txn.get("is_suspicious", False),
                    "fraud_ring_id": txn.get("fraud_ring_id"),
                },
            ))
        return docs

    def _build_authored_docs(self) -> list[Document]:
        docs = []
        for i, ring in enumerate(self.dataset.fraud_rings[:100]):
            ring_id = ring.get("id", f"FR-{i+1:03d}")
            ring_type = ring.get("type", ring.get("ring_type", "UNKNOWN"))
            severity = ring.get("severity", "MEDIUM")
            description = ring.get("description", f"{ring_type} fraud ring {ring_id}")
            entities = ring.get("entities", [])
            key_entities = ring.get("key_entities", [])

            text = (
                f"Fraud Ring {ring_id}: {description}. "
                f"Type: {ring_type}. Severity: {severity}. "
            )
            if entities:
                text += f"Involved entities ({len(entities)}): {', '.join(entities[:10])}."
                if len(entities) > 10:
                    text += f" and {len(entities) - 10} more."
            if key_entities:
                text += f" Key entities: {', '.join(key_entities)}."
            if ring.get("traversal_paths"):
                paths = ring["traversal_paths"]
                text += f" Fraud paths: {len(paths)} paths detected."
                for j, path in enumerate(paths[:3]):
                    if isinstance(path, list):
                        text += f" Path {j+1}: {' -> '.join(path[:5])}"
                        if len(path) > 5:
                            text += f" -> ... ({len(path)} hops)"
                        text += "."

            docs.append(Document(
                id=f"authored::FR_{ring_id}",
                text=text.strip(),
                metadata={
                    "doc_type": "authored",
                    "fraud_ring_id": ring_id,
                    "ring_type": ring_type,
                    "severity": severity,
                    "entity_count": len(entities),
                },
            ))
        return docs

    def build_for_entities(self, entity_ids: list[str]) -> list[Document]:
        docs = []
        for eid in entity_ids:
            entity = self.dataset.get_entity_by_id(eid)
            if not entity:
                continue
            prefix = eid.split("-")[0] if "-" in eid else ""
            if prefix == "P-":
                doc = self._person_to_doc(entity)
            elif prefix == "C-":
                doc = self._company_to_doc(entity)
            elif prefix == "A-":
                doc = self._account_to_doc(entity)
            elif prefix == "ADDR-":
                doc = self._address_to_doc(entity)
            else:
                continue
            if doc:
                docs.append(doc)
        return docs