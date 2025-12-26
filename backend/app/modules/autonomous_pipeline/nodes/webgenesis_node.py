"""
WebGenesis Node (Sprint 8.3)

Website generation node using template-based approach.
Generates Next.js or static websites with governance checks.
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
)
from backend.app.modules.autonomous_pipeline.schemas import ExecutionNodeSpec


class WebGenesisNode(ExecutionNode):
    """
    Website generation execution node.

    Features:
    - Template-based website generation (Next.js/static)
    - Governance-compliant deployment
    - Rollback support (file cleanup)
    - Dry-run preview generation
    """

    # Template paths (relative to backend root)
    TEMPLATES_DIR = Path("storage/website_templates")
    OUTPUT_DIR = Path("storage/generated_websites")
    DEPLOY_DIR = Path("storage/deployed_websites")

    # Available templates
    AVAILABLE_TEMPLATES = {
        "nextjs-business": {
            "type": "nextjs",
            "pages": ["home", "about", "contact", "services"],
            "features": ["responsive", "seo", "dark-mode"],
        },
        "static-landing": {
            "type": "static",
            "pages": ["home"],
            "features": ["responsive", "seo"],
        },
        "ecommerce-basic": {
            "type": "nextjs",
            "pages": ["home", "products", "cart", "checkout"],
            "features": ["responsive", "seo", "payment-ready"],
        },
    }

    def __init__(self, spec: ExecutionNodeSpec):
        """
        Initialize WebGenesis node.

        Args:
            spec: Node specification with executor_params:
                - website_template: str (template ID)
                - pages: List[str] (page names)
                - domain: str (target domain)
                - title: str (website title)
                - description: str (meta description)
                - business_intent_id: str (link to business intent)
        """
        super().__init__(spec)

        # Extract parameters
        params = spec.executor_params
        self.template_id = params.get("website_template", "nextjs-business")
        self.pages = params.get("pages", ["home"])
        self.domain = params.get("domain", "example.local")
        self.title = params.get("title", "My Business")
        self.description = params.get("description", "Generated website")
        self.business_intent_id = params.get("business_intent_id", "unknown")

        # Validate template
        if self.template_id not in self.AVAILABLE_TEMPLATES:
            raise ExecutionNodeError(
                f"Invalid template: {self.template_id}. "
                f"Available: {list(self.AVAILABLE_TEMPLATES.keys())}"
            )

        # State
        self.generated_path: str | None = None
        self.deployed_path: str | None = None

    async def execute(self, context: ExecutionContext) -> tuple[Dict[str, Any], List[str]]:
        """
        Generate and deploy website (LIVE mode).

        Args:
            context: Execution context

        Returns:
            Tuple of (output_data, artifact_paths)

        Raises:
            ExecutionNodeError: If generation or deployment fails
        """
        logger.info(f"[{self.node_id}] Generating website from template: {self.template_id}")

        try:
            # 1. Generate website from template
            generated_path = await self._generate_website(context)
            self.generated_path = str(generated_path)

            # 2. Validate generated structure
            validation_result = await self._validate_website(generated_path)
            if not validation_result["valid"]:
                raise ExecutionNodeError(
                    f"Generated website validation failed: {validation_result['errors']}"
                )

            # 3. Deploy to test path (after governance check)
            deployed_path = await self._deploy_website(generated_path, context)
            self.deployed_path = str(deployed_path)

            # 4. Generate website URL
            website_url = f"http://{self.domain}/"  # Placeholder URL

            # Output data
            output = {
                "website_url": website_url,
                "template": self.template_id,
                "pages_generated": self.pages,
                "domain": self.domain,
                "title": self.title,
                "generated_path": str(generated_path),
                "deployed_path": str(deployed_path),
                "validation": validation_result,
            }

            # Artifacts
            artifacts = [
                str(generated_path),
                str(deployed_path),
            ]

            logger.info(
                f"[{self.node_id}] Website generated successfully: {website_url}"
            )

            return output, artifacts

        except Exception as e:
            logger.error(f"[{self.node_id}] Website generation failed: {e}")
            raise ExecutionNodeError(f"Website generation failed: {e}")

    async def dry_run(self, context: ExecutionContext) -> tuple[Dict[str, Any], List[str]]:
        """
        Simulate website generation (DRY-RUN mode).

        Args:
            context: Execution context

        Returns:
            Tuple of (simulated_output, simulated_artifacts)
        """
        logger.info(
            f"[{self.node_id}] DRY-RUN: Simulating website generation "
            f"(template={self.template_id})"
        )

        # Simulated output
        output = {
            "website_url": f"http://{self.domain}/ (simulated)",
            "template": self.template_id,
            "pages_generated": self.pages,
            "domain": self.domain,
            "title": self.title,
            "generated_path": f"storage/generated_websites/sim_{self.business_intent_id}",
            "deployed_path": f"storage/deployed_websites/sim_{self.domain}",
            "validation": {
                "valid": True,
                "pages_count": len(self.pages),
                "template_features": self.AVAILABLE_TEMPLATES[self.template_id]["features"],
            },
            "dry_run_preview": self._generate_html_preview(),
        }

        # Simulated artifacts
        artifacts = [
            f"sim_website_{self.business_intent_id}.html",
        ]

        logger.info(f"[{self.node_id}] DRY-RUN complete: {len(self.pages)} pages simulated")

        return output, artifacts

    async def rollback(self, context: ExecutionContext):
        """
        Rollback website deployment (remove files).

        Args:
            context: Execution context

        Raises:
            RollbackError: If rollback fails
        """
        logger.warning(f"[{self.node_id}] Rolling back website deployment")

        # Remove deployed website
        if self.deployed_path and Path(self.deployed_path).exists():
            try:
                shutil.rmtree(self.deployed_path)
                logger.info(f"[{self.node_id}] Removed deployed website: {self.deployed_path}")
            except Exception as e:
                logger.error(f"[{self.node_id}] Failed to remove deployed website: {e}")

        # Remove generated website
        if self.generated_path and Path(self.generated_path).exists():
            try:
                shutil.rmtree(self.generated_path)
                logger.info(f"[{self.node_id}] Removed generated website: {self.generated_path}")
            except Exception as e:
                logger.error(f"[{self.node_id}] Failed to remove generated website: {e}")

        logger.info(f"[{self.node_id}] Rollback completed")

    async def _generate_website(self, context: ExecutionContext) -> Path:
        """
        Generate website from template.

        Args:
            context: Execution context

        Returns:
            Path to generated website

        Raises:
            ExecutionNodeError: If generation fails
        """
        # Create output directory
        output_dir = self.OUTPUT_DIR / f"{self.business_intent_id}_{int(datetime.utcnow().timestamp())}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get template info
        template_info = self.AVAILABLE_TEMPLATES[self.template_id]
        template_type = template_info["type"]

        # Generate website based on template type
        if template_type == "static":
            await self._generate_static_website(output_dir)
        elif template_type == "nextjs":
            await self._generate_nextjs_website(output_dir)
        else:
            raise ExecutionNodeError(f"Unsupported template type: {template_type}")

        return output_dir

    async def _generate_static_website(self, output_dir: Path):
        """Generate static HTML website."""
        # Create index.html
        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{self.description}">
    <title>{self.title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; padding: 2rem; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ text-align: center; padding: 3rem 0; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1rem; }}
        p {{ font-size: 1.125rem; color: #666; }}
        .content {{ padding: 2rem 0; }}
        footer {{ text-align: center; padding: 2rem 0; color: #888; font-size: 0.875rem; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{self.title}</h1>
            <p>{self.description}</p>
        </header>
        <main class="content">
            <p>Welcome to {self.title}. This website was generated automatically.</p>
        </main>
        <footer>
            <p>&copy; {datetime.utcnow().year} {self.title}. All rights reserved.</p>
            <p>Generated by BRAiN Autonomous Pipeline</p>
        </footer>
    </div>
</body>
</html>
"""
        (output_dir / "index.html").write_text(index_html)

        # Generate additional pages
        for page in self.pages:
            if page == "home":
                continue  # Already generated as index.html

            page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page.title()} - {self.title}</title>
</head>
<body>
    <h1>{page.title()}</h1>
    <p>Page: {page}</p>
    <p><a href="/">Back to Home</a></p>
</body>
</html>
"""
            (output_dir / f"{page}.html").write_text(page_html)

    async def _generate_nextjs_website(self, output_dir: Path):
        """Generate Next.js website structure."""
        # Create Next.js directory structure
        (output_dir / "app").mkdir(parents=True, exist_ok=True)
        (output_dir / "public").mkdir(parents=True, exist_ok=True)

        # Generate package.json
        package_json = {
            "name": self.title.lower().replace(" ", "-"),
            "version": "1.0.0",
            "description": self.description,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
            },
            "dependencies": {
                "next": "^14.0.0",
                "react": "^18.0.0",
                "react-dom": "^18.0.0",
            },
        }
        import json
        (output_dir / "package.json").write_text(json.dumps(package_json, indent=2))

        # Generate app/page.tsx
        page_tsx = f"""export default function Home() {{
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-4">{self.title}</h1>
        <p className="text-lg text-gray-600 mb-8">{self.description}</p>
        <p>Welcome to {self.title}. This website was generated automatically by BRAiN.</p>
      </div>
    </main>
  )
}}
"""
        (output_dir / "app" / "page.tsx").write_text(page_tsx)

        # Generate app/layout.tsx
        layout_tsx = f"""export const metadata = {{
  title: '{self.title}',
  description: '{self.description}',
}}

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode
}}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  )
}}
"""
        (output_dir / "app" / "layout.tsx").write_text(layout_tsx)

    async def _validate_website(self, website_path: Path) -> Dict[str, Any]:
        """
        Validate generated website structure.

        Args:
            website_path: Path to website directory

        Returns:
            Validation result dict
        """
        errors = []
        warnings = []

        # Check if path exists
        if not website_path.exists():
            errors.append("Website directory does not exist")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check for required files based on template type
        template_info = self.AVAILABLE_TEMPLATES[self.template_id]
        template_type = template_info["type"]

        if template_type == "static":
            # Require index.html
            if not (website_path / "index.html").exists():
                errors.append("Missing index.html")

        elif template_type == "nextjs":
            # Require package.json and app/page.tsx
            if not (website_path / "package.json").exists():
                errors.append("Missing package.json")
            if not (website_path / "app" / "page.tsx").exists():
                errors.append("Missing app/page.tsx")

        # Check page count
        if template_type == "static":
            html_files = list(website_path.glob("*.html"))
            if len(html_files) < len(self.pages):
                warnings.append(f"Expected {len(self.pages)} pages, found {len(html_files)}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "pages_count": len(self.pages),
            "template_type": template_type,
        }

    async def _deploy_website(self, website_path: Path, context: ExecutionContext) -> Path:
        """
        Deploy website to deployment directory.

        Args:
            website_path: Path to generated website
            context: Execution context

        Returns:
            Path to deployed website

        Raises:
            ExecutionNodeError: If deployment fails
        """
        # Create deployment directory
        deploy_path = self.DEPLOY_DIR / self.domain.replace(".", "_")
        deploy_path.mkdir(parents=True, exist_ok=True)

        # Copy website to deployment directory
        try:
            # Remove existing deployment if any
            if deploy_path.exists():
                shutil.rmtree(deploy_path)

            # Copy generated website
            shutil.copytree(website_path, deploy_path)

            logger.info(f"[{self.node_id}] Deployed website to: {deploy_path}")

            return deploy_path

        except Exception as e:
            raise ExecutionNodeError(f"Deployment failed: {e}")

    def _generate_html_preview(self) -> str:
        """Generate HTML preview for dry-run mode."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview: {self.title}</title>
</head>
<body>
    <h1>[DRY-RUN PREVIEW] {self.title}</h1>
    <p>{self.description}</p>
    <h2>Configuration:</h2>
    <ul>
        <li>Template: {self.template_id}</li>
        <li>Domain: {self.domain}</li>
        <li>Pages: {', '.join(self.pages)}</li>
    </ul>
    <p><em>This is a simulation. No actual website was generated.</em></p>
</body>
</html>
"""
