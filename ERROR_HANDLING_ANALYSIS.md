# Pipeline Error Handling Flow Analysis

## Complete Error Flow (When a Module Throws an Error)

### 1. **Module Execution** (service_execution.py, lines 719-732)

```python
try:
    config_instance = ConfigModel(**step.module_config)
    outputs_dict = handlerInstance.run(
        inputs=inputs_dict,
        cfg=config_instance,
        context=ctx
    )
    error = None
except Exception as e:
    outputs_dict = {}
    error = f"{type(e).__name__}: {e}"  # Format: "RuntimeError: This is a test error"
    logger.exception(f"Module {step.module_instance_id} failed: {e}")
```

**What happens:**
- Module's `run()` method throws an exception (e.g., `RuntimeError("This is a test error")`)
- Exception is caught
- Error string is formatted as: `"RuntimeError: This is a test error"`
- outputs_dict is set to empty `{}`

---

### 2. **Step Result Collection** (service_execution.py, lines 734-747)

```python
# Collect step result
step_result = PipelineExecutionStepResult(
    module_instance_id=step.module_instance_id,
    step_number=step.step_number,
    inputs=audit_inputs,
    outputs=audit_outputs,
    error=error  # "RuntimeError: This is a test error"
)
collector.add(step_result)

# Fail fast on error
if error:
    raise RuntimeError(error)  # Raises RuntimeError("RuntimeError: This is a test error")
```

**What happens:**
- Step result is created with the error field set
- Step result is added to the collector (thread-safe)
- A **NEW** RuntimeError is raised, wrapping the already-formatted error string
- This causes the error message to be wrapped AGAIN later

**IMPORTANT:** The step result has the CORRECT error (single prefix). The re-raising creates the double prefix problem at the pipeline level.

---

### 3. **Dask Graph Execution** (service_execution.py, lines 426-438)

```python
try:
    compute(*leaves)  # Raises on first failure (propagates the RuntimeError from step 2)
    status = "success"
    error = None
except Exception as e:
    status = "failed"
    error = f"{type(e).__name__}: {e}"  # "RuntimeError: RuntimeError: This is a test error"
    logger.exception(f"Pipeline execution failed: {e}")
```

**What happens:**
- Dask's `compute()` executes the task graph
- The RuntimeError from step 2 propagates up and is caught here
- Error is formatted AGAIN as `"ExceptionType: message"`
- Since the exception is `RuntimeError("RuntimeError: This is a test error")`, we get:
  - `type(e).__name__` = "RuntimeError"
  - `str(e)` = "RuntimeError: This is a test error"
  - Final: `"RuntimeError: RuntimeError: This is a test error"`

**PROBLEM:** This is where the double-prefixing happens!

---

### 4. **Pipeline Result Return** (service_execution.py, lines 440-451)

```python
collected_steps = collector.get_all()

return PipelineExecutionResult(
    status=status,                      # "failed"
    steps=collected_steps,              # Contains step with error="RuntimeError: This is a test error"
    executed_actions=...,
    error=error                         # "RuntimeError: RuntimeError: This is a test error"
)
```

**What happens:**
- All collected step results are retrieved
- Pipeline result is created with:
  - **Step-level errors**: CORRECT (single prefix) - `"RuntimeError: This is a test error"`
  - **Pipeline-level error**: DOUBLE-PREFIXED - `"RuntimeError: RuntimeError: This is a test error"`

---

### 5. **API Response Mapping** (pdf_templates.py mapper, lines 310-327)

```python
pipeline_steps = [
    ExecutionStepResult(
        module_instance_id=step.module_instance_id,
        step_number=step.step_number,
        inputs=step.inputs,
        outputs=step.outputs,
        error=step.error  # "RuntimeError: This is a test error" (CORRECT)
    )
    for step in result.execution_result.steps
]

return SimulateTemplateResponse(
    extraction_results=extraction_results,
    pipeline_status=result.execution_result.status,  # "failed"
    pipeline_steps=pipeline_steps,
    pipeline_actions=result.execution_result.executed_actions,
    pipeline_error=result.execution_result.error  # "RuntimeError: RuntimeError: ..." (DOUBLE)
)
```

**What happens:**
- Domain types are converted to API DTOs
- Step errors are passed through correctly (single prefix)
- Pipeline error is passed through with double prefix

---

### 6. **Frontend Mapping** (TemplateBuilderModal.tsx, lines 288-327)

```typescript
// Parse error type and message from pipeline_error (format: "ErrorType: message")
let errorType: string | null = null;
let errorMessage: string | null = null;
if (response.pipeline_error) {
    const colonIndex = response.pipeline_error.indexOf(':');
    if (colonIndex > 0) {
        errorType = response.pipeline_error.substring(0, colonIndex).trim();
        errorMessage = response.pipeline_error.substring(colonIndex + 1).trim();
    } else {
        errorMessage = response.pipeline_error;
    }
}

const simulationResult: TemplateSimulationResult = {
    status: response.pipeline_status === 'success' ? 'success' : 'failure',
    error_type: errorType,  // "RuntimeError"
    error_message: errorMessage,  // "RuntimeError: This is a test error"
    pipeline_execution: {
        status: response.pipeline_status,
        error_message: response.pipeline_error,  // Full double-prefixed string
        steps: response.pipeline_steps.map(step => ({
            ...
            error: step.error,  // "RuntimeError: This is a test error" (CORRECT)
        })),
    },
};
```

**What happens:**
- `pipeline_error` = `"RuntimeError: RuntimeError: This is a test error"`
- First colon splits at position after first "RuntimeError"
- `errorType` = `"RuntimeError"`
- `errorMessage` = `"RuntimeError: This is a test error"` (still has one prefix!)
- Step errors are mapped correctly with single prefix

**PROBLEM:** The error_message still has "RuntimeError:" in it because of the double prefix!

---

### 7. **Frontend Display** (TestingStep.tsx, lines 293-303)

```typescript
{simulationResult.status === 'failure' ? (
  <div className="text-red-300">
    <p className="font-bold mb-2">Error Type: {simulationResult.error_type || 'Unknown'}</p>
    <p className="mb-2">Message: {simulationResult.error_message || 'No error message available'}</p>
    {simulationResult.pipeline_execution?.error_message && (
      <>
        <p className="font-bold mb-2 mt-4">Pipeline Error:</p>
        <p>{simulationResult.pipeline_execution.error_message}</p>
      </>
    )}
  </div>
) : ...}
```

**What displays:**
- **Error Type:** RuntimeError
- **Message:** RuntimeError: This is a test error (STILL HAS PREFIX!)
- **Pipeline Error:** RuntimeError: RuntimeError: This is a test error (FULL DOUBLE PREFIX)

---

### 8. **Failed Module Highlighting** (TestingStep.tsx, lines 141-169)

```typescript
const failedModules: string[] = [];

if (simulationResult.pipeline_execution?.steps) {
    simulationResult.pipeline_execution.steps.forEach(step => {
        // ... collect inputs/outputs ...

        // Track failed modules
        if (step.error) {
            failedModules.push(step.module_instance_id);
        }
    });
}

setFailedModuleIds(failedModules);
```

**What happens:**
- Iterates through all steps
- If `step.error` is truthy, adds module_instance_id to failedModules
- Failed modules are highlighted in the pipeline visualization

**THIS SHOULD BE WORKING** - The step.error field is correctly set!

---

## Problems Identified

### 1. **Double Prefixing**
- **Root Cause:** Line 752 in service_execution.py raises a NEW RuntimeError wrapping an already-formatted error string
- **Impact:** Pipeline-level error has double "RuntimeError:" prefix
- **Fix:** Don't format the error again when catching at pipeline level, OR don't raise a new RuntimeError

### 2. **Error Message Still Has Prefix**
- **Root Cause:** Frontend splits on first colon, leaving the second "RuntimeError:" in the message
- **Impact:** Error message shows "RuntimeError: This is a test error" instead of just "This is a test error"
- **Fix:** Better parsing to handle multiple colons, or fix the double-prefixing at the source

### 3. **What About the Visual Highlighting?**

The `failedModuleIds` should be populated correctly because:
- Step has `error` field set (line 744)
- Frontend checks `if (step.error)` (line 166)
- Adds `module_instance_id` to `failedModules`

**If the visual highlighting isn't working, the issue is likely:**
- The `ExecutedPipelineGraph` component not using `failedModuleIds` correctly
- OR the module instance ID doesn't match between the step result and the visual state

---

## Recommendations

### Option 1: Fix at the Source (Preferred)
**Don't double-wrap the error:**

```python
# service_execution.py, line 750-752
if error:
    logger.info(f"Raising RuntimeError due to module error: {error}")
    raise RuntimeError(error)  # This creates RuntimeError("RuntimeError: message")
```

**Change to:**

```python
# Re-raise the original exception type instead of wrapping
if error:
    logger.info(f"Stopping pipeline due to module error: {error}")
    # Extract original exception type and message
    if ':' in error:
        exc_type_name, exc_message = error.split(':', 1)
        exc_message = exc_message.strip()
    else:
        exc_type_name = 'RuntimeError'
        exc_message = error

    # Raise with original type name for better error messages
    raise RuntimeError(exc_message)  # Just the message, no type prefix
```

Then at line 437:

```python
except Exception as e:
    status = "failed"
    # If exception message already has type prefix, don't add it again
    error_msg = str(e)
    if not error_msg.startswith(type(e).__name__):
        error = f"{type(e).__name__}: {error_msg}"
    else:
        error = error_msg  # Already formatted
```

### Option 2: Fix in Frontend Parsing
**Better error parsing to strip ALL prefixes:**

```typescript
if (response.pipeline_error) {
    // Handle multiple colons (e.g., "RuntimeError: RuntimeError: message")
    const parts = response.pipeline_error.split(':').map(p => p.trim());

    if (parts.length >= 2) {
        // Find the actual message (last non-error-type part)
        let messageIndex = parts.length - 1;
        for (let i = parts.length - 2; i >= 0; i--) {
            if (parts[i].match(/^[A-Z][a-zA-Z]*Error$/)) {
                // This is an error type name
                errorType = parts[i];
            } else {
                // This is part of the message
                messageIndex = i;
                break;
            }
        }

        errorMessage = parts.slice(messageIndex).join(':').trim();
    } else {
        errorMessage = response.pipeline_error;
    }
}
```

### Option 3: Don't Fail Fast (Alternative Approach)
**Remove the fail-fast behavior** and let all modules execute even after errors:

```python
# service_execution.py, lines 749-752
# Collect step result with error, but DON'T raise
# This allows other modules to execute
# collector.add(step_result)  # Already done above

# REMOVE THIS:
# if error:
#     raise RuntimeError(error)

return outputs_dict  # Return empty dict, but don't crash the graph
```

This would allow multiple modules to fail and all errors to be collected. But this changes the execution semantics significantly.

---

## Current State Summary

**Backend:**
- ✅ Step-level errors are captured correctly (single prefix)
- ❌ Pipeline-level error has double prefix
- ✅ Failed modules are tracked in step results

**Frontend:**
- ✅ Step errors are mapped correctly
- ❌ Error message parsing doesn't handle double prefix
- ❓ Failed module highlighting should work but needs verification

**What user sees:**
- Error Type: RuntimeError
- Message: RuntimeError: This is a test error (should be: "This is a test error")
- Pipeline Error: RuntimeError: RuntimeError: This is a test error (should be: "RuntimeError: This is a test error")
