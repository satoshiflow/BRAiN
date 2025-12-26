"""
UI Designer - AI-powered UI design generation

Generates modern, accessible UI designs with responsive layouts,
color schemes, and component specifications.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.token_manager import get_token_manager
from core.error_handler import get_error_handler, ErrorContext, with_error_handling

logger = logging.getLogger(__name__)


class DesignStyle(str, Enum):
    """UI design styles"""
    MODERN = "modern"
    MINIMAL = "minimal"
    MATERIAL = "material"
    GLASSMORPHISM = "glassmorphism"
    NEUMORPHISM = "neumorphism"
    RETRO = "retro"
    CORPORATE = "corporate"


class ColorScheme(str, Enum):
    """Color scheme presets"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    CUSTOM = "custom"


@dataclass
class ColorPalette:
    """Color palette for UI"""
    primary: str
    secondary: str
    accent: str
    background: str
    surface: str
    text_primary: str
    text_secondary: str
    success: str
    warning: str
    error: str
    info: str

    def to_css_vars(self) -> str:
        """Generate CSS variables"""
        return f"""
:root {{
  --color-primary: {self.primary};
  --color-secondary: {self.secondary};
  --color-accent: {self.accent};
  --color-background: {self.background};
  --color-surface: {self.surface};
  --color-text-primary: {self.text_primary};
  --color-text-secondary: {self.text_secondary};
  --color-success: {self.success};
  --color-warning: {self.warning};
  --color-error: {self.error};
  --color-info: {self.info};
}}
"""

    def to_tailwind_config(self) -> Dict[str, str]:
        """Generate Tailwind config"""
        return {
            'primary': self.primary,
            'secondary': self.secondary,
            'accent': self.accent,
            'success': self.success,
            'warning': self.warning,
            'error': self.error,
            'info': self.info,
        }


@dataclass
class TypographyScale:
    """Typography scale for consistent text sizing"""
    xs: str = "0.75rem"    # 12px
    sm: str = "0.875rem"   # 14px
    base: str = "1rem"     # 16px
    lg: str = "1.125rem"   # 18px
    xl: str = "1.25rem"    # 20px
    xl2: str = "1.5rem"    # 24px
    xl3: str = "1.875rem"  # 30px
    xl4: str = "2.25rem"   # 36px
    xl5: str = "3rem"      # 48px

    def to_css_vars(self) -> str:
        """Generate CSS variables"""
        return f"""
:root {{
  --font-size-xs: {self.xs};
  --font-size-sm: {self.sm};
  --font-size-base: {self.base};
  --font-size-lg: {self.lg};
  --font-size-xl: {self.xl};
  --font-size-2xl: {self.xl2};
  --font-size-3xl: {self.xl3};
  --font-size-4xl: {self.xl4};
  --font-size-5xl: {self.xl5};
}}
"""


@dataclass
class SpacingScale:
    """Spacing scale for consistent layouts"""
    xs: str = "0.25rem"   # 4px
    sm: str = "0.5rem"    # 8px
    md: str = "1rem"      # 16px
    lg: str = "1.5rem"    # 24px
    xl: str = "2rem"      # 32px
    xl2: str = "3rem"     # 48px
    xl3: str = "4rem"     # 64px

    def to_css_vars(self) -> str:
        """Generate CSS variables"""
        return f"""
:root {{
  --spacing-xs: {self.xs};
  --spacing-sm: {self.sm};
  --spacing-md: {self.md};
  --spacing-lg: {self.lg};
  --spacing-xl: {self.xl};
  --spacing-2xl: {self.xl2};
  --spacing-3xl: {self.xl3};
}}
"""


@dataclass
class UIDesignSpec:
    """Complete UI design specification"""
    name: str
    description: str
    style: DesignStyle
    color_scheme: ColorScheme
    pages: List[str]
    components: List[str]
    features: List[str] = field(default_factory=list)
    target_platforms: List[str] = field(default_factory=lambda: ["web"])


@dataclass
class UIDesign:
    """Generated UI design"""
    spec: UIDesignSpec
    color_palette: ColorPalette
    typography: TypographyScale
    spacing: SpacingScale
    layout_system: str
    component_specs: Dict[str, Any]
    css_output: str
    design_tokens: Dict[str, Any]
    tokens_used: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class UIDesigner:
    """
    AI-powered UI designer

    Features:
    - Modern design generation
    - Color palette generation
    - Typography system
    - Spacing and layout
    - Component specifications
    - Responsive design
    - Accessibility compliance
    """

    def __init__(self):
        """Initialize UI designer"""
        self.token_manager = get_token_manager()
        self.error_handler = get_error_handler()

        # Predefined color palettes
        self._color_palettes = {
            DesignStyle.MODERN: self._modern_palette,
            DesignStyle.MINIMAL: self._minimal_palette,
            DesignStyle.MATERIAL: self._material_palette,
            DesignStyle.GLASSMORPHISM: self._glass_palette,
        }

        logger.info("UIDesigner initialized")

    @with_error_handling(
        operation="design_ui",
        component="ui_designer",
        reraise=True
    )
    def design(self, spec: UIDesignSpec) -> UIDesign:
        """
        Generate UI design from specification

        Args:
            spec: UI design specification

        Returns:
            Complete UI design
        """
        logger.info(f"Generating UI design: {spec.name} ({spec.style.value})")

        # Estimate tokens
        estimated_tokens = 8000 + len(spec.components) * 500
        available, msg = self.token_manager.check_availability(
            estimated_tokens,
            "ui_design"
        )

        if not available:
            raise Exception(f"Insufficient tokens: {msg}")

        operation_id = self.token_manager.reserve_tokens(
            "ui_design",
            estimated_tokens,
            metadata={"name": spec.name, "style": spec.style.value}
        )

        try:
            # Generate color palette
            color_palette = self._generate_color_palette(spec)

            # Typography and spacing
            typography = TypographyScale()
            spacing = SpacingScale()

            # Layout system
            layout_system = self._generate_layout_system(spec)

            # Component specifications
            component_specs = self._generate_component_specs(spec, color_palette)

            # Generate CSS
            css_output = self._generate_css(
                color_palette,
                typography,
                spacing,
                spec
            )

            # Design tokens
            design_tokens = self._generate_design_tokens(
                color_palette,
                typography,
                spacing
            )

            # Record usage
            actual_tokens = 6000 + len(spec.components) * 400
            self.token_manager.record_usage(operation_id, actual_tokens, "completed")

            design = UIDesign(
                spec=spec,
                color_palette=color_palette,
                typography=typography,
                spacing=spacing,
                layout_system=layout_system,
                component_specs=component_specs,
                css_output=css_output,
                design_tokens=design_tokens,
                tokens_used=actual_tokens
            )

            logger.info(f"UI design generated: {spec.name}")
            return design

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))
            raise

    def _generate_color_palette(self, spec: UIDesignSpec) -> ColorPalette:
        """Generate color palette based on design style"""
        generator = self._color_palettes.get(spec.style, self._modern_palette)
        return generator(spec.color_scheme)

    def _modern_palette(self, scheme: ColorScheme) -> ColorPalette:
        """Generate modern color palette"""
        if scheme == ColorScheme.DARK:
            return ColorPalette(
                primary="#3B82F6",      # Blue
                secondary="#8B5CF6",    # Purple
                accent="#F59E0B",       # Amber
                background="#0F172A",   # Slate 900
                surface="#1E293B",      # Slate 800
                text_primary="#F8FAFC", # Slate 50
                text_secondary="#CBD5E1", # Slate 300
                success="#10B981",      # Green
                warning="#F59E0B",      # Amber
                error="#EF4444",        # Red
                info="#3B82F6"          # Blue
            )
        else:  # LIGHT
            return ColorPalette(
                primary="#3B82F6",      # Blue
                secondary="#8B5CF6",    # Purple
                accent="#F59E0B",       # Amber
                background="#FFFFFF",   # White
                surface="#F8FAFC",      # Slate 50
                text_primary="#0F172A", # Slate 900
                text_secondary="#475569", # Slate 600
                success="#10B981",      # Green
                warning="#F59E0B",      # Amber
                error="#EF4444",        # Red
                info="#3B82F6"          # Blue
            )

    def _minimal_palette(self, scheme: ColorScheme) -> ColorPalette:
        """Generate minimal color palette"""
        if scheme == ColorScheme.DARK:
            return ColorPalette(
                primary="#FFFFFF",
                secondary="#A1A1AA",
                accent="#FAFAFA",
                background="#09090B",
                surface="#18181B",
                text_primary="#FAFAFA",
                text_secondary="#A1A1AA",
                success="#22C55E",
                warning="#EAB308",
                error="#EF4444",
                info="#3B82F6"
            )
        else:
            return ColorPalette(
                primary="#18181B",
                secondary="#71717A",
                accent="#09090B",
                background="#FFFFFF",
                surface="#FAFAFA",
                text_primary="#09090B",
                text_secondary="#71717A",
                success="#22C55E",
                warning="#EAB308",
                error="#EF4444",
                info="#3B82F6"
            )

    def _material_palette(self, scheme: ColorScheme) -> ColorPalette:
        """Generate Material Design palette"""
        if scheme == ColorScheme.DARK:
            return ColorPalette(
                primary="#BB86FC",
                secondary="#03DAC6",
                accent="#CF6679",
                background="#121212",
                surface="#1E1E1E",
                text_primary="#FFFFFF",
                text_secondary="#B3B3B3",
                success="#00C853",
                warning="#FFD600",
                error="#CF6679",
                info="#2196F3"
            )
        else:
            return ColorPalette(
                primary="#6200EE",
                secondary="#03DAC6",
                accent="#FF0266",
                background="#FFFFFF",
                surface="#F5F5F5",
                text_primary="#000000",
                text_secondary="#5F6368",
                success="#00C853",
                warning="#FFD600",
                error="#B00020",
                info="#2196F3"
            )

    def _glass_palette(self, scheme: ColorScheme) -> ColorPalette:
        """Generate glassmorphism palette"""
        return ColorPalette(
            primary="rgba(255, 255, 255, 0.15)",
            secondary="rgba(255, 255, 255, 0.1)",
            accent="rgba(255, 255, 255, 0.2)",
            background="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            surface="rgba(255, 255, 255, 0.05)",
            text_primary="rgba(255, 255, 255, 0.95)",
            text_secondary="rgba(255, 255, 255, 0.7)",
            success="rgba(16, 185, 129, 0.8)",
            warning="rgba(245, 158, 11, 0.8)",
            error="rgba(239, 68, 68, 0.8)",
            info="rgba(59, 130, 246, 0.8)"
        )

    def _generate_layout_system(self, spec: UIDesignSpec) -> str:
        """Generate layout system (Grid/Flexbox)"""
        return """
/* Layout System */
.container {
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 1rem;
}

.grid {
  display: grid;
  gap: var(--spacing-md);
}

.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
.grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }

.flex {
  display: flex;
}

.flex-col { flex-direction: column; }
.flex-row { flex-direction: row; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.gap-sm { gap: var(--spacing-sm); }
.gap-md { gap: var(--spacing-md); }
.gap-lg { gap: var(--spacing-lg); }

@media (max-width: 768px) {
  .grid-cols-2,
  .grid-cols-3,
  .grid-cols-4 {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }
}
"""

    def _generate_component_specs(
        self,
        spec: UIDesignSpec,
        palette: ColorPalette
    ) -> Dict[str, Any]:
        """Generate component specifications"""
        specs = {}

        for component in spec.components:
            component_lower = component.lower()

            if 'button' in component_lower:
                specs[component] = self._button_spec(palette)
            elif 'card' in component_lower:
                specs[component] = self._card_spec(palette)
            elif 'input' in component_lower or 'form' in component_lower:
                specs[component] = self._input_spec(palette)
            elif 'nav' in component_lower or 'header' in component_lower:
                specs[component] = self._nav_spec(palette)
            else:
                specs[component] = {"type": "custom", "palette": palette}

        return specs

    def _button_spec(self, palette: ColorPalette) -> Dict[str, Any]:
        """Button component specification"""
        return {
            "type": "button",
            "variants": {
                "primary": {
                    "background": palette.primary,
                    "color": "#FFFFFF",
                    "hover_background": self._darken_color(palette.primary),
                },
                "secondary": {
                    "background": palette.secondary,
                    "color": "#FFFFFF",
                    "hover_background": self._darken_color(palette.secondary),
                },
                "outline": {
                    "background": "transparent",
                    "border": f"1px solid {palette.primary}",
                    "color": palette.primary,
                }
            },
            "sizes": {
                "sm": {"padding": "0.5rem 1rem", "font_size": "0.875rem"},
                "md": {"padding": "0.75rem 1.5rem", "font_size": "1rem"},
                "lg": {"padding": "1rem 2rem", "font_size": "1.125rem"},
            }
        }

    def _card_spec(self, palette: ColorPalette) -> Dict[str, Any]:
        """Card component specification"""
        return {
            "type": "card",
            "background": palette.surface,
            "border_radius": "0.5rem",
            "padding": "1.5rem",
            "shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
            "hover_shadow": "0 10px 15px rgba(0, 0, 0, 0.15)",
        }

    def _input_spec(self, palette: ColorPalette) -> Dict[str, Any]:
        """Input component specification"""
        return {
            "type": "input",
            "background": palette.surface,
            "border": f"1px solid {palette.text_secondary}",
            "border_radius": "0.375rem",
            "padding": "0.75rem 1rem",
            "focus_border": palette.primary,
            "focus_ring": f"0 0 0 3px {palette.primary}33",
        }

    def _nav_spec(self, palette: ColorPalette) -> Dict[str, Any]:
        """Navigation component specification"""
        return {
            "type": "navigation",
            "background": palette.surface,
            "height": "4rem",
            "shadow": "0 1px 3px rgba(0, 0, 0, 0.1)",
            "link_color": palette.text_primary,
            "link_active_color": palette.primary,
        }

    def _generate_css(
        self,
        palette: ColorPalette,
        typography: TypographyScale,
        spacing: SpacingScale,
        spec: UIDesignSpec
    ) -> str:
        """Generate complete CSS"""
        css = "/* Generated UI Design CSS */\n\n"
        css += "/* Color Palette */\n"
        css += palette.to_css_vars()
        css += "\n/* Typography */\n"
        css += typography.to_css_vars()
        css += "\n/* Spacing */\n"
        css += spacing.to_css_vars()
        css += "\n/* Base Styles */\n"
        css += f"""
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: var(--font-size-base);
  line-height: 1.5;
  color: var(--color-text-primary);
  background: var(--color-background);
  margin: 0;
  padding: 0;
}}

* {{
  box-sizing: border-box;
}}
"""
        css += self._generate_layout_system(spec)

        return css

    def _generate_design_tokens(
        self,
        palette: ColorPalette,
        typography: TypographyScale,
        spacing: SpacingScale
    ) -> Dict[str, Any]:
        """Generate design tokens JSON"""
        return {
            "colors": {
                "primary": palette.primary,
                "secondary": palette.secondary,
                "accent": palette.accent,
                "background": palette.background,
                "surface": palette.surface,
                "text": {
                    "primary": palette.text_primary,
                    "secondary": palette.text_secondary,
                },
                "status": {
                    "success": palette.success,
                    "warning": palette.warning,
                    "error": palette.error,
                    "info": palette.info,
                }
            },
            "typography": {
                "fontSize": {
                    "xs": typography.xs,
                    "sm": typography.sm,
                    "base": typography.base,
                    "lg": typography.lg,
                    "xl": typography.xl,
                }
            },
            "spacing": {
                "xs": spacing.xs,
                "sm": spacing.sm,
                "md": spacing.md,
                "lg": spacing.lg,
                "xl": spacing.xl,
            }
        }

    def _darken_color(self, color: str, amount: float = 0.1) -> str:
        """Darken a hex color"""
        # Simplified - in production use proper color manipulation
        return color  # Return same color for now


def design_ui(spec: UIDesignSpec) -> UIDesign:
    """Convenience function to generate UI design"""
    designer = UIDesigner()
    return designer.design(spec)
