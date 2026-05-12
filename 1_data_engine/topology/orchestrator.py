"""
Topology Orchestrator - Coordinates all topology injectors
"""
import random
from typing import List, Dict

from ..schemas.entity_registry import EntityRegistry
from ..utils.logger import get_logger
from .base_topology import TopologyResult

from .circular_ownership import CircularOwnershipInjector
from .funnel_account import FunnelAccountInjector
from .smurfing_pattern import SmurfingInjector
from .laundering_chain import LaunderingChainInjector
from .address_collision import AddressCollisionInjector
from .offshore_routing import OffshoreRoutingInjector
from .central_hub import CentralHubInjector
from .dormant_burst import DormantBurstInjector
from .beneficial_ownership import BeneficialOwnershipInjector
from .semantic_trap import SemanticTrapInjector
from .hybrid_network import HybridNetworkInjector
from .temporal_spike import TemporalSpikeInjector

logger = get_logger(__name__)


class TopologyOrchestrator:
    """
    Orchestrates fraud topology injection across all injector types.

    Executes injectors in sequence:
    1. Circular ownership rings
    2. Funnel accounts
    3. Smurfing patterns
    4. Laundering chains
    5. Address collisions
    6. Offshore routing
    7. Central hub
    8. Dormant burst
    9. Beneficial ownership
    10. Semantic traps
    11. Hybrid networks
    12. Temporal spikes
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.injectors = self._build_injectors()
        self.results: List[TopologyResult] = []

    def _build_injectors(self) -> Dict[str, any]:
        """Build all topology injectors"""
        return {
            "circular_ownership": CircularOwnershipInjector(seed=self.seed),
            "funnel_account": FunnelAccountInjector(seed=self.seed + 1),
            "smurfing": SmurfingInjector(seed=self.seed + 2),
            "laundering_chain": LaunderingChainInjector(seed=self.seed + 3),
            "address_collision": AddressCollisionInjector(seed=self.seed + 4),
            "offshore_routing": OffshoreRoutingInjector(seed=self.seed + 5),
            "central_hub": CentralHubInjector(seed=self.seed + 6),
            "dormant_burst": DormantBurstInjector(seed=self.seed + 7),
            "beneficial_ownership": BeneficialOwnershipInjector(seed=self.seed + 8),
            "semantic_trap": SemanticTrapInjector(seed=self.seed + 9),
            "hybrid_network": HybridNetworkInjector(seed=self.seed + 10),
            "temporal_spike": TemporalSpikeInjector(seed=self.seed + 11),
        }

    def inject_all(self, registry: EntityRegistry) -> Dict[str, TopologyResult]:
        """
        Execute all topology injectors.

        Args:
            registry: Entity registry with generated entities

        Returns:
            Dictionary of injector name to result
        """
        logger.info("Starting fraud topology injection...")

        results = {}
        total_edges = 0
        total_entities = set()

        injector_order = [
            "circular_ownership",
            "funnel_account",
            "smurfing",
            "laundering_chain",
            "address_collision",
            "offshore_routing",
            "central_hub",
            "dormant_burst",
            "beneficial_ownership",
            "semantic_trap",
            "hybrid_network",
            "temporal_spike",
        ]

        for injector_name in injector_order:
            injector = self.injectors[injector_name]
            logger.info(f"  Injecting: {injector_name}")

            result = injector.inject(registry)
            results[injector_name] = result

            if result.success:
                total_edges += len(result.edges_created)
                total_entities.update(result.entities_involved)
                logger.info(
                    f"    {injector_name}: {len(result.edges_created)} edges, "
                    f"{len(result.entities_involved)} entities"
                )
            else:
                logger.warning(f"    {injector_name}: {result.error_message}")

        logger.info(
            f"Topology injection complete: {total_edges} fraud edges, "
            f"{len(total_entities)} unique entities"
        )
        logger.info(f"Total fraud rings: {registry.get_fraud_ring_count()}")

        self.results = list(results.values())
        return results

    def get_injector(self, name: str):
        """Get a specific injector by name"""
        return self.injectors.get(name)

    def get_statistics(self) -> Dict:
        """Get injection statistics"""
        return {
            "total_injectors": len(self.injectors),
            "successful_injections": sum(1 for r in self.results if r.success),
            "failed_injections": sum(1 for r in self.results if not r.success),
            "total_edges": sum(len(r.edges_created) for r in self.results),
            "total_entities": len(set(e for r in self.results for e in r.entities_involved)),
        }