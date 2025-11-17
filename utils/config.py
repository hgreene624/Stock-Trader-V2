"""
YAML configuration loader with merge semantics for experiment overrides.

Supports:
- Loading base configuration from YAML
- Merging experiment overrides
- Validation using pydantic models
- Environment variable expansion
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, ValidationError


class ConfigLoader:
    """
    YAML configuration loader with merge semantics.

    Allows experiment configs to override base configs using
    deep dictionary merging.
    """

    @staticmethod
    def load_yaml(file_path: str) -> Dict[str, Any]:
        """
        Load YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed YAML as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        # Expand environment variables
        return ConfigLoader._expand_env_vars(config)

    @staticmethod
    def _expand_env_vars(obj: Any) -> Any:
        """
        Recursively expand environment variables in config.

        Supports ${VAR_NAME} or $VAR_NAME syntax.

        Args:
            obj: Config object (dict, list, or primitive)

        Returns:
            Object with environment variables expanded
        """
        if isinstance(obj, dict):
            return {k: ConfigLoader._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ConfigLoader._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Expand ${VAR} or $VAR
            if obj.startswith('${') and obj.endswith('}'):
                var_name = obj[2:-1]
                return os.getenv(var_name, obj)
            elif obj.startswith('$'):
                var_name = obj[1:]
                return os.getenv(var_name, obj)
        return obj

    @staticmethod
    def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.

        Override values take precedence. Nested dicts are merged recursively.
        Lists are replaced (not merged).

        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary

        Returns:
            Merged dictionary

        Example:
            >>> base = {"a": 1, "b": {"c": 2, "d": 3}}
            >>> override = {"b": {"c": 99}, "e": 4}
            >>> deep_merge(base, override)
            {"a": 1, "b": {"c": 99, "d": 3}, "e": 4}
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                result[key] = ConfigLoader.deep_merge(result[key], value)
            else:
                # Override value (including lists)
                result[key] = value

        return result

    @staticmethod
    def load_with_overrides(
        base_config_path: str,
        override_config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load base config and optionally merge with override config.

        Args:
            base_config_path: Path to base YAML config
            override_config_path: Optional path to override YAML config

        Returns:
            Merged configuration dictionary

        Example:
            # Load base config only
            config = ConfigLoader.load_with_overrides("configs/base/system.yaml")

            # Load base + experiment override
            config = ConfigLoader.load_with_overrides(
                "configs/base/system.yaml",
                "configs/experiments/trend_sweep.yaml"
            )
        """
        # Load base config
        base_config = ConfigLoader.load_yaml(base_config_path)

        # If no override, return base
        if override_config_path is None:
            return base_config

        # Load and merge override
        override_config = ConfigLoader.load_yaml(override_config_path)
        return ConfigLoader.deep_merge(base_config, override_config)

    @staticmethod
    def validate(config: Dict[str, Any], model_class: type[BaseModel]) -> BaseModel:
        """
        Validate configuration against pydantic model.

        Args:
            config: Configuration dictionary
            model_class: Pydantic model class for validation

        Returns:
            Validated pydantic model instance

        Raises:
            ValidationError: If config doesn't match schema

        Example:
            from pydantic import BaseModel

            class SystemConfig(BaseModel):
                mode: str
                initial_nav: float

            config = {"mode": "backtest", "initial_nav": 100000.0}
            validated = ConfigLoader.validate(config, SystemConfig)
        """
        try:
            return model_class(**config)
        except ValidationError as e:
            raise ValidationError(f"Config validation failed: {e}")


def load_config(
    base_path: str,
    override_path: Optional[str] = None,
    validate_with: Optional[type[BaseModel]] = None
) -> Dict[str, Any]:
    """
    Convenience function to load and optionally validate config.

    Args:
        base_path: Path to base YAML config
        override_path: Optional path to override config
        validate_with: Optional pydantic model for validation

    Returns:
        Configuration dictionary or validated pydantic model

    Example:
        # Load without validation
        config = load_config("configs/base/system.yaml")

        # Load with experiment override
        config = load_config(
            "configs/base/system.yaml",
            override_path="configs/experiments/exp_001.yaml"
        )

        # Load with validation
        config = load_config(
            "configs/base/system.yaml",
            validate_with=SystemConfigModel
        )
    """
    config = ConfigLoader.load_with_overrides(base_path, override_path)

    if validate_with is not None:
        return ConfigLoader.validate(config, validate_with)

    return config


# Example usage
if __name__ == "__main__":
    # Test merge semantics
    base = {
        "system": {
            "mode": "backtest",
            "models": [{"name": "Model1", "budget": 0.5}],
            "risk": {"max_leverage": 1.2}
        }
    }

    override = {
        "system": {
            "mode": "paper",
            "risk": {"max_leverage": 1.0, "drawdown_trigger": 0.15}
        }
    }

    merged = ConfigLoader.deep_merge(base, override)
    print("Merged config:")
    print(yaml.dump(merged, default_flow_style=False))
