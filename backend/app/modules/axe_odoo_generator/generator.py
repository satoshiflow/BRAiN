"""
AXE Odoo Module Generator

Generates Odoo module files from ModuleAST.
Sprint IV: AXE × Odoo Integration
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

from .schemas import GeneratedFile, ModuleAST, OdooModuleGenerationResult


class OdooModuleGenerator:
    """
    Generates Odoo module files from ModuleAST.

    Uses Jinja2 templates to generate:
    - __manifest__.py
    - models/*.py
    - views/*.xml
    - security/ir.model.access.csv
    - __init__.py files
    """

    def __init__(self):
        """Initialize generator with Jinja2 environment."""
        templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(enabled_extensions=[], default=False),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, module_ast: ModuleAST) -> OdooModuleGenerationResult:
        """
        Generate Odoo module from AST.

        Args:
            module_ast: ModuleAST to generate from

        Returns:
            OdooModuleGenerationResult with generated files
        """
        try:
            files: List[GeneratedFile] = []
            warnings: List[str] = []

            # Validate AST
            validation_warnings = self._validate_ast(module_ast)
            warnings.extend(validation_warnings)

            # Generate __manifest__.py
            manifest_file = self._generate_manifest(module_ast)
            files.append(manifest_file)

            # Generate __init__.py (root)
            root_init_file = self._generate_root_init(module_ast)
            files.append(root_init_file)

            # Generate models
            if module_ast.models:
                model_files = self._generate_models(module_ast)
                files.extend(model_files)

                # Generate models/__init__.py
                models_init_file = self._generate_models_init(module_ast)
                files.append(models_init_file)

            # Generate views
            if module_ast.views:
                view_files = self._generate_views(module_ast)
                files.extend(view_files)

            # Generate security
            if module_ast.access_rights:
                security_file = self._generate_security(module_ast)
                files.append(security_file)

            # Generate README.md
            readme_file = self._generate_readme(module_ast)
            files.append(readme_file)

            # Compute module hash
            module_hash = self._compute_module_hash(files)

            logger.info(
                f"Generated Odoo module '{module_ast.name}' with {len(files)} files"
            )

            return OdooModuleGenerationResult(
                success=True,
                module_name=module_ast.name,
                version=module_ast.version,
                files=files,
                module_hash=module_hash,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Failed to generate Odoo module: {e}")
            return OdooModuleGenerationResult(
                success=False,
                module_name=module_ast.name,
                version=module_ast.version,
                files=[],
                errors=[str(e)],
            )

    def _validate_ast(self, module_ast: ModuleAST) -> List[str]:
        """
        Validate ModuleAST for common issues.

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for models
        if not module_ast.models:
            warnings.append("Module has no models defined")

        # Check for views
        if not module_ast.views and module_ast.models:
            warnings.append("Module has models but no views defined")

        # Check model names
        for model in module_ast.models:
            if "." not in model.name:
                warnings.append(
                    f"Model '{model.name}' should use dot notation (e.g., 'custom.model')"
                )

            # Check for required fields
            if not model.fields:
                warnings.append(f"Model '{model.name}' has no fields defined")

        # Check dependencies
        if "base" not in module_ast.depends:
            warnings.append("Module should depend on 'base'")

        return warnings

    def _generate_manifest(self, module_ast: ModuleAST) -> GeneratedFile:
        """Generate __manifest__.py file."""
        template = self.env.get_template("manifest.py.jinja2")
        content = template.render(module=module_ast)

        return GeneratedFile(
            path="__manifest__.py",
            content=content,
            file_type="python",
        )

    def _generate_root_init(self, module_ast: ModuleAST) -> GeneratedFile:
        """Generate root __init__.py file."""
        content = "# -*- coding: utf-8 -*-\n"
        if module_ast.models:
            content += "from . import models\n"

        return GeneratedFile(
            path="__init__.py",
            content=content,
            file_type="python",
        )

    def _generate_models(self, module_ast: ModuleAST) -> List[GeneratedFile]:
        """Generate model files."""
        files = []
        template = self.env.get_template("model.py.jinja2")

        for model in module_ast.models:
            # Generate model file
            content = template.render(model=model)

            # Filename from model name
            filename = f"{model.name.replace('.', '_')}.py"

            files.append(
                GeneratedFile(
                    path=f"models/{filename}",
                    content=content,
                    file_type="python",
                )
            )

        return files

    def _generate_models_init(self, module_ast: ModuleAST) -> GeneratedFile:
        """Generate models/__init__.py file."""
        content = "# -*- coding: utf-8 -*-\n"

        for model in module_ast.models:
            filename = model.name.replace(".", "_")
            content += f"from . import {filename}\n"

        return GeneratedFile(
            path="models/__init__.py",
            content=content,
            file_type="python",
        )

    def _generate_views(self, module_ast: ModuleAST) -> List[GeneratedFile]:
        """Generate view XML files."""
        files = []
        template = self.env.get_template("views.xml.jinja2")

        # Group views by model
        views_by_model = {}
        for view in module_ast.views:
            if view.model not in views_by_model:
                views_by_model[view.model] = []
            views_by_model[view.model].append(view)

        # Generate one XML file per model
        for model_name, views in views_by_model.items():
            # Find model AST
            model_ast = next(
                (m for m in module_ast.models if m.name == model_name), None
            )

            if not model_ast:
                logger.warning(
                    f"Views defined for model '{model_name}' but model not found in AST"
                )
                continue

            # Generate views XML
            content = template.render(model=model_ast, views=views)

            # Filename from model name
            filename = f"{model_name.replace('.', '_')}_views.xml"

            files.append(
                GeneratedFile(
                    path=f"views/{filename}",
                    content=content,
                    file_type="xml",
                )
            )

        return files

    def _generate_security(self, module_ast: ModuleAST) -> GeneratedFile:
        """Generate security/ir.model.access.csv file."""
        template = self.env.get_template("ir.model.access.csv.jinja2")
        content = template.render(access_rights=module_ast.access_rights)

        return GeneratedFile(
            path="security/ir.model.access.csv",
            content=content,
            file_type="csv",
        )

    def _generate_readme(self, module_ast: ModuleAST) -> GeneratedFile:
        """Generate README.md file."""
        content = f"""# {module_ast.display_name or module_ast.name}

**Version:** {module_ast.version}

{module_ast.summary or ""}

## Description

{module_ast.description or module_ast.summary or "No description provided."}

## Models

{chr(10).join(f"- `{model.name}`: {model.description or 'No description'}" for model in module_ast.models)}

## Dependencies

{chr(10).join(f"- {dep}" for dep in module_ast.depends)}

## Installation

1. Copy this module to your Odoo addons directory
2. Update the module list in Odoo
3. Install the module from Apps menu

## Author

{module_ast.author}

## License

{module_ast.license}

---

*Generated by BRAiN AXE Odoo Generator*
"""

        return GeneratedFile(
            path="README.md",
            content=content,
            file_type="markdown",
        )

    def _compute_module_hash(self, files: List[GeneratedFile]) -> str:
        """
        Compute SHA256 hash of all generated files.

        Args:
            files: List of generated files

        Returns:
            SHA256 hash as hex string
        """
        hasher = hashlib.sha256()

        # Sort files by path for deterministic hash
        sorted_files = sorted(files, key=lambda f: f.path)

        for file in sorted_files:
            # Include path and content
            hasher.update(file.path.encode("utf-8"))
            hasher.update(file.content.encode("utf-8"))

        return hasher.hexdigest()
