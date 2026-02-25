# {Paper Title}

## 0. One-Sentence Summary

{What it does + key trick + outcome, in 1 sentence.}

---

## 1. Problem

- **Task:** ... *(Source: ...)*
- **Setting:** ... *(Source: ...)*
- **Difficulty / bottleneck:** ... *(Source: ...)*
- **Objective:** ... (keep LaTeX if any) *(Source: ...)*
- **Impl. environment:** ... *(Source: ...)*

---

## 2. Why Prior Work Fails

- **Main limitation:** ... *(Source: ...)*
- **Root cause:** ... *(Source: ...)*
- **What this paper changes:** ... *(Source: ...)*

---

## 3. Core Mechanism

### High-Level Idea

{Intuitive explanation — make the reader think "ah, I get it" before any equations.} *(Source: ...)*

### Mechanism Details

Include ONLY the relevant blocks from Phase 1 classification:

**Learning-oriented blocks:**
- **Model / Representation:** ... *(Source: ...)*
- **Objective / Loss:** ... (key equations allowed; use $...$) *(Source: ...)*
- **Optimization / Training:** ... *(Source: ...)*
- **Inference / Simulation:** ... *(Source: ...)*
- **Data:** ... *(Source: ...)*

**Physics-oriented blocks:**
- **State representation:** ... *(Source: ...)*
- **Governing equations / Energy:** ... *(Source: ...)*
- **Constraints:** ... *(Source: ...)*
- **Solver type:** ... *(Source: ...)*
- **Time integration:** ... *(Source: ...)*

**Hybrid:** include relevant blocks from both groups, plus:
- **Coupling:** ... (how physics and learning modules interact) *(Source: ...)*

---

## 4. How It Works (5 steps max)

> 1. ... *(Source: ...)*
> 2. ... *(Source: ...)*
> 3. ... *(Source: ...)*
> 4. ... *(Source: ...)*
> 5. ... *(Source: ...)*

---

## 5. Results

- **Best metric:** ... *(Source: ...)*
- **Improvement over baseline:** ... *(Source: ...)*
- **Benchmark / dataset:** ... *(Source: ...)*
- **Main qualitative effect:** ... *(Source: ...)*

---

## 6. Works / Fails

- **Works well when:** ... *(Source: ...)*
- **Weak when:** ... *(Source: ...)*

---

## 7. Pseudocode or Algorithm

Choose whichever communicates the method more clearly:

- **Python pseudocode** -- better when the method is procedural, involves data processing pipelines, or has a training loop.
- **Algorithm block** (math-style, using `>` blockquote) -- better when the method is equation-heavy, uses formal math notation, or is a classical numerical procedure.

Pick one. Do not include both.

### Option A: Python pseudocode

```python
def core_algorithm(inputs, params):
    """
    Inputs: ...
    Outputs: ...
    """
    state = initialize(inputs, params)
    for t in range(params.max_iter):
        state = update(state, inputs, params)
    return finalize(state)
```

### Option B: Algorithm block

> **Input:** ...
> **Output:** ...
>
> 1. ...
> 2. **for** ... **do**
>    1. ...
> 3. **return** ...
