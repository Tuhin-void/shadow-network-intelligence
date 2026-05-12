"""
Seed Manager - Deterministic seed propagation for reproducible generation
"""
import random
from typing import Optional, Dict
from dataclasses import dataclass


@dataclass
class SeedManager:
    """
    Manages deterministic seed propagation for reproducible synthetic data generation.

    Usage:
        seed_mgr = SeedManager(global_seed=42)

        # Generate component seeds
        person_seed = seed_mgr.get_seed("person")
        company_seed = seed_mgr.get_seed("company")

        # Each component uses its seed for deterministic generation
        person_gen = PersonGenerator(seed=person_seed)
    """

    global_seed: int = 42
    _component_seeds: Dict[str, int] = None

    def __post_init__(self):
        self._component_seeds = {}
        random.seed(self.global_seed)

    def get_seed(self, component: str, offset: int = 0) -> int:
        """
        Get a deterministic seed for a component.

        Args:
            component: Component name (e.g., "person", "company", "topology")
            offset: Optional offset for variations

        Returns:
            Deterministic seed for the component
        """
        if component not in self._component_seeds:
            self._component_seeds[component] = self._derive_seed(component)

        return self._component_seeds[component] + offset

    def _derive_seed(self, component: str) -> int:
        """Derive a unique seed from global seed and component name"""
        base = f"{self.global_seed}_{component}"
        seed_val = hash(base) % (2**31)
        return seed_val

    def reset(self) -> None:
        """Reset the seed manager to initial state"""
        self._component_seeds = {}
        random.seed(self.global_seed)

    def fork(self, branch: str) -> "SeedManager":
        """
        Create a forked seed manager for parallel generation branches.

        Args:
            branch: Branch identifier

        Returns:
            New SeedManager with derived seed
        """
        branch_seed = self.get_seed(branch)
        return SeedManager(global_seed=branch_seed)

    def get_all_seeds(self) -> Dict[str, int]:
        """Get all component seeds"""
        return self._component_seeds.copy()


class DeterministicRandom:
    """
    Wrapper around random.Random with seed management.

    Usage:
        rng = DeterministicRandom(seed=42)
        value = rng.random()
        choice = rng.choice([1, 2, 3])
    """

    def __init__(self, seed: Optional[int] = None):
        self._random = random.Random(seed)

    def random(self) -> float:
        return self._random.random()

    def uniform(self, a: float, b: float) -> float:
        return self._random.uniform(a, b)

    def randint(self, a: int, b: int) -> int:
        return self._random.randint(a, b)

    def choice(self, seq: list):
        return self._random.choice(seq)

    def sample(self, seq: list, k: int):
        return self._random.sample(seq, k)

    def shuffle(self, seq: list):
        return self._random.shuffle(seq)

    def gauss(self, mu: float, sigma: float) -> float:
        return self._random.gauss(mu, sigma)

    def normalvariate(self, mu: float, sigma: float) -> float:
        return self._random.normalvariate(mu, sigma)

    def seed(self, seed: int):
        self._random.seed(seed)