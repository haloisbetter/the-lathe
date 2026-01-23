# lathe/shared

**Shared data models and contracts for Lathe subsystems.**

## Purpose

This module defines the explicit data contracts used between all three subsystems:
- `lathe-prompts`
- `lathe-context`
- `lathe-validation`

## What's Included

- **Enums**: Shared enumerations (ValidationLevel, ContextSourceType, PromptScope)
- **Data Models**: Pydantic-compatible dataclasses for cross-subsystem communication
- **Contracts**: Input/output specifications for each subsystem

## What's NOT Included

- **NO business logic**
- **NO persistence logic**
- **NO subsystem-specific interfaces**
- **NO orchestration**

## Data Models

### PromptMetadata
Metadata for prompts in the registry. Used by `lathe-prompts`.

### ContextSource
Represents a single context source. Input to `lathe-context`.

### ContextOutput
Assembled context ready for AI. Output from `lathe-context`.

### ValidationRule
Defines a validation rule structure. Used by `lathe-validation`.

### ValidationResult
Result of validation. Output from `lathe-validation`.

## Enums

- **ValidationLevel**: Pass, Warn, Fail
- **ContextSourceType**: Knowledge, Memory, File, Metadata, Custom
- **PromptScope**: Global, Project, Task, Custom

## Design Principles

1. **No Cross-Subsystem Imports**: Other subsystems import only from `shared`
2. **Stateless**: These models carry no state, only structure
3. **Explicit Contracts**: Each model defines clear input/output boundaries
4. **Future-Proof**: Models are designed to support persistence adapters later

## Extension Points

To add persistence later:
1. Add a `persistence` submodule
2. Add adapters that convert these models to/from database formats
3. NO changes needed to core subsystem logic

To add new subsystems:
1. Define new models in this module
2. Import from `shared` in the new subsystem
3. Keep subsystems independent
