"""
Config Package - Configuration loaders
"""
import os
from pathlib import Path
import yaml
from typing import Dict, Any, Optional


class ConfigLoader:
    """Configuration loader for YAML config files"""

    _cache: Dict[str, Any] = {}

    @classmethod
    def load_yaml(cls, filename: str, cache: bool = True) -> Dict[str, Any]:
        """Load a YAML configuration file"""
        if cache and filename in cls._cache:
            return cls._cache[filename]

        config_dir = Path(__file__).parent
        config_path = config_dir / filename

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        if cache:
            cls._cache[filename] = config

        return config

    @classmethod
    def get_profile(cls, profile_name: str) -> Dict[str, Any]:
        """Get a generation profile configuration"""
        profiles = cls.load_yaml("profiles.yaml")
        return profiles.get("profiles", {}).get(profile_name, profiles["profiles"]["hackathon_default"])

    @classmethod
    def get_regions(cls) -> Dict[str, Any]:
        """Get regional distribution configuration"""
        return cls.load_yaml("regions.yaml")

    @classmethod
    def get_industries(cls) -> Dict[str, Any]:
        """Get industry configuration"""
        return cls.load_yaml("industries.yaml")

    @classmethod
    def get_fraud_scenarios(cls) -> Dict[str, Any]:
        """Get fraud scenario configuration"""
        return cls.load_yaml("fraud_scenarios.yaml")

    @classmethod
    def get_noise_config(cls) -> Dict[str, Any]:
        """Get semantic noise configuration"""
        return cls.load_yaml("noise_config.yaml")


__all__ = ["ConfigLoader"]