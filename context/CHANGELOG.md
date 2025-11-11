# CHANGELOG

## [2025-11-10 19:30] — Template Version Editing & VBA Migration Setup
### Spec / Intent
- Fix config editability in view mode for pipeline viewer
- Fix connection validation for initialized modules in template builder
- Preserve current step when switching template versions
- Set up VBA migration infrastructure and documentation

### Changes Made
- Files Modified:
  - `client/src/renderer/features/pipelines/components/PipelineGraph/ConfigSection.tsx`
  - `client/src/renderer/features/pipelines/components/PipelineGraph/ModuleConfig.tsx`
  - `client/src/renderer/features/pipelines/components/PipelineGraph/PipelineGraph.tsx`
  - `client/src/renderer/features/templates/components/TemplateDetail/TemplateDetailModal.tsx`

- Files Created:
  - `context/docs/CLAUDE_CODE_SLASH_COMMANDS.md` - Comprehensive guide to slash commands for VBA analysis
  - `vba-code/HTC_350C_Sub_1_of_2_translation.vba` - Original VBA code for migration
  - `vba-code/HTC_350C_Sub_2_of_2_createorders.vba` - Original VBA code for migration

### Summary of Fixes

#### 1. Config Editability in View Mode (commit: 6259021)
**Problem**: Config inputs were editable in view mode because ModuleConfig always passed a wrapper function to ConfigSection.
**Solution**: Made onConfigChange optional in ConfigSectionProps, conditionally pass undefined in view mode.

#### 2. Connection Validation for Initialized Modules (commit: 56a0703)
**Problem**: Connection validation used raw pipelineState lacking enriched metadata (allowed_types, direction, label, type_var), causing validation failures.
**Solution**: Updated all validation and type system operations to use enrichedPipelineState:
- `isValidConnection`: Uses enriched state for correct allowed_types
- `onConnect`: Validates with enriched state, persists to raw state
- `handleUpdateNode`: Calculates propagation with enriched state
- `effectiveTypesCache`: Computed from enriched state
Pattern: Read from enriched (for metadata), write to raw (for persistence).

#### 3. Template Version Step Preservation (commit: 6e5db09)
**Problem**: Switching template versions reset to signature-objects step, disrupting workflow.
**Solution**: Removed step reset from handleVersionChange to preserve current view.

### Next Actions
- Create `.claude/commands/` directory with VBA analysis slash commands
- Run `/vba-inventory` to analyze VBA codebase structure
- Begin systematic VBA to Python/TypeScript migration
- Define new pipeline module definitions for database writing

### Notes
- VBA migration is full rewrite of previous MS Access/VBA system
- VBA code stored in `vba-code/` directory for analysis
- Slash commands documented in `context/docs/CLAUDE_CODE_SLASH_COMMANDS.md`
- All recent commits ready to push to remote
