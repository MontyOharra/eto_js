# Feature: New Pipeline Modules

## Overview

Add new pipeline modules for math operations and general LLM processing.

---

## 1. Math Modules

### Modules to Implement

| Module | Identifier | Operation | Notes |
|--------|------------|-----------|-------|
| Add | `math_add` | a + b + c + ... | Sum all inputs |
| Subtract | `math_subtract` | a - b - c - ... | Subtract in order |
| Multiply | `math_multiply` | a * b * c * ... | Product of all inputs |
| Divide | `math_divide` | a / b / c / ... | Divide in order |

### Common Structure

All math modules share the same I/O pattern:

```python
@classmethod
def meta(cls) -> ModuleMeta:
    return ModuleMeta(
        io_shape=IOShape(
            inputs=IOSideShape(
                nodes=[
                    NodeGroup(
                        label="number",
                        typing=NodeTypeRule(allowed_types=["int", "float"]),
                        min_count=2,      # Minimum 2 inputs
                        max_count=None    # Unlimited
                    )
                ]
            ),
            outputs=IOSideShape(
                nodes=[
                    NodeGroup(
                        label="result",
                        typing=NodeTypeRule(allowed_types=["float"]),
                        min_count=1,
                        max_count=1
                    )
                ]
            )
        )
    )
```

### Module Metadata

```python
# Common attributes for all math modules
kind = "transform"
category = "Math"
color = "#8B5CF6"  # Purple for math
```

### Implementation Pattern

```python
def run(self, inputs, cfg, context, access_conn_manager=None):
    # Collect all input values in order
    values = [inputs[node.node_id] for node in context.inputs]

    # Perform operation (varies per module)
    result = self._compute(values)

    return {context.outputs[0].node_id: float(result)}
```

### Individual Module Logic

**Add:**
```python
def _compute(self, values):
    return sum(values)
```

**Subtract:**
```python
def _compute(self, values):
    result = values[0]
    for v in values[1:]:
        result -= v
    return result
```

**Multiply:**
```python
def _compute(self, values):
    result = 1
    for v in values:
        result *= v
    return result
```

**Divide:**
```python
def _compute(self, values):
    result = values[0]
    for v in values[1:]:
        if v == 0:
            raise ValueError("Division by zero")
        result /= v
    return result
```

### Config

Math modules require no configuration (empty ConfigModel or minimal options like rounding).

```python
class MathModuleConfig(BaseModel):
    """Optional: round result to N decimal places"""
    decimal_places: int | None = Field(None, description="Round result to N decimals (None = no rounding)")
```

---

## 2. General LLM Module

### Overview

A flexible LLM module that allows users to:
- Define multiple named inputs that map to `${variable}` placeholders in the prompt
- Define an output JSON schema that the LLM should return
- Configure the system prompt template with variable injection

### Module Metadata

```python
identifier = "llm_processor"
version = "1.0.0"
title = "LLM Processor"
description = "Process inputs through an LLM with customizable prompts and structured output"
kind = "transform"
category = "LLM"
color = "#10B981"  # Green for LLM
```

### Configuration Schema

```python
class LLMProcessorConfig(BaseModel):
    """Configuration for the general LLM module"""

    # Prompt template with ${variable} placeholders
    prompt_template: str = Field(
        ...,
        description="Prompt template. Use ${variable_name} to inject input values. Example: 'Parse this address: ${delivery_address}'"
    )

    # Output schema definition
    output_schema: dict = Field(
        ...,
        description="JSON schema defining expected output structure. Example: {'state': 'str', 'city': 'str', 'zip': 'str'}"
    )

    # LLM settings
    model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use"
    )

    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for response randomness (0 = deterministic)"
    )

    # Optional system context
    system_context: str | None = Field(
        None,
        description="Additional system context prepended to the prompt"
    )
```

### I/O Shape

The module has:
- **Inputs**: Multiple text inputs (names defined elsewhere or inferred from prompt)
- **Output**: Single JSON string output (parsed according to output_schema)

```python
@classmethod
def meta(cls) -> ModuleMeta:
    return ModuleMeta(
        io_shape=IOShape(
            inputs=IOSideShape(
                nodes=[
                    NodeGroup(
                        label="input",
                        typing=NodeTypeRule(allowed_types=["str"]),
                        min_count=1,
                        max_count=None  # Multiple inputs allowed
                    )
                ]
            ),
            outputs=IOSideShape(
                nodes=[
                    NodeGroup(
                        label="output",
                        typing=NodeTypeRule(allowed_types=["str"]),  # JSON string
                        min_count=1,
                        max_count=None  # Multiple outputs based on schema
                    )
                ]
            )
        )
    )
```

### Validation

Custom validation to ensure prompt variables match inputs and output schema matches outputs:

```python
@classmethod
def validate_config(cls, cfg: LLMProcessorConfig, inputs, outputs, services=None) -> list[str]:
    errors = []

    # Extract ${variable} placeholders from prompt
    import re
    prompt_vars = set(re.findall(r'\$\{(\w+)\}', cfg.prompt_template))

    # Get input node names
    input_names = {inp.name for inp in inputs}

    # Check all prompt variables have corresponding inputs
    missing_inputs = prompt_vars - input_names
    if missing_inputs:
        errors.append(f"Prompt references undefined inputs: {missing_inputs}")

    # Check all inputs are used in prompt
    unused_inputs = input_names - prompt_vars
    if unused_inputs:
        errors.append(f"Inputs not used in prompt: {unused_inputs}")

    # Validate output schema keys match output nodes
    schema_keys = set(cfg.output_schema.keys())
    output_names = {out.name for out in outputs}

    if schema_keys != output_names:
        errors.append(f"Output schema keys {schema_keys} don't match output nodes {output_names}")

    return errors
```

### Execution Flow

```python
def run(self, inputs, cfg: LLMProcessorConfig, context, access_conn_manager=None):
    from openai import OpenAI
    import os
    import json
    import re

    # 1. Build prompt by injecting input values
    prompt = cfg.prompt_template
    for input_node in context.inputs:
        var_name = input_node.name
        value = inputs[input_node.node_id]
        prompt = prompt.replace(f"${{{var_name}}}", str(value))

    # 2. Build system message
    system_parts = []
    if cfg.system_context:
        system_parts.append(cfg.system_context)

    # Add output format instruction
    system_parts.append(
        f"Respond with a JSON object matching this schema: {json.dumps(cfg.output_schema)}"
    )
    system_message = "\n\n".join(system_parts)

    # 3. Call LLM
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=cfg.model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        temperature=cfg.temperature,
        response_format={"type": "json_object"}
    )

    # 4. Parse response
    content = response.choices[0].message.content
    parsed = json.loads(content)

    # 5. Map to outputs
    result = {}
    for output_node in context.outputs:
        key = output_node.name
        if key in parsed:
            result[output_node.node_id] = parsed[key]
        else:
            result[output_node.node_id] = None

    return result
```

### Example Usage

**Config:**
```json
{
    "prompt_template": "Parse this delivery address into components: ${delivery_address}",
    "output_schema": {
        "street": "str",
        "city": "str",
        "state": "str",
        "zip": "str"
    },
    "model": "gpt-4o-mini",
    "temperature": 0.0
}
```

**Inputs:**
- `delivery_address`: "123 Main St, Dallas, TX 75201"

**Outputs:**
- `street`: "123 Main St"
- `city`: "Dallas"
- `state`: "TX"
- `zip`: "75201"

---

## Implementation Checklist

### Math Modules

- [ ] Create `server/src/features/modules/definitions/transform/math_add.py`
- [ ] Create `server/src/features/modules/definitions/transform/math_subtract.py`
- [ ] Create `server/src/features/modules/definitions/transform/math_multiply.py`
- [ ] Create `server/src/features/modules/definitions/transform/math_divide.py`
- [ ] Add error handling for division by zero
- [ ] Test with 2 inputs
- [ ] Test with 3+ inputs
- [ ] Test with mixed int/float inputs

### LLM Module

- [ ] Create `server/src/features/modules/definitions/transform/llm_processor.py`
- [ ] Implement config schema with prompt_template and output_schema
- [ ] Implement variable injection (${var} replacement)
- [ ] Implement validation (prompt vars ↔ inputs, schema ↔ outputs)
- [ ] Implement LLM execution with JSON mode
- [ ] Handle LLM errors gracefully
- [ ] Test with single input/output
- [ ] Test with multiple inputs/outputs
- [ ] Test validation error cases

### Frontend (if needed)

- [ ] Verify math modules render correctly in pipeline editor
- [ ] Verify LLM module config UI works with prompt_template textarea
- [ ] Verify output_schema config input (JSON editor or structured form)
