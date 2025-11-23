"""
Model and Parameter ID generation utilities.

Provides consistent identification for models and their parameter sets.
"""

import hashlib
import json
import inspect
from typing import Dict, Any, Optional


def generate_param_id(parameters: Dict[str, Any]) -> str:
    """
    Generate a short, deterministic ID for a parameter set.

    Args:
        parameters: Dictionary of parameter names and values

    Returns:
        Parameter ID in format 'p-XXXXXXXX' (8 char hash)
    """
    # Sort parameters for deterministic hashing
    sorted_params = json.dumps(parameters, sort_keys=True, default=str)

    # Generate SHA256 hash and take first 8 characters
    hash_digest = hashlib.sha256(sorted_params.encode()).hexdigest()[:8]

    return f"p-{hash_digest}"


def generate_model_hash(model_class_or_source: Any) -> str:
    """
    Generate a hash of the model source code.

    Args:
        model_class_or_source: Either a class object or source code string

    Returns:
        Model hash in format 'm-XXXXXXXX' (8 char hash)
    """
    if isinstance(model_class_or_source, str):
        source = model_class_or_source
    else:
        try:
            source = inspect.getsource(model_class_or_source)
        except (TypeError, OSError):
            # Fallback to class name if source not available
            source = str(model_class_or_source)

    hash_digest = hashlib.sha256(source.encode()).hexdigest()[:8]
    return f"m-{hash_digest}"


def generate_model_id(model_name: str, parameters: Dict[str, Any], model_source: Optional[str] = None) -> str:
    """
    Generate a full model identifier combining model hash and parameter ID.

    Args:
        model_name: Name of the model class
        parameters: Dictionary of parameter names and values
        model_source: Optional model source code for hashing

    Returns:
        Full ID in format 'ModelName::m-XXXXXXXX::p-YYYYYYYY'
    """
    param_id = generate_param_id(parameters)

    if model_source:
        model_hash = generate_model_hash(model_source)
        return f"{model_name}::{model_hash}::{param_id}"
    else:
        return f"{model_name}::{param_id}"


def parse_model_id(full_id: str) -> tuple:
    """
    Parse a full model ID into components.

    Args:
        full_id: Full ID in format 'ModelName::p-XXXXXXXX'

    Returns:
        Tuple of (model_name, param_id)
    """
    if '::' in full_id:
        model_name, param_id = full_id.split('::', 1)
        return model_name, param_id
    return full_id, None


def get_param_summary(parameters: Dict[str, Any], max_params: int = 5) -> str:
    """
    Get a human-readable summary of key parameters.

    Args:
        parameters: Dictionary of parameter names and values
        max_params: Maximum number of parameters to include

    Returns:
        Summary string like 'mom=126, top_n=4, lev=1.4'
    """
    # Key parameters to prioritize in summary
    priority_keys = [
        'momentum_period', 'top_n_sectors', 'top_n', 'bull_leverage',
        'bear_leverage', 'min_momentum', 'atr_period', 'trailing_atr_mult',
        'take_profit_atr_mult', 'crash_exposure'
    ]

    # Short names for readability
    short_names = {
        'momentum_period': 'mom',
        'top_n_sectors': 'top_n',
        'bull_leverage': 'bull_lev',
        'bear_leverage': 'bear_lev',
        'min_momentum': 'min_mom',
        'atr_period': 'atr',
        'trailing_atr_mult': 'trail',
        'take_profit_atr_mult': 'tp',
        'crash_exposure': 'crash_exp'
    }

    # Select parameters to show
    shown = []
    for key in priority_keys:
        if key in parameters and len(shown) < max_params:
            short_key = short_names.get(key, key[:6])
            value = parameters[key]
            if isinstance(value, float):
                shown.append(f"{short_key}={value:.2g}")
            else:
                shown.append(f"{short_key}={value}")

    return ', '.join(shown) if shown else 'default'


if __name__ == '__main__':
    # Example usage
    params = {
        'momentum_period': 126,
        'top_n_sectors': 4,
        'bull_leverage': 1.4,
        'bear_leverage': 1.0,
        'min_momentum': 0.1,
        'atr_period': 21,
        'crash_exposure': 0.25
    }

    param_id = generate_param_id(params)
    full_id = generate_model_id('SectorRotationConsistent_v3', params)
    summary = get_param_summary(params)

    print(f"Parameter ID: {param_id}")
    print(f"Full Model ID: {full_id}")
    print(f"Parameter Summary: {summary}")
