"""
Odoo Module Factory Node (Sprint 8.5)

Automated Odoo module generation with AXE guidance.
Generates models, views, access rules, and manifest files.
"""

from typing import Dict, Any, List
import os
import shutil
from pathlib import Path
from datetime import datetime
from loguru import logger

from backend.app.modules.autonomous_pipeline.execution_node import (
    ExecutionNode,
    ExecutionContext,
    ExecutionNodeError,
    RollbackError,
)
from backend.app.modules.autonomous_pipeline.schemas import ExecutionNodeSpec


class OdooModuleNode(ExecutionNode):
    """
    Odoo module generation execution node.

    Features:
    - Automated module structure generation
    - Model, view, and access rule generation
    - AXE-guided logic assistance (optional)
    - Path traversal prevention
    - Rollback support (uninstall + delete)
    - Dry-run simulation
    """

    # Odoo modules directory
    MODULES_DIR = Path("storage/odoo_modules")

    def __init__(self, spec: ExecutionNodeSpec):
        """
        Initialize Odoo module node.

        Args:
            spec: Node specification with executor_params:
                - module_name: str (technical name, e.g., "my_business_crm")
                - module_title: str (human-readable name)
                - module_description: str (description)
                - version: str (module version, default: "1.0.0")
                - models: List[Dict] (model definitions)
                - views: List[Dict] (view definitions)
                - access_rules: List[Dict] (security rules)
                - depends: List[str] (dependencies, e.g., ["base", "sale"])
                - business_intent_id: str (link to business intent)
        """
        super().__init__(spec)

        # Extract parameters
        params = spec.executor_params
        self.module_name = params.get("module_name")
        self.module_title = params.get("module_title", self.module_name)
        self.module_description = params.get("module_description", "Auto-generated module")
        self.version = params.get("version", "1.0.0")
        self.models = params.get("models", [])
        self.views = params.get("views", [])
        self.access_rules = params.get("access_rules", [])
        self.depends = params.get("depends", ["base"])
        self.business_intent_id = params.get("business_intent_id", "unknown")

        # Validate required params
        if not self.module_name:
            raise ExecutionNodeError("Missing required parameter: module_name")

        # Validate module name (no path traversal!)
        if not self._is_safe_module_name(self.module_name):
            raise ExecutionNodeError(
                f"Invalid module_name: {self.module_name}. "
                f"Must be alphanumeric with underscores only (no path traversal)."
            )

        # State
        self.module_path: Path | None = None
        self.installed: bool = False

    async def execute(self, context: ExecutionContext) -> tuple[Dict[str, Any], List[str]]:
        """
        Generate and install Odoo module (LIVE mode).

        Args:
            context: Execution context

        Returns:
            Tuple of (output_data, artifact_paths)

        Raises:
            ExecutionNodeError: If generation or installation fails
        """
        logger.info(f"[{self.node_id}] Generating Odoo module: {self.module_name}")

        try:
            # 1. Generate module structure
            module_path = await self._generate_module_structure(context)
            self.module_path = module_path

            # 2. Generate manifest
            await self._generate_manifest(module_path)

            # 3. Generate models
            await self._generate_models(module_path)

            # 4. Generate views
            await self._generate_views(module_path)

            # 5. Generate access rules
            await self._generate_access_rules(module_path)

            # 6. Validate module structure
            validation_result = await self._validate_module(module_path)
            if not validation_result["valid"]:
                raise ExecutionNodeError(
                    f"Module validation failed: {validation_result['errors']}"
                )

            # 7. Install module (via Odoo connector - governance check)
            install_status = await self._install_module(context)
            self.installed = install_status["success"]

            # Output data
            output = {
                "module_path": str(module_path),
                "module_name": self.module_name,
                "module_title": self.module_title,
                "version": self.version,
                "odoo_install_status": install_status,
                "models_count": len(self.models),
                "views_count": len(self.views),
                "validation": validation_result,
            }

            # Artifacts
            artifacts = [str(module_path)]

            logger.info(
                f"[{self.node_id}] Odoo module generated successfully: {module_path}"
            )

            return output, artifacts

        except Exception as e:
            logger.error(f"[{self.node_id}] Odoo module generation failed: {e}")
            raise ExecutionNodeError(f"Odoo module generation failed: {e}")

    async def dry_run(self, context: ExecutionContext) -> tuple[Dict[str, Any], List[str]]:
        """
        Simulate Odoo module generation (DRY-RUN mode).

        Args:
            context: Execution context

        Returns:
            Tuple of (simulated_output, simulated_artifacts)
        """
        logger.info(
            f"[{self.node_id}] DRY-RUN: Simulating Odoo module generation "
            f"({self.module_name})"
        )

        # Simulated output
        output = {
            "module_path": f"storage/odoo_modules/{self.module_name} (simulated)",
            "module_name": self.module_name,
            "module_title": self.module_title,
            "version": self.version,
            "odoo_install_status": {
                "success": True,
                "simulated": True,
                "message": "Module installation simulated",
            },
            "models_count": len(self.models),
            "views_count": len(self.views),
            "validation": {
                "valid": True,
                "structure_complete": True,
                "simulated": True,
            },
            "generated_files": [
                "__manifest__.py",
                "__init__.py",
                "models/__init__.py",
                *[f"models/{model['name']}.py" for model in self.models],
                "views/__init__.py",
                *[f"views/{view['name']}.xml" for view in self.views],
                "security/ir.model.access.csv",
            ],
        }

        # Simulated artifacts
        artifacts = [f"sim_odoo_module_{self.module_name}"]

        logger.info(
            f"[{self.node_id}] DRY-RUN complete: Odoo module structure simulated "
            f"({len(self.models)} models, {len(self.views)} views)"
        )

        return output, artifacts

    async def rollback(self, context: ExecutionContext):
        """
        Rollback Odoo module installation and generation.

        Args:
            context: Execution context

        Raises:
            RollbackError: If rollback fails
        """
        logger.warning(f"[{self.node_id}] Rolling back Odoo module: {self.module_name}")

        # 1. Uninstall module (if installed)
        if self.installed:
            try:
                await self._uninstall_module(context)
                logger.info(f"[{self.node_id}] Odoo module uninstalled: {self.module_name}")
            except Exception as e:
                logger.error(f"[{self.node_id}] Failed to uninstall module: {e}")

        # 2. Delete module files
        if self.module_path and self.module_path.exists():
            try:
                shutil.rmtree(self.module_path)
                logger.info(f"[{self.node_id}] Deleted module files: {self.module_path}")
            except Exception as e:
                logger.error(f"[{self.node_id}] Failed to delete module files: {e}")
                raise RollbackError(f"Failed to delete module files: {e}")

        logger.info(f"[{self.node_id}] Rollback completed")

    def _is_safe_module_name(self, name: str) -> bool:
        """
        Validate module name (prevent path traversal).

        Args:
            name: Module name to validate

        Returns:
            True if safe, False otherwise
        """
        # Allow only alphanumeric and underscores
        # No dots, slashes, or special characters
        return name.replace("_", "").isalnum() and ".." not in name and "/" not in name

    async def _generate_module_structure(self, context: ExecutionContext) -> Path:
        """
        Create module directory structure.

        Args:
            context: Execution context

        Returns:
            Path to module directory
        """
        module_path = self.MODULES_DIR / self.module_name
        module_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (module_path / "models").mkdir(exist_ok=True)
        (module_path / "views").mkdir(exist_ok=True)
        (module_path / "security").mkdir(exist_ok=True)

        # Create __init__.py files
        (module_path / "__init__.py").write_text(
            "# -*- coding: utf-8 -*-\n"
            "from . import models\n"
        )
        (module_path / "models" / "__init__.py").write_text(
            "# -*- coding: utf-8 -*-\n"
            "# Import models here\n"
        )

        return module_path

    async def _generate_manifest(self, module_path: Path):
        """Generate __manifest__.py file."""
        manifest = f"""# -*- coding: utf-8 -*-
{{
    'name': '{self.module_title}',
    'summary': '{self.module_description}',
    'description': \"\"\"
{self.module_description}

Generated by BRAiN Autonomous Pipeline.
Business Intent ID: {self.business_intent_id}
    \"\"\",
    'author': 'BRAiN Autonomous Pipeline',
    'website': 'https://brain.ai',
    'category': 'Customization',
    'version': '{self.version}',
    'depends': {self.depends},
    'data': [
        'security/ir.model.access.csv',
        # Views will be listed here
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}}
"""
        (module_path / "__manifest__.py").write_text(manifest)

    async def _generate_models(self, module_path: Path):
        """Generate model files."""
        if not self.models:
            return

        models_init = "# -*- coding: utf-8 -*-\n"

        for model in self.models:
            model_name = model.get("name", "unknown_model")
            model_class = self._to_class_name(model_name)
            model_table = model.get("table", f"x_{model_name}")
            fields = model.get("fields", [])

            # Generate model file
            model_code = f"""# -*- coding: utf-8 -*-
from odoo import models, fields, api


class {model_class}(models.Model):
    _name = '{model_table}'
    _description = '{model.get("description", model_name)}'

    name = fields.Char(string='Name', required=True)
"""

            # Add fields
            for field in fields:
                field_name = field.get("name")
                field_type = field.get("type", "Char")
                field_label = field.get("label", field_name.replace("_", " ").title())
                field_required = field.get("required", False)

                model_code += f"    {field_name} = fields.{field_type}(string='{field_label}', required={field_required})\n"

            # Write model file
            (module_path / "models" / f"{model_name}.py").write_text(model_code)

            # Add to __init__.py
            models_init += f"from . import {model_name}\n"

        # Write models/__init__.py
        (module_path / "models" / "__init__.py").write_text(models_init)

    async def _generate_views(self, module_path: Path):
        """Generate view XML files."""
        if not self.views:
            return

        for view in self.views:
            view_name = view.get("name", "unknown_view")
            model_table = view.get("model", "x.unknown")
            view_type = view.get("type", "form")

            # Generate basic view XML
            view_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="{view_name}" model="ir.ui.view">
        <field name="name">{view_name}</field>
        <field name="model">{model_table}</field>
        <field name="arch" type="xml">
            <{view_type}>
                <field name="name"/>
            </{view_type}>
        </field>
    </record>
</odoo>
"""
            (module_path / "views" / f"{view_name}.xml").write_text(view_xml)

    async def _generate_access_rules(self, module_path: Path):
        """Generate security/ir.model.access.csv file."""
        csv_header = "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n"
        csv_rows = ""

        for model in self.models:
            model_name = model.get("name", "unknown_model")
            model_table = model.get("table", f"x_{model_name}")
            access_id = f"access_{model_table.replace('.', '_')}"

            # Grant all permissions to base.group_user
            csv_rows += f"{access_id},{model_table},model_{model_table.replace('.', '_')},base.group_user,1,1,1,1\n"

        (module_path / "security" / "ir.model.access.csv").write_text(csv_header + csv_rows)

    async def _validate_module(self, module_path: Path) -> Dict[str, Any]:
        """
        Validate generated module structure.

        Args:
            module_path: Path to module

        Returns:
            Validation result dict
        """
        errors = []
        warnings = []

        # Check required files
        required_files = ["__manifest__.py", "__init__.py", "security/ir.model.access.csv"]
        for file_path in required_files:
            if not (module_path / file_path).exists():
                errors.append(f"Missing required file: {file_path}")

        # Check models directory
        if self.models and not (module_path / "models" / "__init__.py").exists():
            errors.append("Missing models/__init__.py")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "structure_complete": True,
        }

    async def _install_module(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Install Odoo module (via connector - governance check).

        Args:
            context: Execution context

        Returns:
            Installation status dict
        """
        # Placeholder: In real implementation, this would:
        # 1. Call Odoo connector to install module
        # 2. Wait for installation to complete
        # 3. Verify module is installed

        logger.info(
            f"[{self.node_id}] Installing Odoo module: {self.module_name} "
            f"(placeholder - connector not implemented)"
        )

        # Emit audit event
        context.emit_audit_event({
            "event_type": "odoo_module_installed",
            "module_name": self.module_name,
            "version": self.version,
        })

        return {
            "success": True,
            "message": f"Module {self.module_name} installation simulated",
            "installed_at": datetime.utcnow().isoformat(),
        }

    async def _uninstall_module(self, context: ExecutionContext):
        """
        Uninstall Odoo module.

        Args:
            context: Execution context
        """
        logger.warning(f"[{self.node_id}] Uninstalling Odoo module: {self.module_name}")

        # Placeholder: Would call Odoo connector to uninstall

        # Emit audit event
        context.emit_audit_event({
            "event_type": "odoo_module_uninstalled",
            "module_name": self.module_name,
        })

    @staticmethod
    def _to_class_name(snake_case: str) -> str:
        """Convert snake_case to PascalCase for class names."""
        return "".join(word.capitalize() for word in snake_case.split("_"))
