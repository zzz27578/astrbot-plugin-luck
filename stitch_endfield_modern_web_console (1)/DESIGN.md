```markdown
# Design System Specification: Biomechanical Precision

### 1. Overview & Creative North Star
**Creative North Star: "The Clinical Greenhouse"**

This design system is a sophisticated dialogue between two opposing forces: the sterile, high-precision world of industrial technology and the untamed, deep-toned essence of organic life. It moves beyond standard "minimalism" by embracing a "Clinical Greenhouse" aesthetic—where expansive white space (Technology) is punctuated by dense, mossy structures (Life) and illuminated by high-frequency data highlights. 

We break the "template" look through **Rigid Asymmetry**. While the grid is strict, the content should feel like a technical schematic overlaid on a natural landscape. We avoid the "web-standard" softened corners in favor of aggressive, 0px industrial bevels, creating an interface that feels like a precision instrument.

---

### 2. Colors
The palette is rooted in the contrast between high-key whites and low-key greens, bridged by a hyper-modern mint-cyan.

*   **Primary (The Forest Core):** `#1B3022` (`primary_container`). This represents the "Life" element. Use this for heavy industrial panels, structural headers, and primary navigation blocks.
*   **Secondary (The Data Pulse):** `#5FF2D0` (mapped to `secondary_fixed`). This is your high-precision highlight. Use it for data visualizations, active states, and critical terminal readouts.
*   **Surface (The Clinical Void):** `#FFFFFF` (`surface_container_lowest`). This is the dominant theme. It must feel surgical and breathable.

**The "No-Line" Rule**
Traditional 1px borders are strictly prohibited for sectioning. Boundaries must be defined through background color shifts. To separate a side panel from a main view, transition from `surface` to `surface_container_low`. The eye should perceive the change in depth through tonal shifts, not "drawn" lines.

**The "Glass & Gradient" Rule**
For floating modals or technical overlays, use Glassmorphism. Apply `surface_container` colors at 70-80% opacity with a heavy `backdrop-blur (20px)`. To add "soul" to primary CTAs, use a subtle linear gradient from `primary` to `primary_container` at a 135-degree angle.

---

### 3. Typography
The typography system is a dual-font architecture designed to feel like an editorial terminal.

*   **Technical High-Precision (Space Grotesk):** Used for `display`, `headline`, and `label` roles. Space Grotesk provides a "terminal" feel with professional, high-end geometric construction. Use it for data points, headers, and UI controls.
*   **Functional Clarity (Inter):** Used for `body` and `title` roles. Inter provides the necessary neutral balance to the technicality of Space Grotesk, ensuring long-form readability without distracting from the "industrial" aesthetic.

**Typographic Hierarchy as Identity**
Large-scale Display headers should use `display-lg` with tight tracking (-2%) to feel like a structural element. Labels (`label-sm`) should be set in all-caps with increased letter spacing (+10%) to mimic technical metadata found in architectural blueprints.

---

### 4. Elevation & Depth
Depth in this system is not achieved through "fluff" or traditional shadows, but through **Tonal Layering** and **Industrial Bevels**.

*   **The Layering Principle:** Treat the UI as stacked sheets of material. A `surface_container_lowest` card sits atop a `surface_container_low` background. This "stacking" creates hierarchy through value rather than light source simulation.
*   **Ambient Shadows:** If a floating element (like a context menu) requires a shadow, it must be nearly imperceptible. Use a 32px blur with 4% opacity, tinted with the `primary` color (`#1B3022`) to ensure it feels like it belongs to the environment.
*   **The "Ghost Border" Fallback:** If containment is functionally required, use a "Ghost Border": the `outline_variant` at 15% opacity.
*   **Industrial Corners:** All containers must maintain a `0px` border radius. To create the "Bevel" look mentioned in the creative brief, use CSS `clip-path` to "dog-ear" the corners of primary panels at a 45-degree angle.

---

### 5. Components

**Buttons**
*   **Primary:** Solid `primary_container` (#1B3022) with `on_primary` text. Sharp 0px corners.
*   **Secondary:** `outline` variant with a technical "glitch" hover state (momentary shift to `secondary_fixed`).
*   **Technical/Action:** High-contrast `secondary_container` (#5FF2D0) for mission-critical actions.

**Cards & Containers**
*   **Forbid Divider Lines:** Use vertical white space or a shift from `surface_container_lowest` to `surface_container_high`.
*   **The "Ink-Wash" Backdrop:** Major layout sections (e.g., the Hero or Dashboard background) should feature a subtle, low-contrast ink-wash texture—a faded, organic shadow play that softens the rigid tech elements.

**Technical Terminals (Data Fields)**
*   Input fields should not be boxes. Use a bottom-only border (2px `primary`) with a `label-sm` technical tag floating in the top-left, reminiscent of a command-line interface.

**Progress & Data**
*   Use the `secondary_fixed` (#5FF2D0) for all progress bars and data pips. These should be thin (2px-4px) and grouped in clusters to resemble motherboard circuitry.

---

### 6. Do’s and Don’ts

**Do:**
*   **Do** use extreme white space. The "Technology" theme requires the UI to breathe.
*   **Do** align technical data to a strict grid, but allow "Life" elements (ink-wash shadows, moss green panels) to break the grid slightly for visual interest.
*   **Do** use `Space Grotesk` for all numbers and statistics.

**Don’t:**
*   **Don’t** ever use a border-radius. Even a 2px radius destroys the industrial precision.
*   **Don’t** use pure black. Use `primary` (#1B3022) for your darkest values to maintain the "Life" infusion.
*   **Don’t** use standard drop shadows. If it doesn't look like it was machined in a factory or grown in a lab, it doesn't belong.
*   **Don’t** use icons with rounded caps. All iconography must be sharp, stroke-based, and geometric.```