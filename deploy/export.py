"""
Model Export CLI for VPS Deployment.

Exports models as standalone packages ready for production deployment.

Usage:
    python -m deploy.export --models SectorRotationModel_v1 --stage live

Output Structure:
    production/models/
        SectorRotationModel_v1/
            model.py          # Model source code
            params.json       # Model parameters
            universe.json     # Symbol universe
            manifest.json     # Metadata (version, date, class name, etc.)
"""

import argparse
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelExporter:
    """Export models for production deployment."""

    def __init__(self, project_root: Path = None):
        """
        Initialize model exporter.

        Args:
            project_root: Project root directory (defaults to current dir parent parent)
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent

        self.project_root = project_root
        self.models_dir = project_root / 'models'
        self.configs_dir = project_root / 'configs'
        self.output_dir = project_root / 'production' / 'models'
        self.lifecycle_file = self.configs_dir / '.model_lifecycle.json'

        logger.info(f"Initialized ModelExporter (project={project_root})")

    def _load_lifecycle_states(self) -> Dict:
        """Load model lifecycle states."""
        if not self.lifecycle_file.exists():
            logger.warning(f"Lifecycle file not found: {self.lifecycle_file}")
            return {}

        with open(self.lifecycle_file, 'r') as f:
            return json.load(f)

    def _load_profiles(self) -> Dict:
        """Load test profiles configuration."""
        profiles_file = self.configs_dir / 'profiles.yaml'

        if not profiles_file.exists():
            logger.warning(f"Profiles file not found: {profiles_file}")
            return {}

        with open(profiles_file, 'r') as f:
            data = yaml.safe_load(f)

        # Extract 'profiles' key if it exists, otherwise return the whole dict
        return data.get('profiles', data) if isinstance(data, dict) else {}

    def _find_model_file(self, model_name: str) -> Path:
        """Find model source file."""
        # Try common patterns
        patterns = [
            f"{model_name.lower()}.py",
            f"{model_name}.py",
            # Handle versioned models (e.g., SectorRotationModel_v1 -> sector_rotation_v1.py)
            f"{'_'.join(model_name.lower().replace('model', '').split('_'))}.py",
        ]

        for pattern in patterns:
            model_file = self.models_dir / pattern
            if model_file.exists():
                return model_file

        # Search all files
        for model_file in self.models_dir.glob('*.py'):
            # Read file and check for class definition
            with open(model_file, 'r') as f:
                content = f.read()
                if f'class {model_name}' in content:
                    return model_file

        raise FileNotFoundError(f"Could not find model file for {model_name}")

    def _extract_model_info(self, model_name: str, model_file: Path) -> Dict:
        """
        Extract model information from source file.

        Returns:
            Dict with class_name, parameters, etc.
        """
        # Read source file to find class name
        with open(model_file, 'r') as f:
            content = f.read()

        # Extract class name (simple regex would work, but let's keep it simple)
        import re
        class_match = re.search(rf'class\s+({model_name}\w*)\s*\(', content)

        if not class_match:
            raise ValueError(f"Could not find class definition for {model_name} in {model_file}")

        class_name = class_match.group(1)

        return {
            'class_name': class_name,
            'source_file': model_file,
        }

    def _get_model_parameters_from_profile(self, model_name: str) -> Dict:
        """Get model parameters from profiles.yaml."""
        profiles = self._load_profiles()

        # Find profile matching this model
        for profile_name, profile_config in profiles.items():
            if profile_config.get('model') == model_name:
                params = profile_config.get('parameters', {})
                universe = profile_config.get('universe', [])

                return {
                    'parameters': params,
                    'universe': universe,
                    'profile_name': profile_name,
                }

        # Not found in profiles
        logger.warning(f"No profile found for {model_name}, using empty parameters")
        return {
            'parameters': {},
            'universe': [],
            'profile_name': None,
        }

    def export_model(
        self,
        model_name: str,
        stage: str = 'live',
        budget_fraction: float = None
    ) -> Path:
        """
        Export a single model for production deployment.

        Args:
            model_name: Model name (e.g., "SectorRotationModel_v1")
            stage: Required lifecycle stage ('live', 'paper', or 'candidate')
            budget_fraction: Model budget fraction (defaults to equal split)

        Returns:
            Path to exported model directory
        """
        logger.info(f"Exporting model: {model_name} (stage={stage})")

        # Validate lifecycle stage
        lifecycle_states = self._load_lifecycle_states()
        current_stage = lifecycle_states.get(model_name, {}).get('stage', 'research')

        if current_stage != stage:
            logger.warning(
                f"Model {model_name} is at stage '{current_stage}', "
                f"but you requested '{stage}'. Proceeding anyway..."
            )

        # Find model file
        model_file = self._find_model_file(model_name)
        logger.info(f"Found model source: {model_file}")

        # Extract model info
        model_info = self._extract_model_info(model_name, model_file)
        logger.info(f"Extracted class name: {model_info['class_name']}")

        # Get parameters from profile
        param_info = self._get_model_parameters_from_profile(model_name)
        logger.info(f"Parameters: {param_info['parameters']}")
        logger.info(f"Universe: {param_info['universe']}")

        # Create output directory
        model_output_dir = self.output_dir / model_name
        model_output_dir.mkdir(parents=True, exist_ok=True)

        # Copy model source file
        shutil.copy(model_file, model_output_dir / 'model.py')
        logger.info(f"Copied model source to {model_output_dir / 'model.py'}")

        # Write parameters.json
        params_file = model_output_dir / 'params.json'
        with open(params_file, 'w') as f:
            json.dump(param_info['parameters'], f, indent=2)
        logger.info(f"Wrote parameters to {params_file}")

        # Write universe.json
        universe_file = model_output_dir / 'universe.json'
        with open(universe_file, 'w') as f:
            json.dump(param_info['universe'], f, indent=2)
        logger.info(f"Wrote universe to {universe_file}")

        # Create manifest
        manifest = {
            'model_name': model_name,
            'class_name': model_info['class_name'],
            'stage': stage,
            'parameters': param_info['parameters'],
            'universe': param_info['universe'],
            'budget_fraction': budget_fraction,
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'exported_from_profile': param_info['profile_name'],
            'source_file': str(model_file.relative_to(self.project_root)),
        }

        manifest_file = model_output_dir / 'manifest.json'
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Wrote manifest to {manifest_file}")

        logger.info(f"✅ Successfully exported {model_name} to {model_output_dir}")
        return model_output_dir

    def export_models(
        self,
        model_names: List[str],
        stage: str = 'live',
        equal_budget: bool = True
    ) -> List[Path]:
        """
        Export multiple models.

        Args:
            model_names: List of model names to export
            stage: Required lifecycle stage
            equal_budget: If True, assign equal budget fractions (1/N each)

        Returns:
            List of paths to exported model directories
        """
        logger.info(f"Exporting {len(model_names)} models")

        budget_fraction = 1.0 / len(model_names) if equal_budget else None

        exported_paths = []

        for model_name in model_names:
            try:
                path = self.export_model(
                    model_name=model_name,
                    stage=stage,
                    budget_fraction=budget_fraction
                )
                exported_paths.append(path)
            except Exception as e:
                logger.error(f"Failed to export {model_name}: {e}")
                continue

        logger.info(f"✅ Exported {len(exported_paths)}/{len(model_names)} models successfully")
        return exported_paths


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Export models for production VPS deployment'
    )

    parser.add_argument(
        '--models',
        nargs='+',
        required=True,
        help='Model names to export (e.g., SectorRotationModel_v1)'
    )

    parser.add_argument(
        '--stage',
        choices=['live', 'paper', 'candidate'],
        default='live',
        help='Required lifecycle stage (default: live)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        help='Output directory (default: production/models/)'
    )

    parser.add_argument(
        '--no-equal-budget',
        action='store_true',
        help='Do not assign equal budget fractions'
    )

    args = parser.parse_args()

    # Initialize exporter
    exporter = ModelExporter()

    if args.output:
        exporter.output_dir = args.output

    # Export models
    exported_paths = exporter.export_models(
        model_names=args.models,
        stage=args.stage,
        equal_budget=not args.no_equal_budget
    )

    # Summary
    print("\n" + "=" * 80)
    print("EXPORT SUMMARY")
    print("=" * 80)
    print(f"Exported {len(exported_paths)} models:")
    for path in exported_paths:
        print(f"  ✅ {path.name}")
    print("\n" + "=" * 80)
    print("Next steps:")
    print("  1. Run: cd production/deploy && ./build.sh")
    print("  2. Run: ./deploy.sh your-vps-hostname")
    print("=" * 80)


if __name__ == '__main__':
    main()
