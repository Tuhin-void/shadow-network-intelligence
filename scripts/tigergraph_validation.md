# TigerGraph operational validation

**Status:** `HEALTHY`  •  **Elapsed:** 6.36s

- Host: `https://tg-6937a943-57ef-4bc3-88b0-3bce0d9a3290.tg-2635877100.i.tgcloud.io`
- Offline mode: `False`
- Vertex types in schema: 7
- Edge types in schema:   19

## Vertex counts

| type | count |
|---|---|
| `Person` | 6000 |
| `Company` | 5000 |
| `Account` | 10000 |
| `Address` | 4000 |
| `Device` | 150 |
| `Transaction` | 150054 |

**Total vertices:** 175,204

## Edge counts

| edge | count |
|---|---|
| `ACCESSED_FROM` | 0 |
| `ACCOUNT_MEMBER_OF_RING` | 84 |
| `ADDRESS_CONNECTED_TO_RING` | 0 |
| `ASSOCIATED_WITH` | 400 |
| `BENEFITS_FROM` | 1020 |
| `COMPANY_MEMBER_OF_RING` | 23 |
| `DEVICE_CONNECTED_TO_RING` | 0 |
| `HAS_ACCOUNT` | 10000 |
| `LOCATED_AT` | 21998 |
| `OWNS` | 10103 |
| `PERSON_MEMBER_OF_RING` | 23 |
| `RECEIVED_TRANSACTION` | 160053 |
| `REGISTERED_AT` | 0 |
| `SENT_TRANSACTION` | 160051 |
| `SHARES_ADDRESS_WITH` | 3831 |
| `SHARES_DEVICE_WITH` | 26 |
| `TRANSACTION_MEMBER_OF_RING` | 74 |
| `TRANSFERRED_TO` | 5230 |
| `USES_DEVICE` | 319 |
| `reverse_account_member_of_ring` | 84 |
| `reverse_address_connected_to_ring` | 0 |
| `reverse_company_member_of_ring` | 23 |
| `reverse_device_connected_to_ring` | 0 |
| `reverse_person_member_of_ring` | 23 |
| `reverse_transaction_member_of_ring` | 74 |

**Total edges:** 373,439

**Reverse edges observed:** 6

## Ring connectivity probe

Rings sampled: 5  •  With members: 4

| ring | edges |
|---|---|
| `FR-014` | 6 |
| `FR-006` | 19 |
| `FR-011` | 10 |
| `FR-FUNNEL-00` | 0 |
| `FR-005` | 10 |

## Installed queries

| query | status |
|---|---|
| `tg_ring_members` | installed (returned data) |
| `tg_shortest_path` | installed (returned data) |

## Cache snapshot

- hits:   0
- misses: 0
