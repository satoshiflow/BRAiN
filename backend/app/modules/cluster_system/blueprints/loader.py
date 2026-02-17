"""
Blueprint Loader

Loads and parses YAML blueprints for cluster creation.
"""

import yaml
from typing import Dict, Any
from pathlib import Path
from loguru import logger


class BlueprintLoader:
    """
    Loads cluster blueprints from YAML files.

    Usage:
        loader = BlueprintLoader()
        blueprint = loader.load_from_file("marketing.yaml")
    """

    def __init__(self, blueprints_dir: str = "storage/blueprints"):
        self.blueprints_dir = Path(blueprints_dir)
        self.blueprints_dir.mkdir(parents=True, exist_ok=True)

    def load_from_file(self, filename: str) -> Dict[str, Any]:
        """
        Load blueprint from YAML file.

        Args:
            filename: Filename in blueprints directory

        Returns:
            dict: Parsed blueprint

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        logger.info(f"Loading blueprint from {filename}")

        file_path = self.blueprints_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Blueprint file not found: {filename}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                blueprint = yaml.safe_load(f)

            blueprint_id = blueprint.get('metadata', {}).get('id', 'unknown')
            logger.info(f"Successfully loaded blueprint: {blueprint_id}")

            return blueprint

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {filename}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading blueprint {filename}: {e}")
            raise

    def load_from_string(self, yaml_content: str) -> Dict[str, Any]:
        """
        Load blueprint from YAML string.

        Args:
            yaml_content: YAML as string

        Returns:
            dict: Parsed blueprint

        Raises:
            yaml.YAMLError: If YAML is invalid
        """
        # TODO: Implement (Max's Task 3.2)
        try:
            blueprint = yaml.safe_load(yaml_content)
            logger.info(f"Loaded blueprint: {blueprint.get('metadata', {}).get('id', 'unknown')}")
            return blueprint
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise

    def save_to_file(self, blueprint: Dict[str, Any], filename: str) -> Path:
        """
        Save blueprint to YAML file.

        Args:
            blueprint: Blueprint dictionary
            filename: Target filename

        Returns:
            Path: Path to saved file
        """
        logger.info(f"Saving blueprint to {filename}")

        file_path = self.blueprints_dir / filename

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    blueprint,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False
                )

            blueprint_id = blueprint.get('metadata', {}).get('id', 'unknown')
            logger.info(f"Successfully saved blueprint {blueprint_id} to {filename}")

            return file_path

        except Exception as e:
            logger.error(f"Error saving blueprint to {filename}: {e}")
            raise
