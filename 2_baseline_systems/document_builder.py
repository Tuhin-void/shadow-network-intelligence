"""
Hybrid chunking: turns the loaded ShadowDataset into vector-RAG documents.

Three document families are produced, sharing a uniform shape:
    {"id": str, "text": str, "metadata": dict}

  * entity profile cards   — one per Person/Company/Account/Address, with linked
                             ownership / account / address relationships rolled
                             into natural language.
  * transaction event docs — one per Transaction, with party names resolved.
  * authored semantic docs — passed through verbatim from semantic_documents.json.
"""
from __future__ import annotations

from typing import Any

from .data_loader import ShadowDataset


Document = dict[str, Any]


def _person_card(person: dict, ds: ShadowDataset, idx: dict[str, dict]) -> Document:
    pid = person["person_id"]
    owned = [e for e in ds.owns_edges if e["from_id"] == pid]
    accounts = [e for e in ds.has_account_edges if e["entity_id"] == pid]

    lines = [
        f"Person {pid}: {person['name']}.",
        f"Nationality: {person.get('nationality', 'unknown')}. "
        f"Date of birth: {person.get('dob', 'unknown')}.",
        f"Risk score: {person.get('risk_score', 'n/a')}. "
        f"PEP: {person.get('pep_flag', 'False')}. "
        f"Sanctions: {person.get('sanctions_flag', 'False')}.",
    ]
    for edge in owned:
        target = idx.get(edge["to_id"], {})
        lines.append(
            f"Owns {edge['to_id']} ({target.get('name', '?')}) "
            f"at {edge.get('ownership_percent', '?')}% since {edge.get('start_date', '?')}."
        )
    for edge in accounts:
        acct = idx.get(edge["account_id"], {})
        lines.append(
            f"Holds account {edge['account_id']} "
            f"({acct.get('bank_name', '?')}, balance {acct.get('balance', '?')} {acct.get('currency', '')})."
        )

    return {
        "id": f"entity::{pid}",
        "text": " ".join(lines),
        "metadata": {"doc_type": "entity_profile", "entity_type": "Person", "entity_id": pid},
    }


def _company_card(company: dict, ds: ShadowDataset, idx: dict[str, dict]) -> Document:
    cid = company["company_id"]
    owned_by = [e for e in ds.owns_edges if e["to_id"] == cid]
    owns = [e for e in ds.owns_edges if e["from_id"] == cid]
    accounts = [e for e in ds.has_account_edges if e["entity_id"] == cid]
    addresses = [e for e in ds.located_at_edges if e["entity_id"] == cid]

    lines = [
        f"Company {cid}: {company['name']}.",
        f"Country: {company.get('country', '?')}. "
        f"Industry: {company.get('industry', '?')}. "
        f"Registered: {company.get('registration_date', '?')}.",
        f"Risk score: {company.get('risk_score', 'n/a')}.",
    ]
    for edge in owned_by:
        owner = idx.get(edge["from_id"], {})
        lines.append(
            f"Owned by {edge['from_id']} ({owner.get('name', '?')}) "
            f"at {edge.get('ownership_percent', '?')}%."
        )
    for edge in owns:
        target = idx.get(edge["to_id"], {})
        lines.append(
            f"Owns {edge['to_id']} ({target.get('name', '?')}) "
            f"at {edge.get('ownership_percent', '?')}%."
        )
    for edge in accounts:
        acct = idx.get(edge["account_id"], {})
        lines.append(
            f"Holds account {edge['account_id']} at {acct.get('bank_name', '?')} "
            f"(balance {acct.get('balance', '?')} {acct.get('currency', '')})."
        )
    for edge in addresses:
        addr = idx.get(edge["address_id"], {})
        lines.append(
            f"Located at {edge['address_id']}: {addr.get('full_address', '?')} "
            f"({addr.get('address_type', '?')}, risk {addr.get('risk_level', '?')})."
        )

    return {
        "id": f"entity::{cid}",
        "text": " ".join(lines),
        "metadata": {"doc_type": "entity_profile", "entity_type": "Company", "entity_id": cid},
    }


def _account_card(account: dict, ds: ShadowDataset, idx: dict[str, dict]) -> Document:
    aid = account["account_id"]
    held_by = [e for e in ds.has_account_edges if e["account_id"] == aid]
    outgoing = [t for t in ds.transactions if t["from_account"] == aid]
    incoming = [t for t in ds.transactions if t["to_account"] == aid]

    lines = [
        f"Account {aid} at {account.get('bank_name', '?')}.",
        f"Currency: {account.get('currency', '?')}. "
        f"Balance: {account.get('balance', '?')}. "
        f"Opened: {account.get('opened_date', '?')}. "
        f"Risk score: {account.get('risk_score', 'n/a')}.",
    ]
    for edge in held_by:
        holder = idx.get(edge["entity_id"], {})
        lines.append(f"Held by {edge['entity_id']} ({holder.get('name', '?')}).")
    if outgoing:
        lines.append(f"Outgoing transactions: {len(outgoing)}.")
    if incoming:
        lines.append(f"Incoming transactions: {len(incoming)}.")

    return {
        "id": f"entity::{aid}",
        "text": " ".join(lines),
        "metadata": {"doc_type": "entity_profile", "entity_type": "Account", "entity_id": aid},
    }


def _address_card(address: dict, ds: ShadowDataset, idx: dict[str, dict]) -> Document:
    addr_id = address["address_id"]
    occupants = [e for e in ds.located_at_edges if e["address_id"] == addr_id]

    lines = [
        f"Address {addr_id}: {address.get('full_address', '?')}.",
        f"Country: {address.get('country', '?')}. "
        f"Type: {address.get('address_type', '?')}. "
        f"Risk level: {address.get('risk_level', '?')}.",
    ]
    if len(occupants) >= 2:
        lines.append(
            f"ADDRESS COLLISION: shared by {len(occupants)} entities — "
            + ", ".join(f"{e['entity_id']} ({idx.get(e['entity_id'], {}).get('name', '?')})" for e in occupants)
            + "."
        )
    elif occupants:
        e = occupants[0]
        lines.append(f"Used by {e['entity_id']} ({idx.get(e['entity_id'], {}).get('name', '?')}).")

    return {
        "id": f"entity::{addr_id}",
        "text": " ".join(lines),
        "metadata": {"doc_type": "entity_profile", "entity_type": "Address", "entity_id": addr_id},
    }


def _transaction_doc(txn: dict, idx: dict[str, dict], ds: ShadowDataset) -> Document:
    tid = txn["transaction_id"]
    src = idx.get(txn["from_account"], {})
    dst = idx.get(txn["to_account"], {})

    src_holder_edges = [e for e in ds.has_account_edges if e["account_id"] == txn["from_account"]]
    dst_holder_edges = [e for e in ds.has_account_edges if e["account_id"] == txn["to_account"]]
    src_holder = idx.get(src_holder_edges[0]["entity_id"], {}) if src_holder_edges else {}
    dst_holder = idx.get(dst_holder_edges[0]["entity_id"], {}) if dst_holder_edges else {}

    text = (
        f"Transaction {tid}: {txn.get('amount', '?')} {txn.get('currency', '')} "
        f"transferred via {txn.get('transaction_type', '?')} on {txn.get('timestamp', '?')}. "
        f"From account {txn['from_account']} at {src.get('bank_name', '?')} "
        f"(held by {src_holder.get('name', '?')}) "
        f"to account {txn['to_account']} at {dst.get('bank_name', '?')} "
        f"(held by {dst_holder.get('name', '?')}). "
        f"Risk score: {txn.get('risk_score', 'n/a')}."
    )

    return {
        "id": f"txn::{tid}",
        "text": text,
        "metadata": {
            "doc_type": "transaction",
            "transaction_id": tid,
            "from_account": txn["from_account"],
            "to_account": txn["to_account"],
            "amount": txn.get("amount"),
            "transaction_type": txn.get("transaction_type"),
        },
    }


def _authored_doc(doc: dict) -> Document:
    return {
        "id": f"authored::{doc['document_id']}",
        "text": f"{doc.get('title', '')}\n\n{doc.get('content', '')}",
        "metadata": {
            "doc_type": "authored",
            "document_id": doc["document_id"],
            "entity_id": doc.get("entity_id"),
            "title": doc.get("title"),
        },
    }


def build_documents(ds: ShadowDataset) -> list[Document]:
    idx = ds.entity_index()
    docs: list[Document] = []

    for person in ds.persons:
        docs.append(_person_card(person, ds, idx))
    for company in ds.companies:
        docs.append(_company_card(company, ds, idx))
    for account in ds.accounts:
        docs.append(_account_card(account, ds, idx))
    for address in ds.addresses:
        docs.append(_address_card(address, ds, idx))
    for txn in ds.transactions:
        docs.append(_transaction_doc(txn, idx, ds))
    for doc in ds.semantic_documents:
        docs.append(_authored_doc(doc))

    return docs


if __name__ == "__main__":
    from .data_loader import load_dataset
    ds = load_dataset()
    docs = build_documents(ds)
    print(f"Built {len(docs)} documents")
    for d in docs[:3]:
        print(f"\n--- {d['id']} ({d['metadata']['doc_type']}) ---")
        print(d["text"])
