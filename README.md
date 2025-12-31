# Marginalia

Marginalia is a static analysis tool for extracting structured metadata
from Python source code using `# meta:` comments.

See `specs/` for the formal specification.


## Marginalia `# meta:` Comments

Marginalia is a **comment-based metadata system for Python source code**.  
It lets you describe the *logical structure* of a codebase—modules, roles, call paths, and conceptual groupings—**without affecting runtime behavior**.

This README explains how to write and use `# meta:` lines so they can be parsed by Marginalia-compatible tools.

---

## Why `# meta:` Lines Exist

Python code often has *implicit structure* that isn’t captured by files, imports, or classes alone:

- Logical modules that cut across files
- Conceptual threads like “startup” or “UI loop”
- Global or shared data roles
- Informal architectural boundaries

`# meta:` lines make this structure **explicit, machine-readable, and human-friendly**, while remaining inert comments as far as Python itself is concerned.

---

## Core Principles

- **Pure comments** — no runtime effect
- **Static analysis only** — tools read source files, never execute them
- **Descriptive, not prescriptive** — metadata informs humans and tooling, but never enforces behavior
- **Local binding** — metadata applies only to the next symbol (or a named anchor)

---

## Basic Syntax

A meta comment starts with:

```python
# meta:
```

It is followed by **key=value** entries separated by whitespace:

```python
# meta: modules=db threads=main callers=3
```

### Grammar Overview

| Element | Description |
|------|------------|
| Comment prefix | `# meta:` |
| Entry format | `key=value_list` |
| Entry separator | Whitespace |
| Value separator | `,` |
| Case sensitivity | Case-sensitive |
| Ordering | Insignificant |

Whitespace around separators is ignored.

---

## Binding Rules

### Default Binding

A `# meta:` line applies to the **immediately following bindable symbol**.

Bindable symbols include:

- Functions
- Classes
- Data assignments
- Explicit anchors

Example:

```python
# meta: modules=io threads=startup
def load_config():
    ...
```

The metadata binds to `load_config`.

---

### Anchor Binding

Anchors allow metadata to bind to *logical names* rather than Python symbols.

Anchors are written using `@name` inside the meta line.

```python
# meta: @X modules=coordinates threads=main flags=g
```

Anchors **must be explicit**. There is no implicit anchor creation.

Anchors are especially useful for:

- Dictionary keys
- Global registries
- Conceptual entities that are not standalone Python symbols

#### Example: Binding to Dictionary Entries

```python
g = {
    # meta: @X modules=coordinates threads=main flags=g
    "X": 0,

    # meta: @Y modules=coordinates threads=main flags=g
    "Y": 0,
}
```

This produces two metadata bindings, one for `@X` and one for `@Y`.

---

## Supported Keys

Marginalia recognizes a small set of **well-known keys**, but allows arbitrary extension.

### `modules`

```text
modules = set<string>
```

Logical modules or functional groupings.

- Descriptive only
- Do **not** imply physical Python modules or packages

Example:

```python
# meta: modules=db,cache
```

---

### `threads`

```text
threads = set<string>
```

Conceptual execution contexts or call paths.

- Not OS threads
- Not concurrency primitives
- Narrative or architectural threads

Examples:

```python
# meta: threads=main,startup
# meta: threads=ui-loop
```

---

### `callers`

```text
callers = "*" | array<string> | integer
```

Approximate information about call sites.

| Form | Meaning |
|----|--------|
| `*` | Unbounded or general-purpose usage |
| Integer | Expected number of distinct call sites |
| Array | Explicit list of calling symbols |

Examples:

```python
# meta: callers=*
# meta: callers=2
# meta: callers=cli.main,api.handle_request
```

This field is **informational only**.

---

### `flags`

```text
flags = set<character>
```

Single-character user-defined markers.

- Opaque to Marginalia
- Meaning is defined entirely by you or your tools

Examples:

```python
# meta: flags=D
# meta: flags=#,X
```

Common uses include:
- Global variables
- Deprecated elements
- Experimental features
- “Do not remove” markers

---

## Multiple Entries and Conflicts

- Multiple entries per line are allowed
- Duplicate keys are allowed
- **Last value wins** if a key is repeated

```python
# meta: modules=db modules=storage
```

Result:

```
modules = {"storage"}
```

---

## Extensibility

You may define **any additional keys** you like.

Rules:
- Unknown keys must be ignored by tools
- Reserved keys are:
  - `modules`
  - `threads`
  - `callers`
  - `flags`

Example custom usage:

```python
# meta: stability=experimental owner=lion
```

This metadata is preserved but not interpreted by Marginalia itself.

---

## Parsing Guarantees

- Ordering is insignificant
- Unknown keys are preserved
- Whitespace is ignored around separators
- Tools must be forward-compatible

Marginalia is intentionally permissive.

---

## Non-Goals

Marginalia explicitly does **not** aim to provide:

- Runtime behavior changes
- Static type checking
- Dependency enforcement
- Call graph validation
- Architectural policing

It is a **descriptive annotation system**, not a rule engine.

---

## Recommended Normalized Output

Tools consuming Marginalia metadata are encouraged to normalize extracted data into records like:

```json
{
  "symbol_name": "load_config",
  "symbol_type": "function",
  "source_file": "config.py",
  "line_number": 42,
  "meta": {
    "modules": ["io"],
    "threads": ["startup"],
    "callers": 1
  }
}
```

The exact output format is tool-defined.

---

## Philosophy

Marginalia exists to support:

- Architectural literacy
- Human-centered code comprehension
- Long-lived systems with evolving structure
- Gentle tooling that *reads* code rather than *controls* it

Think of `# meta:` lines as **margin notes for programs**—annotations for future readers, including yourself.

---

## License and Use

Use freely.  
Ignore freely.  
Extend freely.

