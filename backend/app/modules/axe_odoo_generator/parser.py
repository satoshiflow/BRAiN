"""
AXE Odoo Module Spec Parser

Parses simplified text specifications into ModuleAST.
Sprint IV: AXE × Odoo Integration
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .schemas import (
    ModuleAST,
    OdooAccessRightAST,
    OdooFieldAST,
    OdooFieldType,
    OdooMenuItemAST,
    OdooModelAST,
    OdooViewAST,
    OdooViewType,
)


class ModuleSpecParser:
    """
    Parser for simplified Odoo module specifications.

    Converts AI-friendly text format into structured ModuleAST.

    Example Format:
    ```
    Create an Odoo module called "my_custom_crm" v1.0.0
    Summary: Custom CRM extension
    Dependencies: base, crm

    Model: custom.lead.stage
      Description: Custom Lead Stage
      - name (required text, label "Stage Name")
      - sequence (integer, default 10)
      - color (integer, label "Color Index")

    Views:
      - Tree view with name, sequence, color
      - Form view with all fields

    Access: base.group_user can read/write/create
    ```
    """

    def __init__(self):
        """Initialize parser."""
        self.current_line = 0
        self.lines: List[str] = []

    def parse(self, spec_text: str) -> ModuleAST:
        """
        Parse module specification text into ModuleAST.

        Args:
            spec_text: Simplified text specification

        Returns:
            ModuleAST object

        Raises:
            ValueError: If spec is invalid
        """
        self.lines = [line.rstrip() for line in spec_text.split("\n")]
        self.current_line = 0

        try:
            # Parse module metadata
            metadata = self._parse_module_metadata()

            # Parse models
            models = self._parse_models()

            # Parse views
            views = self._parse_views(models)

            # Parse menus (if any)
            menus = self._parse_menus()

            # Parse access rights
            access_rights = self._parse_access_rights(models)

            # Build ModuleAST
            ast = ModuleAST(
                name=metadata["name"],
                version=metadata.get("version", "1.0.0"),
                display_name=metadata.get("display_name"),
                summary=metadata.get("summary"),
                description=metadata.get("description"),
                depends=metadata.get("depends", ["base"]),
                category=metadata.get("category", "Uncategorized"),
                models=models,
                views=views,
                menus=menus,
                access_rights=access_rights,
            )

            logger.info(f"Parsed module spec: {ast.name} v{ast.version}")
            return ast

        except Exception as e:
            logger.error(f"Failed to parse module spec: {e}")
            raise ValueError(f"Invalid module specification: {e}")

    def _parse_module_metadata(self) -> Dict[str, Any]:
        """Parse module metadata from header."""
        metadata: Dict[str, Any] = {}

        # Parse "Create an Odoo module called 'name' vX.Y.Z"
        for line in self.lines[: min(20, len(self.lines))]:
            line_lower = line.lower()

            # Module name and version
            if "module called" in line_lower or "create" in line_lower:
                # Extract name (in quotes or after "called")
                name_match = re.search(r'["\']([a-z_]+)["\']\s*v?([\d.]+)?', line, re.IGNORECASE)
                if name_match:
                    metadata["name"] = name_match.group(1)
                    if name_match.group(2):
                        metadata["version"] = name_match.group(2)
                else:
                    # Try without quotes
                    name_match = re.search(r'called\s+([a-z_]+)\s*v?([\d.]+)?', line, re.IGNORECASE)
                    if name_match:
                        metadata["name"] = name_match.group(1)
                        if name_match.group(2):
                            metadata["version"] = name_match.group(2)

            # Summary
            elif line.startswith("Summary:") or line.startswith("summary:"):
                metadata["summary"] = line.split(":", 1)[1].strip()

            # Description
            elif line.startswith("Description:") or line.startswith("description:"):
                metadata["description"] = line.split(":", 1)[1].strip()

            # Dependencies
            elif line.startswith("Dependencies:") or line.startswith("dependencies:") or line.startswith("Depends:"):
                deps_str = line.split(":", 1)[1].strip()
                metadata["depends"] = [d.strip() for d in deps_str.split(",")]

            # Category
            elif line.startswith("Category:") or line.startswith("category:"):
                metadata["category"] = line.split(":", 1)[1].strip()

            # Display name
            elif line.startswith("Name:") or line.startswith("name:"):
                metadata["display_name"] = line.split(":", 1)[1].strip()

        if "name" not in metadata:
            raise ValueError("Module name not found in specification")

        return metadata

    def _parse_models(self) -> List[OdooModelAST]:
        """Parse model definitions."""
        models = []

        for i, line in enumerate(self.lines):
            line_stripped = line.strip()

            # Look for "Model: model.name"
            if line_stripped.startswith("Model:") or line_stripped.startswith("model:"):
                model_name = line_stripped.split(":", 1)[1].strip()

                # Parse model details
                model = self._parse_single_model(model_name, i + 1)
                models.append(model)

        return models

    def _parse_single_model(self, model_name: str, start_line: int) -> OdooModelAST:
        """Parse a single model definition."""
        fields = []
        description = None
        inherits = None

        # Look ahead for model details
        for i in range(start_line, len(self.lines)):
            line = self.lines[i]
            indent = len(line) - len(line.lstrip())

            # Stop at next section (no indent or different keyword)
            if indent == 0 and i > start_line:
                if any(
                    line.strip().startswith(kw)
                    for kw in ["Model:", "Views:", "Access:", "Menu:", "Dependencies:"]
                ):
                    break

            line_stripped = line.strip()

            # Description
            if line_stripped.startswith("Description:") or line_stripped.startswith("description:"):
                description = line_stripped.split(":", 1)[1].strip()

            # Inherits
            elif line_stripped.startswith("Inherits:") or line_stripped.startswith("inherits:"):
                inherits = line_stripped.split(":", 1)[1].strip()

            # Field definition (starts with -)
            elif line_stripped.startswith("-"):
                field = self._parse_field(line_stripped[1:].strip())
                fields.append(field)

        return OdooModelAST(
            name=model_name,
            description=description,
            inherits=inherits,
            fields=fields,
        )

    def _parse_field(self, field_spec: str) -> OdooFieldAST:
        """
        Parse a field specification.

        Examples:
        - name (required text, label "Stage Name")
        - sequence (integer, default 10)
        - partner_id (many2one res.partner, label "Customer")
        """
        # Extract field name (before parenthesis)
        field_name_match = re.match(r'^([a-z_][a-z0-9_]*)', field_spec)
        if not field_name_match:
            raise ValueError(f"Invalid field specification: {field_spec}")

        field_name = field_name_match.group(1)

        # Extract attributes from parentheses
        attrs_match = re.search(r'\((.*?)\)(?:\s*,\s*(.*))?$', field_spec)
        if not attrs_match:
            # No parentheses - default to char
            return OdooFieldAST(name=field_name, field_type=OdooFieldType.CHAR)

        attrs_str = attrs_match.group(1)
        extra_attrs = attrs_match.group(2) or ""

        # Combine all attributes
        full_attrs = attrs_str
        if extra_attrs:
            full_attrs += ", " + extra_attrs

        # Parse attributes
        field_type = None
        required = False
        readonly = False
        default = None
        string = None
        help_text = None
        comodel_name = None
        selection = None

        # Split by comma (but respect quoted strings)
        attr_parts = re.findall(r'(?:[^,"]|"(?:\\.|[^"])*")+', full_attrs)

        for attr in attr_parts:
            attr = attr.strip()
            attr_lower = attr.lower()

            # Field type detection
            if attr_lower in ["text", "char", "string"]:
                field_type = OdooFieldType.CHAR if attr_lower == "char" else OdooFieldType.TEXT
            elif attr_lower == "integer":
                field_type = OdooFieldType.INTEGER
            elif attr_lower == "float":
                field_type = OdooFieldType.FLOAT
            elif attr_lower in ["boolean", "bool"]:
                field_type = OdooFieldType.BOOLEAN
            elif attr_lower == "date":
                field_type = OdooFieldType.DATE
            elif attr_lower == "datetime":
                field_type = OdooFieldType.DATETIME
            elif attr_lower == "html":
                field_type = OdooFieldType.HTML
            elif attr_lower == "binary":
                field_type = OdooFieldType.BINARY

            # Relational fields
            elif attr_lower.startswith("many2one"):
                field_type = OdooFieldType.MANY2ONE
                # Extract comodel: "many2one res.partner"
                parts = attr.split()
                if len(parts) > 1:
                    comodel_name = parts[1]
            elif attr_lower.startswith("one2many"):
                field_type = OdooFieldType.ONE2MANY
                parts = attr.split()
                if len(parts) > 1:
                    comodel_name = parts[1]
            elif attr_lower.startswith("many2many"):
                field_type = OdooFieldType.MANY2MANY
                parts = attr.split()
                if len(parts) > 1:
                    comodel_name = parts[1]

            # Flags
            elif attr_lower == "required":
                required = True
            elif attr_lower == "readonly":
                readonly = True

            # Default value
            elif attr_lower.startswith("default"):
                default_match = re.search(r'default\s+(.+)', attr, re.IGNORECASE)
                if default_match:
                    default_val = default_match.group(1).strip()
                    # Try to parse as number
                    try:
                        default = int(default_val)
                    except ValueError:
                        try:
                            default = float(default_val)
                        except ValueError:
                            # Remove quotes if present
                            default = default_val.strip('"\'')

            # Label/String
            elif attr_lower.startswith("label"):
                label_match = re.search(r'label\s+"([^"]+)"', attr, re.IGNORECASE)
                if label_match:
                    string = label_match.group(1)

            # Help text
            elif attr_lower.startswith("help"):
                help_match = re.search(r'help\s+"([^"]+)"', attr, re.IGNORECASE)
                if help_match:
                    help_text = help_match.group(1)

        # Default to CHAR if no type specified
        if field_type is None:
            field_type = OdooFieldType.CHAR

        return OdooFieldAST(
            name=field_name,
            field_type=field_type,
            required=required,
            readonly=readonly,
            default=default,
            string=string,
            help=help_text,
            comodel_name=comodel_name,
            selection=selection,
        )

    def _parse_views(self, models: List[OdooModelAST]) -> List[OdooViewAST]:
        """Parse view definitions."""
        views = []

        for i, line in enumerate(self.lines):
            line_stripped = line.strip()

            # Look for "Views:" section
            if line_stripped.startswith("Views:") or line_stripped.startswith("views:"):
                # Parse view items
                for j in range(i + 1, len(self.lines)):
                    view_line = self.lines[j].strip()

                    # Stop at next section
                    if any(
                        view_line.startswith(kw)
                        for kw in ["Model:", "Access:", "Menu:", "Dependencies:"]
                    ):
                        break

                    # View item (starts with -)
                    if view_line.startswith("-"):
                        view_spec = view_line[1:].strip()
                        parsed_views = self._parse_view_spec(view_spec, models)
                        views.extend(parsed_views)

        return views

    def _parse_view_spec(
        self, view_spec: str, models: List[OdooModelAST]
    ) -> List[OdooViewAST]:
        """
        Parse a view specification.

        Examples:
        - Tree view with name, sequence, color
        - Form view with all fields
        - Kanban view
        """
        views = []
        view_spec_lower = view_spec.lower()

        # Determine view type
        if "tree" in view_spec_lower:
            view_type = OdooViewType.TREE
        elif "form" in view_spec_lower:
            view_type = OdooViewType.FORM
        elif "kanban" in view_spec_lower:
            view_type = OdooViewType.KANBAN
        elif "search" in view_spec_lower:
            view_type = OdooViewType.SEARCH
        elif "calendar" in view_spec_lower:
            view_type = OdooViewType.CALENDAR
        elif "graph" in view_spec_lower:
            view_type = OdooViewType.GRAPH
        else:
            # Default to form
            view_type = OdooViewType.FORM

        # Parse field list (if any)
        fields_to_include = []

        # "with field1, field2, field3"
        if " with " in view_spec_lower:
            fields_part = view_spec.split(" with ", 1)[1]
            if "all fields" in fields_part.lower():
                fields_to_include = []  # Empty means all fields
            else:
                # Parse comma-separated fields
                fields_to_include = [f.strip() for f in fields_part.split(",")]

        # Generate view for each model
        for model in models:
            view_name = f"{model.name.replace('.', '_')}_{view_type.value}"

            views.append(
                OdooViewAST(
                    name=view_name,
                    model=model.name,
                    view_type=view_type,
                    fields=fields_to_include,
                )
            )

        return views

    def _parse_menus(self) -> List[OdooMenuItemAST]:
        """Parse menu definitions."""
        menus = []

        # For now, skip menu parsing - will add if needed
        # Menu syntax TBD

        return menus

    def _parse_access_rights(
        self, models: List[OdooModelAST]
    ) -> List[OdooAccessRightAST]:
        """Parse access rights."""
        access_rights = []

        for i, line in enumerate(self.lines):
            line_stripped = line.strip()

            # Look for "Access:" section
            if line_stripped.startswith("Access:") or line_stripped.startswith("access:"):
                # Parse access spec
                # Example: "Access: base.group_user can read/write/create"
                access_spec = line_stripped.split(":", 1)[1].strip()
                rights = self._parse_access_spec(access_spec, models)
                access_rights.extend(rights)

        # If no access rights specified, add default (read-only for base.group_user)
        if not access_rights:
            for model in models:
                access_rights.append(
                    OdooAccessRightAST(
                        model=model.name,
                        group="base.group_user",
                        perm_read=True,
                        perm_write=False,
                        perm_create=False,
                        perm_unlink=False,
                    )
                )

        return access_rights

    def _parse_access_spec(
        self, access_spec: str, models: List[OdooModelAST]
    ) -> List[OdooAccessRightAST]:
        """
        Parse access specification.

        Example: "base.group_user can read/write/create"
        """
        rights = []

        # Extract group
        group_match = re.match(r'^([a-z._]+)\s+can\s+(.+)', access_spec, re.IGNORECASE)
        if not group_match:
            # Default to base.group_user with read
            group = "base.group_user"
            perms = "read"
        else:
            group = group_match.group(1)
            perms = group_match.group(2).lower()

        # Parse permissions
        perm_read = "read" in perms
        perm_write = "write" in perms
        perm_create = "create" in perms
        perm_unlink = "delete" in perms or "unlink" in perms

        # Create access right for each model
        for model in models:
            rights.append(
                OdooAccessRightAST(
                    model=model.name,
                    group=group,
                    perm_read=perm_read,
                    perm_write=perm_write,
                    perm_create=perm_create,
                    perm_unlink=perm_unlink,
                )
            )

        return rights
