"""Path-aware retriever — finds paths and traversal patterns between entities."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PathResult:
    path: list[str]
    path_edges: list[str]
    path_length: int
    total_risk: float
    entities: list[dict] = field(default_factory=list)


class PathAwareRetriever:
    """
    Finds paths and relationships between entities in the graph.
    - Shortest path between two entities
    - Multi-hop path enumeration
    - Layering chain detection
    """

    def __init__(self, graph_client: "GraphClient"):
        self.client = graph_client

    def find_path(
        self,
        from_id: str,
        to_id: str,
        max_hops: int = 5,
    ) -> Optional[PathResult]:
        """Find the shortest path between two entities."""
        result = self.client.run_installed_query(
            "tg_shortest_path",
            {"from_id": from_id, "to_id": to_id, "max_hops": max_hops},
        )

        if "error" not in result or not result.get("results"):
            path_vertices = []
            path_edges = []
            seen_ids = set()
            frontier = [from_id]
            seen_ids.add(from_id)

            for _ in range(max_hops):
                next_frontier = []
                for fid in frontier:
                    neighbors = self.client.get_neighbors(fid, limit=20)
                    for n in neighbors.get("results", []):
                        n_id = n.get("v_id") or n.get("id") or ""
                        if n_id and n_id not in seen_ids:
                            path_vertices.append(n_id)
                            path_edges.append(n.get("edge_type", ""))
                            seen_ids.add(n_id)
                            next_frontier.append(n_id)
                            if n_id == to_id:
                                return PathResult(
                                    path=[from_id] + path_vertices,
                                    path_edges=path_edges,
                                    path_length=len(path_vertices),
                                    total_risk=sum(v.get("risk_score", 0) for v in path_vertices if isinstance(v, dict)),
                                    entities=path_vertices,
                                )
                frontier = next_frontier
                if not frontier:
                    break

        return None

    def find_all_paths(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 4,
    ) -> list[PathResult]:
        """Find all simple paths up to max_depth."""
        all_paths = []
        visited = set()

        def dfs(current: str, path: list[str], depth: int) -> None:
            if depth > max_depth:
                return
            if current == to_id:
                all_paths.append(PathResult(
                    path=path,
                    path_edges=[],
                    path_length=len(path) - 1,
                    total_risk=0.0,
                ))
                return
            visited.add(current)
            neighbors = self.client.get_neighbors(current, limit=50)
            for n in neighbors.get("results", []):
                n_id = n.get("v_id") or n.get("id") or ""
                if n_id and n_id not in visited:
                    dfs(n_id, path + [n_id], depth + 1)
            visited.remove(current)

        dfs(from_id, [from_id], 0)
        return all_paths

    def detect_layering_chain(
        self,
        from_account: str,
        to_account: str,
        min_hops: int = 3,
        max_hops: int = 7,
    ) -> dict:
        """Detect layering/smurfing transaction chains."""
        result = self.client.run_installed_query(
            "tg_layering_chain",
            {
                "from_account": from_account,
                "to_account": to_account,
                "min_hops": min_hops,
                "max_hops": max_hops,
            },
        )

        if "error" not in result:
            return {"detected": True, "analysis": result}

        paths = self.find_all_paths(from_account, to_account, max_depth=max_hops)
        valid_paths = [p for p in paths if p.path_length >= min_hops]

        return {
            "detected": len(valid_paths) > 0,
            "path_count": len(valid_paths),
            "paths": [{"length": p.path_length, "entities": p.path} for p in valid_paths],
        }

    def get_ownership_chain(self, company_id: str, max_depth: int = 4) -> list[dict]:
        """Get ownership chain from a company."""
        result = self.client.run_installed_query(
            "tg_ownership_chain",
            {"company_id": company_id, "max_depth": max_depth},
        )

        if "error" not in result:
            return result.get("results", [])

        chain = []
        visited = set()

        def _traverse(cid: str, depth: int) -> None:
            if depth > max_depth or cid in visited:
                return
            visited.add(cid)

            company = self.client.get_vertex("Company", cid)
            if company:
                chain.append({"type": "Company", "v_id": cid, "attributes": company.get("attributes", {})})

            persons = self.client.get_edges("OWNS", cid, to_type="Person")[:5]
            for p in persons:
                pid = p.get("to_id") or p.get("v_id", "")
                person = self.client.get_vertex("Person", pid)
                if person:
                    chain.append({"type": "Person", "v_id": pid, "attributes": person.get("attributes", {})})

            sub_companies = self.client.get_edges("OWNS", cid, to_type="Company")[:5]
            for sc in sub_companies:
                sc_id = sc.get("to_id") or sc.get("v_id", "")
                _traverse(sc_id, depth + 1)

        _traverse(company_id, 0)
        return chain