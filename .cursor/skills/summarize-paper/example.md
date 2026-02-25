# Example: Implicit Position-Based Fluids (Physics-oriented)

Shortened reference showing **tone and style** per section. See [template.md](template.md) for the full output template.

---

**One-Sentence Summary:**

IPBF formulates SPH fluid simulation as an implicit position optimization with compliance-normalized energy, achieving unconditional stability and near-incompressibility at large time steps.

---

**Problem:**

- **Task:** Simulate incompressible fluids using SPH. *(Source: Abstract)*
- **Difficulty / bottleneck:** Water barely compresses, so the solver must enforce very stiff constraints — but stiff constraints fight numerical stability. *(Source: Section 1)*
- **Impl. environment:** CUDA on NVIDIA RTX 4090 GPU. *(Source: Section 4)*

---

**Why Prior Work Fails** -- separated section, not sub-bullets of problem:

- **Main limitation:** Existing SPH solvers cannot simultaneously achieve stability, incompressibility, and low cost. *(Source: Section 1)*
- **Root cause:** Explicit/semi-implicit integrators (WCSPH, IISPH, DFSPH) diverge under stiff constraints or low iterations; PBF is stable but first-order updates over-damp the motion. *(Source: Section 1, 2)*
- **What this paper changes:** Uses a second-order implicit descent on a compliance-normalized energy — stiffness can go to infinity without instability or damping. *(Source: Section 1)*

---

**Core Mechanism** -- physics-oriented, so include: State, Energy, Constraints, Solver, Time integration:

### High-Level Idea

Each particle wants two things: keep its momentum, and not crowd neighbors. IPBF frames this as a single optimization per time step. The $\alpha = 1/k$ trick lets you demand perfect incompressibility ($\alpha \to 0$) without floating-point blowup. *(Source: Section 3.1, 3.2)*

### Mechanism Details

- **State representation:** particle positions $\mathbf{x}$, velocities $\mathbf{v}$ *(Source: Section 3.1)*
- **Governing equations / Energy:** $\bar{\Psi}(\mathbf{x}) = \frac{\alpha}{2h^2}\|\mathbf{x}-\mathbf{y}\|_M^2 + \frac{1}{2}\sum_i C_i(\mathbf{x})^2$ *(Source: Section 3.2 Eq. 7)*
- **Constraints:** density constraint $C_i = \rho_i/\rho_0 - 1$, clamped at surface *(Source: Section 3.1 Eq. 6)*
- **Solver type:** relaxed Jacobi with per-particle Newton step (3x3 solve), approximate Hessian *(Source: Section 3.3, 3.5)*
- **Time integration:** implicit Euler (variational form) *(Source: Section 3.1)*

---

**How It Works** -- max 5 steps, algorithm block:

> 1. Compute inertial positions $\mathbf{y} = \mathbf{x}^t + h\mathbf{v}^t + h^2\mathbf{a}^*$ *(Source: Eq. 3)*
> 2. Initialize $\mathbf{x} \leftarrow \mathbf{y}$
> 3. **for** each iteration: update $\rho_i, \nabla C_i$; solve $\Delta\mathbf{x}_i = \mathbf{H}_i^{-1}\mathbf{f}_i$; apply $\mathbf{x}_i \mathrel{+}= \Delta\mathbf{x}_i/2$ *(Source: Algorithm 1)*
> 4. Compute velocities $\mathbf{v}^{t+1} = (\mathbf{x} - \mathbf{x}^t)/h$ *(Source: Section 3.6)*
> 5. Apply artificial damping via lower-stiffness reference (Eq. 17) *(Source: Section 3.6)*

---

**Results** -- rigorous:

- **Best metric:** Mean density error 9.2e-4 at 70 ms/frame (Double Dam Break). *(Source: Table 1)*
- **Improvement over baseline:** DFSPH 1.2e-3 at 111 ms; PBF 5.6e-3 at 250 ms — IPBF is ~1.6x faster at lower error. *(Source: Table 1)*
- **Benchmark / dataset:** Double Dam Break, Block Flop (250K), Balloon (1M particles). *(Source: Section 4)*
- **Main qualitative effect:** Unconditionally stable; recovers from 7x rest density without volume loss. *(Source: Fig. 5, 6)*

---

**Works / Fails:**

- **Works well when:** Large time steps, low iteration budgets, GPU parallel execution. *(Source: Section 4)*
- **Weak when:** $\alpha = 0$ removes convergence guarantee; energy injection artifacts may appear without damping. *(Source: Section 5 Conclusion)*

---

**Pseudocode or Algorithm** -- agent picks the better format. This paper is equation-heavy / numerical, so algorithm block fits better:

> **Input:** $\mathbf{x}^t, \mathbf{v}^t, \mathbf{a}^*, h, \alpha, M$
> **Output:** $\mathbf{x}^{t+1}, \mathbf{v}^{t+1}$
>
> 1. $\mathbf{y} \leftarrow \mathbf{x}^t + h\mathbf{v}^t + h^2\mathbf{a}^*$
> 2. $\mathbf{x} \leftarrow \mathbf{y}$
> 3. **for** $l = 0$ **to** $M-1$ **do**
>    1. Update $\rho_i, \nabla C_i$ from current $\mathbf{x}$
>    2. **for all** $i$: $\Delta\mathbf{x}_i \leftarrow \mathbf{H}_i^{-1}\mathbf{f}_i$; $\mathbf{x}_i \leftarrow \mathbf{x}_i + \Delta\mathbf{x}_i/2$
> 4. $\mathbf{v}^{t+1} \leftarrow (\mathbf{x} - \mathbf{x}^t)/h$
> 5. Apply artificial damping (Eq. 17)
