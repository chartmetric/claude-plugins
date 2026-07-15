---
name: write-react-code
description: Guides Claude Code in implementing features and fixes for a React TypeScript codebase following established project conventions and best practices.
author: itai@chartmetric.com
---

# Write Code React TypeScript Project

## Purpose
Guide Claude Code in implementing features and fixes for a React TypeScript codebase following established project conventions and best practices.

## Core Principles

### 1. ESLint Compliance
- **ALWAYS** check `.eslintrc.json` before writing code
- Run ESLint after making changes: `yarn lint ...`
- Fix all linting errors before completing a task
- Never ignore or disable ESLint rules without explicit user approval

### 2. TypeScript Best Practices
- Use strict type checking - no `any` types unless absolutely necessary (if absolutely necessary, use the `AnyRecord` specified type)
- Prefer `interface` for object shapes that may be extended
- Prefer `type` for unions, intersections, and utility types
- Always type function parameters and return values explicitly
- Use TypeScript utility types (`Partial`, `Pick`, `Omit`, etc.) appropriately
- Leverage type inference only when it improves readability
- Please don't add comments to explain things that can be made clear through better naming or types. Instead, refactor the code to be self-explanatory. Comments should only be used for complex business logic that cannot be simplified, and to answer "why", not "what", or to provide context that isn't obvious from the code itself.

### 3. State Management Pattern

#### When to Use Contexts and Hooks
Use Context API + custom hooks when:
- A prop is drilled through **3 or more component levels**
- Data is shared between **4 or more components**
- The data represents global or feature-level state

#### Implementation Pattern
```typescript
// types.ts
export interface MyFeatureState {
  data: string;
  isLoading: boolean;
}

export interface MyFeatureContextValue extends
{
  state: MyFeatureState;
  updateData: (data: string) => void;
}

// MyFeatureContext.tsx
import { createContext, useContext, useState, ReactNode } from 'react';
import type { MyFeatureContextValue, MyFeatureState } from './types';

const MyFeatureContext = createContext<MyFeatureContextValue | undefined>(undefined);

export function MyFeatureProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<MyFeatureState>({
    data: '',
    isLoading: false,
  });

  const updateData = (data: string) => {
    setState(prev => ({ ...prev, data }));
  };

  return (
    <MyFeatureContext.Provider value={{ state, updateData }}>
      {children}
    </MyFeatureContext.Provider>
  );
}

export function useMyFeature() {
  const context = useContext(MyFeatureContext);
  if (!context) {
    throw new Error('useMyFeature must be used within MyFeatureProvider');
  }
  return context;
}
```

#### When NOT to Use Context
- For props passed through only 1-2 levels (use prop drilling)
- For local component state (use `useState` or `useReducer`)
- For data only needed by 1-3 components in close proximity

### 4. File Organization

#### Required File Structure
Every feature or module should be organized as follows:

```
/src
  /components
    /MyFeature
      MyFeature.tsx          # Main component
      /components            # Sub-components specific to MyFeature
        FeatureChild.tsx
        FeatureItem.tsx
      utils.ts               # Helper functions specific to MyFeature
      types.ts               # Type definitions for MyFeature
      MyFeatureContext.tsx   # Context (if needed)
```

Please never include barrel files (index.ts), as it goes against the ESLint rules.

#### File Responsibilities

**utils.ts**
- Pure helper functions
- Data transformation logic
- Validation functions
- Formatting utilities
- Business logic that doesn't belong in components

```typescript
// utils.ts example
export function formatUserName(firstName: string, lastName: string): string {
  return `${firstName} ${lastName}`.trim();
}

export function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
```

**types.ts**
- All TypeScript interfaces and types
- Enums and constants with types
- Props interfaces
- State interfaces
- API response types

```typescript
// types.ts example
export interface User {
  id: string;
  email: string;
}

export type UserRole = 'admin' | 'user' | 'guest';
```

Please include component props in the component files themselves though -- do not put them in types.ts. Please also only name props types `Props`, as it is local to the component.

**components/**
- React components (one per file)
- Each component should have a single responsibility
- Component files should only contain JSX and component logic
- Import types from `types.ts`, utilities from `utils.ts`

### 6. Naming Conventions

- **Files**: PascalCase for components (`UserProfile.tsx`), camelCase for utilities (`utils.ts`)
- **Components**: PascalCase (`UserProfile`)
- **Functions/Variables**: camelCase (`getUserData`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRY_COUNT`)
- **Types/Interfaces**: PascalCase (`UserProfile`, `UserProfileProps`)
- **Hooks**: camelCase starting with `use` (`useUserData`)

### 7. Component Patterns

```typescript
// Prefer functional components with TypeScript
interface Props {
  title: string;
  onAction: () => void;
}

export function MyComponent({ title, onAction }: Props) {
  // Component logic
  const { data, isLoading } = useGetMyComponentData();
  return <div>{title}</div>;
}

// Export types alongside components when needed
export type { MyComponentProps };
```

## Implementation Workflow

When executing a plan:

1. **Analyze the requirement**
   - Identify which components need changes
   - Determine if new contexts/hooks are needed
   - Check for prop drilling depth

2. **Check existing code**
   - Review `.eslintrc.json` for rules
   - Look at existing file structure
   - Review existing types and utilities

3. **Create/modify files in order**
   - Start with `types.ts` (define interfaces first)
   - Then `utils.ts` (create helper functions)
   - Then contexts (if needed)
   - Finally components

4. **Validate**
   - Run `yarn lint-staged` to run TSC, ESLint, and Prettier on changed files
   - Fix any errors before completing

5. **Keep existing conventions**
   - Match indentation and formatting of existing code
   - Use the same import ordering
   - Follow the same commenting style

## Common Patterns to Follow

### Import Ordering
```typescript
// 1. React imports
import { useState, useEffect } from 'react';

// 2. External library imports
import { format } from 'date-fns';

// 3. Internal imports - types
import type { User, UserSettings } from './types';

// 4. Internal imports - components
import { UserProfile } from './components/UserProfile';

// 5. Internal imports - utilities
import { formatUserName } from './utils';

// 6. Styles (if applicable)
import styles from './MyComponent.module.css';
```

### Components/Styles

- The `@chartmetric/chartmetric-design-system` is the source of truth for all stylistic components, and is built on top of Tailwind CSS.
For any atoms, molecules, or organisms, prefer using components from this design system over custom components. Things like flex/containers, buttons, texts, inputs, etc. should all be found here first, and have customization applied via props or Tailwind classes.
- If custom styles are needed, prefer Tailwind instead of creating a `.module.scss` file, unless absolutely necessary. This is for consistency with the design system. This is done already in many places in the codebase.

### Error Handling
```typescript
// Always type error objects
try {
  await fetchData();
} catch (error) {
  if (error instanceof Error) {
    console.error('Failed to fetch:', error.message);
  }
}
```

## What NOT to Do

- ❌ Don't create mega-files with multiple components
- ❌ Don't put business logic directly in components (use utils.ts)
- ❌ Don't use `any` type without strong justification (use `AnyRecord` instead)
- ❌ Don't prop drill beyond 2 levels - use context instead
- ❌ Don't mix types and component code in the same file
- ❌ Don't ignore ESLint warnings
- ❌ Don't create contexts for local state

## Examples

### Example 1: Simple Feature Addition
**Task**: Add a user greeting feature

**Steps**:
1. Add types to `types.ts`:
```typescript
export interface GreetingProps {
  userName: string;
  timeOfDay: 'morning' | 'afternoon' | 'evening';
}
```

2. Add utility to `utils.ts`:
```typescript
export function getTimeOfDay(): 'morning' | 'afternoon' | 'evening' {
  const hour = new Date().getHours();
  if (hour < 12) return 'morning';
  if (hour < 18) return 'afternoon';
  return 'evening';
}
```

3. Create component in `components/Greeting.tsx`:
```typescript
import type { GreetingProps } from '../types';
import { getTimeOfDay } from '../utils';

export function Greeting({ userName }: Pick<GreetingProps, 'userName'>) {
  const timeOfDay = getTimeOfDay();
  return <h1>Good {timeOfDay}, {userName}!</h1>;
}
```

### Example 2: When to Use Context
**Scenario**: User theme is needed in Header, Sidebar, Footer, and 5 other components

**Decision**: Use Context (shared by 8 components)

**Implementation**:
1. Create `types.ts` with theme types
2. Create `ThemeContext.tsx` with provider and hook
3. Wrap app with `ThemeProvider`
4. Use `useTheme()` hook in components

## Summary

- Follow ESLint rules strictly
- Use granular, composable types
- Organize code into utils.ts, types.ts, and components/
- Use contexts when prop drilling >= 3 levels or shared by >= 4 components
- Keep TypeScript strict and explicit
- Match existing project conventions