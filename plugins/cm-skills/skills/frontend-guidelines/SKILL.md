---
name: frontend-guidelines
description: Chartmetric Web App frontend conventions and rules — styling (Tailwind `tw-` classes vs `.module.scss`), the `@chartmetric/chartmetric-design-system` components (CMFlex, CMButton, CMContainer, CMInput, …) over raw HTML, import ordering with group comments, componentization, i18n via `useTranslation` across de/en/es/fr/ja/ko/pt, no magic numbers, and TypeScript conventions (interface over type, function-declaration components). Use when writing or reviewing React code in chartmetric-web-app, or when you need the team's frontend styling/structure rules. Pairs with the write-react-code skill.
author: itai@chartmetric.com
---

PLEASE KEEP THIS CONVENTIONS AND RULES.

# Chartmetric Web App: Conventions & Rules

## Styling

- **Tailwind Classes:** Use Tailwind (`tw-`) classes for simple, one-off styles.<br>
  _Example_: `className="tw-flex tw-items-center tw-gap-2"`
- **SCSS Modules:** Use `.module.scss` files for multi-line, dynamic, or repeated styles.

## Design System

- **Component Usage:** Always use components from `@chartmetric/chartmetric-design-system` (e.g., `CMFlex`, `CMButton`, `CMContainer`, `CMInput`) before creating custom components.
- **Component List:** Use these components instead of raw HTML tags or FontAwesomeIcon:
  - CMBrandIcon, CMButton, CMButtonToggle, CMCheckbox, CMCompositeButton, CMContainer, CMDatePicker, CMDropdown, CMFlagIcon, CMFlex, CMGenreIcon, CMIcon, CMInfoCard, CMInput, CMMoodIcon, CMPopover, CMSearchBar, CMSwitch, CMTable, CMTag, CMText, CMTextArea, CMTooltip
- **Exceptions:** Do NOT use CM design system components for `ul`, `li`, `ol`, etc.
- **CMFlex / CMContainer Props:** Use the following props for `CMFlex` and `CMContainer`:
  - **Basic:** `children`, `element` (default: div), `_className`
  - **Layout/Flex:** `justify`, `align`, `wrap`, `gap`, `vertical`, `flex`, `fullWidth`, `fullHeight`
  - **Spacing:** `p`, `pt`, `pr`, `pb`, `pl`, `m`, `mt`, `mr`, `mb`, `ml`
  - **Size & Style:** `width`, `height`, `background`, `border`, `r`, `rt`, `rb`, `rl`, `rr`
  - **Behavior:** `cursor`, `position`, `overflow`
- **Design System Styling:** Follow Chartmetric Design System spacing, typography, and component conventions across all views.

## Imports & Structure

- **Import Order:** Organize imports in this order. **For every modified file, ALWAYS comment each import group** with `// External Libraries`, `// Components`, `// Hooks`, `// Types`, `// Constants`, `// Styles` headers:
  1. External Libraries
  2. Components
  3. Hooks
  4. Types
  5. Constants
  6. Styles
- **Component Decomposition:** Split large or multi-section components into smaller ones under a subfolder.
- **Utility & Type Files:** Use `utils.ts` for reusable logic, `constants.ts` for shared constants, and `types.ts` for type definitions.
- **Componentization:** Break down complex components into smaller, reusable pieces.

## Internationalization (i18n)

- **Translation Hook:** All text must use `useTranslation`.
- **Locales:** Provide translations for `de`, `en`, `es`, `fr`, `ja`, `ko`, and `pt` in locale files.

## Code Quality & Logic

- **Magic Numbers:** Do not use literal numbers directly. Store them in `constants.ts` and use named constants.
- **Constants vs. Memoization:**
  - Use `const` for simple values without logic.
  - Use `useMemo` or `useCallback` for complex computed values used in hooks.
- **Hook Modularity:** Extract complex hooks or those with multiple side effects into separate `useXxx.ts` files.

## TypeScript Conventions

- **Interface vs. Type:** Use `interface` instead of `type` for object shapes.
- **Component Declaration:** Use `function` declarations for components, not arrow functions.<br>
  _Example_: `export function MyComponent() {}` **not** `const MyComponent = () => {}`

## Skills

- Use the "write-react-code" skill when creating new React components or modifying existing ones.
