---
page: actas
---
A professional management system for IT Delivery Receipts (Actas) for JMIE.

**DESIGN SYSTEM (REQUIRED):**
### 1. Visual Theme & Atmosphere
The design is **Dense, Technical, and Precision-oriented**. It uses a sophisticated **Dark Mode (OLED)** aesthetic that emphasizes focus and productivity. The atmosphere is professional and high-end, utilizing glassmorphism and subtle elevation to create depth.

### 2. Color Palette & Roles
- **Corporate Blue (#003594)**: Used for brand identity, focus rings, and secondary information badges.
- **Vibrant Orange (#ED8B00)**: Primary Action color. Used for high-priority CTAs, active highlights, and critical visual indicators.
- **Deep Slate Background (#0a0c14)**: The primary surface color for the entire application.
- **Mid-Surface Slate (#171c28)**: Background color for input fields, selects, and containers.
- **Elevated Slate (#1e2533)**: Used for hover states, card backgrounds, and glass panels.
- **Accent Slate (#2a3344)**: Used for badges, tooltips, and secondary UI elements.
- **Clean White (#f0f3f8)**: Primary text color for high readability.
- **Muted Gray (#7C878E)**: Used for labels, secondary text, and placeholder information.

### 3. Typography Rules
- **Font Family**: Montserrat (Variable) is the primary font for all UI elements.
- **Headlines**: Extra bold or Black (`font-black`) with tight tracking (`tracking-tighter`) for a strong, industrial feel.
- **Body**: Semi-bold or Medium weight for high legibility on dark backgrounds.
- **Labels**: Small uppercase text (`text-[10px]`) with wide tracking (`tracking-widest`) and high bold weight.

### 4. Component Stylings
* **Buttons**:
    - **Primary**: Solid Vibrant Orange (#ED8B00) with white text. Slightly rounded corners (0.5rem). Strong glow shadow on hover.
    - **Secondary**: Subtle Slate (#1e2533) with border, becoming more prominent on hover.
    - **Interaction**: All buttons must have an `active:scale-95` micro-interaction.
* **Cards/Containers**:
    - **Shape**: Rounded corners (0.75rem or 1rem).
    - **Background**: Glass panels with `backdrop-blur-lg` and `bg-white/5` or `bg-surface-container-low`.
    - **Borders**: Paper-thin borders (`border-white/5`) for subtle separation.
* **Inputs/Forms**:
    - **Fields**: Background Mid-Surface Slate (#171c28), rounded (0.5rem).
    - **Focus**: Clear ring indicator in Corporate Blue (#003594) with a 2px offset.
    - **Validation**: Error states use a sharp red border and semantic error text.

### 5. Layout Principles
- **Whitespace**: Generous but structured spacing using a 4/8px grid system.
- **Density**: High information density suitable for expert users, but with clear visual hierarchy.
- **Navigation**: Persistent left sidebar with clean, icon-based navigation.

**Page Structure:**
1. A dense list of generated Actas (receipts) with status badges (Draft, Signed, Archived).
2. Action buttons for "Sign Document", "Download PDF", and "View Details".
3. A summary panel showing "Pending Signatures" and "Documents this month".
4. Professional filtering system by Colaborador and Date Range.
