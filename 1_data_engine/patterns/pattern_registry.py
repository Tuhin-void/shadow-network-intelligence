"""
Pattern Registry - Central registry for all fraud patterns
"""
from typing import Dict, List, Optional
from .pattern_definition import PatternConfig, PATTERN_CONFIGS, PatternType, Severity


class PatternRegistry:
    """Registry for fraud detection patterns"""

    _patterns: Dict[str, PatternConfig] = PATTERN_CONFIGS

    @classmethod
    def register(cls, name: str, config: PatternConfig) -> None:
        """Register a new pattern"""
        cls._patterns[name] = config

    @classmethod
    def get(cls, name: str) -> Optional[PatternConfig]:
        """Get pattern by name"""
        return cls._patterns.get(name)

    @classmethod
    def get_all(cls) -> List[PatternConfig]:
        """Get all patterns"""
        return list(cls._patterns.values())

    @classmethod
    def get_by_severity(cls, severity: str) -> List[PatternConfig]:
        """Get patterns by severity"""
        return [p for p in cls._patterns.values() if p.severity == severity]

    @classmethod
    def get_by_type(cls, pattern_type: PatternType) -> List[PatternConfig]:
        """Get patterns by type"""
        return [p for p in cls._patterns.values() if p.type == pattern_type]

    @classmethod
    def get_critical(cls) -> List[PatternConfig]:
        """Get critical severity patterns"""
        return cls.get_by_severity("CRITICAL")

    @classmethod
    def get_high(cls) -> List[PatternConfig]:
        """Get high severity patterns"""
        return cls.get_by_severity("HIGH")