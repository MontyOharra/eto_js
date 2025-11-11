# Claude Code Slash Commands Guide

## Overview

Slash commands are custom, reusable prompts stored as markdown files that Claude Code executes when you type `/commandname`. They provide consistency, efficiency, and documentation for repetitive analysis tasks.

## Directory Structure

```
eto_js/
├── .claude/
│   ├── CLAUDE.md          # Project instructions
│   └── commands/          # Slash commands directory
│       ├── analyze-vba.md
│       ├── vba-to-python.md
│       └── migration-plan.md
```

## Creating Slash Commands

### File Format

Each `.md` file becomes a command. Filename = command name:
- `analyze-vba.md` → `/analyze-vba`
- `vba-to-python.md` → `/vba-to-python`

### Basic Structure

```markdown
---
description: Short description shown in autocomplete
---

Your prompt goes here. You can use:
- Multiple lines
- **Markdown formatting**
- Code blocks
- Variables/placeholders
```

## Example Commands for VBA Analysis

### 1. Analyze VBA Function (`analyze-vba.md`)

```markdown
---
description: Analyze a VBA code snippet and explain its functionality
---

Please analyze the following VBA code:

1. **Purpose**: What does this code do in plain English?
2. **Dependencies**: What Access objects, tables, or external dependencies does it use?
3. **Business Logic**: What business rules are implemented?
4. **Data Flow**: What data goes in and what comes out?
5. **Complexity**: Rate complexity (Low/Medium/High) and explain why
6. **Modern Equivalent**: How would you implement this in TypeScript/Python?
7. **Migration Notes**: Any challenges or considerations for migrating this?

Please be thorough and cite specific line numbers when referencing the code.
```

### 2. VBA to Python Migration (`vba-to-python.md`)

```markdown
---
description: Convert VBA code to Python for backend migration
---

Please convert the following VBA code to Python:

**Requirements:**
- Use modern Python 3.11+ syntax
- Use SQLAlchemy for database operations
- Use Pydantic for data validation
- Follow our existing codebase patterns in `server/src/`
- Add type hints
- Include docstrings
- Handle errors appropriately
- Add inline comments for complex logic

**Output Format:**
1. Python code
2. Required imports
3. Any new database models needed
4. Test cases (if applicable)
5. Migration notes

Please preserve the business logic exactly while modernizing the implementation.
```

### 3. VBA Inventory (`vba-inventory.md`)

```markdown
---
description: Create an inventory of VBA modules, functions, and dependencies
---

Please analyze all VBA files in the `vba-code/` directory and create a structured inventory:

## Inventory Format

For each VBA file:
- **File**: Filename
- **Module Type**: Standard Module / Form / Class
- **Functions/Subs**: List with brief description
- **Dependencies**:
  - Database tables accessed
  - External references
  - Other VBA modules called
- **Complexity Score**: 1-10
- **Migration Priority**: High / Medium / Low (based on business impact)

Create a summary table at the end showing:
- Total functions
- Most complex modules
- Most interconnected modules
- Suggested migration order
```

### 4. Migration Plan Generator (`migration-plan.md`)

```markdown
---
description: Generate a detailed migration plan for a VBA module
---

Based on the VBA code provided, create a detailed migration plan:

## Migration Plan

### 1. Analysis
- What does this code do?
- What are the dependencies?

### 2. Modern Architecture
- Where does this fit in our new system? (Frontend/Backend/Both)
- What new tables/schemas are needed?
- What API endpoints are needed?

### 3. Implementation Steps
Break down into small, testable chunks:
- [ ] Step 1
- [ ] Step 2
- [ ] etc.

### 4. Data Migration
- What data needs to be migrated?
- Transformation rules?

### 5. Testing Strategy
- Unit tests needed
- Integration tests needed
- Manual testing steps

### 6. Risks & Challenges
- Technical risks
- Business continuity concerns
- Rollback plan

### 7. Effort Estimate
- Development time
- Testing time
- Dependencies on other work
```

### 5. VBA Pattern Detector (`vba-patterns.md`)

```markdown
---
description: Detect common VBA patterns and anti-patterns
---

Analyze this VBA code for common patterns:

**Look for:**
1. **Database Access Patterns**: DAO vs ADO, connection handling
2. **Error Handling**: On Error Resume Next, error trapping
3. **Form/UI Logic**: User interaction patterns
4. **Business Logic**: Calculations, validations, workflows
5. **Data Manipulation**: Recordset loops, SQL queries
6. **Anti-patterns**:
   - Hard-coded values
   - Lack of error handling
   - Copy-paste code duplication
   - Magic numbers
   - Poor variable naming

**Output:**
- List of patterns found (with line numbers)
- Recommendations for modernization
- Reusable components that could be extracted
```

## Usage

1. **Create the directory**: `mkdir -p .claude/commands`

2. **Create command files**: Copy the examples above into `.md` files

3. **Use in chat**:
   ```
   /analyze-vba
   [Claude will prompt you for the VBA code]
   ```

4. **View available commands**: Type `/` to see all commands with descriptions

## Best Practices

### 1. Start Simple, Iterate
Begin with basic commands and refine based on actual usage.

### 2. One Purpose Per Command
Don't make mega-commands. Better to have multiple focused commands.

### 3. Include Project Context
Reference your project structure, coding standards, patterns:
```markdown
Follow the patterns in `server/src/modules/` for module structure.
Use the same database models as in `server/src/models/`.
```

### 4. Make Commands Self-Documenting
Include examples in the command itself showing expected output format.

### 5. Version Control Them
Slash commands are just files - commit them to git so your team can use them.

## Suggested Workflow for VBA Migration

1. **Initial Exploration**: `/vba-inventory` - Creates overview of all VBA code
2. **Deep Dive**: `/analyze-vba` - Analyze specific modules
3. **Plan Migration**: `/migration-plan` - Create detailed migration plan
4. **Implement**: `/vba-to-python` - Convert VBA to Python
5. **Compare**: `/compare-vba` - Compare different approaches

## Advanced Claude Code Features

For reference, here are other advanced features that complement slash commands:

### Task Tool / Specialized Agents
Multiple types of AI agents for specific tasks (e.g., Explore agent for codebase exploration)

### MCP (Model Context Protocol) Servers
External tools/services to extend capabilities (databases, APIs, custom data sources)

### Skills
Reusable capability packages similar to slash commands but more structured

### CLAUDE.md Files
Project-specific instructions Claude reads at conversation start (you already have this)

### Hooks
Shell commands that automatically execute in response to events

### Context Management (.claudeignore)
Control what files Claude can see to manage token usage

### TodoWrite Tool
Task tracking system for breaking down complex work into steps

### Multi-file Pattern Matching (Glob tool)
Efficient searching across entire codebases with pattern matching

## Next Steps

To get started with VBA analysis:

1. Create `.claude/commands/` directory
2. Copy the example commands above into individual `.md` files
3. Run `/vba-inventory` to get an overview of your VBA codebase
4. Use `/analyze-vba` on individual modules to understand functionality
5. Generate migration plans with `/migration-plan`

The `vba-code/` directory is ready for analysis using these commands.
