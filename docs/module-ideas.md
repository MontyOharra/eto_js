# Pipeline Module Ideas

This document tracks ideas for potential new pipeline modules. These are not committed work items - just a backlog of possibilities to consider as needs arise.

---

## Regex Module

**Purpose:** General-purpose regex pattern matching and extraction.

**Potential Features:**
- Configurable regex pattern input
- Multiple capture group support
- Named capture groups for cleaner output mapping
- Match mode options (first match, all matches, validation only)

**Use Cases:**
- Extract structured data from free-form text
- Validate format of extracted values
- Parse complex string patterns not covered by existing modules

---

## LLM Module

**Purpose:** AI-powered text processing with configurable prompts.

**Potential Features:**
- Long text input with referenceable pass-in values
- Example prompt: `"Please extract important info from {notes_input}. Return in datetime format..."`
- Configurable model selection
- Temperature/creativity settings

**Design Challenges:**
- Customizable output schema definition
- Type inference for downstream pipeline connections
- Validation of LLM responses against expected schema
- Error handling for malformed responses
- Cost/latency considerations

**Use Cases:**
- Extract unstructured information that doesn't follow predictable patterns
- Summarize or transform text content
- Handle edge cases that rule-based modules miss

---

## Adding New Ideas

When a new module idea comes up, add it here with:
1. **Purpose** - What problem does it solve?
2. **Potential Features** - Key capabilities
3. **Design Challenges** - Technical hurdles to consider
4. **Use Cases** - Concrete examples of when it would be useful
