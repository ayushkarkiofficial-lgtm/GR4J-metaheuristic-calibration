"""RS-SPSO -- Respawning Speciation-based Particle Swarm Optimization.

The reusable optimizer library, extracted from rs_spso.ipynb so it can be imported
(`from rs_spso import rs_spso`) WITHOUT executing the notebook's demo/benchmark cells.
Python resolves this .py module before the import_ipynb notebook hook, so importing it
is silent. The notebook keeps the demos, animation, and benchmark comparisons.
"""

import numpy as np
import random
from operator import attrgetter
import time

import numpy as np
import random
from scipy.optimize import differential_evolution


def euclidean(a, b):
    return np.linalg.norm(a - b)


class Particle:
    def __init__(self, bounds, obj_func):
        self.position = np.array([random.uniform(lo, hi) for lo, hi in bounds])
        self.velocity = np.zeros(len(bounds))
        self.pBestPosition = self.position.copy()
        self.pBestScore = obj_func(self.position)
        self.swarm_id = 0                     # 0 = free particle; 1..m = sub_swarm[id-1]

    def update_velocity(self, sBestPosition, repulsion, c1, c2, w):
        dim = len(self.position)
        r1 = np.random.random(dim)            # resampled every step (per-dimension)
        r2 = np.random.random(dim)
        cognitive = c1 * r1 * (self.pBestPosition - self.position)
        social    = c2 * r2 * (sBestPosition - self.position)
        self.velocity = w * self.velocity + cognitive + social + repulsion

    def update_position(self, bounds):
        self.position = self.position + self.velocity
        for d, (lo, hi) in enumerate(bounds):
            if self.position[d] < lo:
                self.position[d] = lo
                self.velocity[d] = 0.0        # kill velocity into the wall
            elif self.position[d] > hi:
                self.position[d] = hi
                self.velocity[d] = 0.0

    def evaluate(self, obj_func):
        score = obj_func(self.position)
        if score < self.pBestScore:
            self.pBestPosition = self.position.copy()
            self.pBestScore = score
        return score


class SubSwarm:
    def __init__(self, seed, index):
        self.index = index
        self.members = [seed]
        seed.swarm_id = index + 1
        self.sBestPosition = seed.pBestPosition.copy()
        self.sBestScore = seed.pBestScore
        self.stall_counter = 0
        self.active = True

    def update_sBest(self):
        prev = self.sBestScore
        for p in self.members:
            if p.pBestScore < self.sBestScore:
                self.sBestScore = p.pBestScore
                self.sBestPosition = p.pBestPosition.copy()
        return prev - self.sBestScore        # improvement this step (>= 0)

    def radius(self):
        return max(euclidean(p.position, self.sBestPosition) for p in self.members)

    def respawn(self, bounds, obj_func, found, avoid, tries=30):
        """Relocate this species' own particles into unexplored space (> avoid from every
        found optimum) to hunt for a still-missing minimum. Keeps the species active.
        This is the RS ('respawn') part: converged species explore instead of freezing."""
        for p in self.members:
            cand = None
            for _ in range(tries):
                cand = np.array([random.uniform(lo, hi) for lo, hi in bounds])
                if all(euclidean(cand, fp) > avoid for fp in found):
                    break
            p.position = cand
            p.velocity = np.zeros(len(bounds))
            p.pBestPosition = cand.copy()
            p.pBestScore = obj_func(cand)
        best = min(self.members, key=lambda p: p.pBestScore)
        self.sBestPosition = best.pBestPosition.copy()
        self.sBestScore = best.pBestScore
        self.stall_counter = 0

    def free_members(self):
        for p in self.members:
            p.swarm_id = 0
        self.members = []
        self.active = False

def repulsion_force(p, all_particles, k_swarm, k_particle, v_repel_max, eps=1e-12):
    """Push p away from the nearest particle of a different swarm. Bounded by v_repel_max."""
    nearest, nd = None, np.inf
    for q in all_particles:
        if q is p or q.swarm_id == p.swarm_id:
            continue
        d = euclidean(p.position, q.position)
        if d < nd:
            nd, nearest = d, q
    if nearest is None:
        return np.zeros(len(p.position))
    direction = (p.position - nearest.position) / (nd + eps)
    strength = k_swarm if nearest.swarm_id != 0 else k_particle   # swarm-swarm >> particle
    force = strength * direction / (nd ** 2 + eps)
    return np.clip(force, -v_repel_max, v_repel_max)               # cap is essential


def select_seeds(sorted_swarm, m, r):
    """Best-first seeds, each > r from all others. Farthest-point fallback if < m found."""
    seeds = [sorted_swarm[0]]
    for p in sorted_swarm[1:]:
        if all(euclidean(p.position, s.position) > r for s in seeds):
            seeds.append(p)
        if len(seeds) == m:
            break
    if len(seeds) < m:
        remaining = [p for p in sorted_swarm if p not in seeds]
        while len(seeds) < m and remaining:
            # most-isolated leftover: max over p of its distance to the nearest seed
            best_p = max(remaining,
                         key=lambda p: min(euclidean(p.position, s.position) for s in seeds))
            seeds.append(best_p)
            remaining.remove(best_p)
    return seeds


def build_subswarms(sorted_swarm, seeds, n):
    """Assign each non-seed to its nearest seed that still has capacity ('look farther')."""
    subswarms = [SubSwarm(s, i) for i, s in enumerate(seeds)]
    seed_ids = {id(s) for s in seeds}
    remaining = [p for p in sorted_swarm if id(p) not in seed_ids]
    for p in remaining:
        order = sorted(range(len(seeds)),
                       key=lambda i: euclidean(p.position, seeds[i].position))
        for i in order:
            if len(subswarms[i].members) < n:
                subswarms[i].members.append(p)
                p.swarm_id = i + 1
                break
        # if every swarm is full, p stays swarm_id = 0 (free reserve pool)
    return subswarms


def default_refiner(obj_func, x0, bounds, pad_frac=0.05):
    """Refine a stalled swarm with Differential Evolution, restricted to a LOCAL box
    around x0. Keeping DE basin-local stops every stalled swarm collapsing onto the
    single global optimum. pad_frac sets the half-width as a fraction of each range."""
    x0 = np.asarray(x0)
    local_bounds = []
    for d, (lo, hi) in enumerate(bounds):
        pad = pad_frac * (hi - lo)
        local_bounds.append((max(lo, x0[d] - pad), min(hi, x0[d] + pad)))
    res = differential_evolution(obj_func, local_bounds, x0=x0, polish=True, tol=1e-6)
    return res.x, res.fun

def rs_spso(obj_func, bounds, m,
            N=40, r=None, c1=1.5, c2=1.5, w=0.7,
            max_iteration=200, pos_tol=1e-4, f_tol=1e-8, patience=15,
            k_swarm=1.0, k_particle=0.1, v_repel_max=None, sep=None,
            refiner=default_refiner, verbose=True):
    """RS-SPSO -- Respawning Speciation-based PSO.

    Finds up to m distinct minima of obj_func, returned as (position, score).
    Speciated sub-swarms search in parallel, repel each other, and a stalled species
    is polished by DE. When a species converges (or is DE-refined) its optimum is
    recorded if new, then the species RESPAWNS into unexplored space to hunt for the
    minima still missing -- so converged particles keep working instead of freezing."""
    assert m <= N, "need at least as many particles as solutions"
    lo = np.array([b[0] for b in bounds]); hi = np.array([b[1] for b in bounds])
    diag = euclidean(lo, hi)
    if r is None:
        r = 0.1 * diag                       # seed spacing ~ 10% of domain diagonal
    if v_repel_max is None:
        v_repel_max = 0.1 * diag
    if sep is None:
        sep = 0.02 * diag                    # two optima counted "the same" if closer than sep
    avoid = r * 0.5                          # respawn keeps new explorers this far from found optima
    n = max(2, N // m)                        # particles per species (1 seed + rest)

    swarm = [Particle(bounds, obj_func) for _ in range(N)]
    sorted_swarm = sorted(swarm, key=lambda p: p.pBestScore)
    seeds = select_seeds(sorted_swarm, m, r)
    subswarms = build_subswarms(sorted_swarm, seeds, n)

    t0 = time.time()
    solutions = []
    for iteration in range(max_iteration):
        active = [S for S in subswarms if S.active]
        if not active or len(solutions) >= m:
            break

        # --- move every active species ---
        for S in active:
            for p in S.members:
                rep = repulsion_force(p, swarm, k_swarm, k_particle, v_repel_max)
                p.update_velocity(S.sBestPosition, rep, c1, c2, w)
                p.update_position(bounds)
                p.evaluate(obj_func)
            improvement = S.update_sBest()
            S.stall_counter = S.stall_counter + 1 if improvement < f_tol else 0

        # --- converged / stalled -> record if new, then respawn to explore (or retire) ---
        for S in active:
            converged = S.radius() < pos_tol
            stalled = S.stall_counter >= patience
            if not (converged or stalled):
                continue
            if stalled and not converged:
                t_de = time.time()
                x, fx = refiner(obj_func, S.sBestPosition, bounds)
                cand, cscore = np.asarray(x), float(fx)
                if verbose:
                    print(f"[iter {iteration:3d}] species {S.index} stalled -> DE refine  "
                          f"f={cscore:.3e}  ({time.time() - t_de:.2f}s)")
            else:
                cand, cscore = S.sBestPosition.copy(), S.sBestScore

            is_new = all(euclidean(cand, sp) > sep for sp, _ in solutions)
            if is_new:
                solutions.append((cand, cscore))
                if verbose:
                    print(f"[iter {iteration:3d}] species {S.index} -> NEW optimum "
                          f"({len(solutions)}/{m})  f={cscore:.3e}")
            elif verbose:
                print(f"[iter {iteration:3d}] species {S.index} hit a known optimum -> respawn")

            if len(solutions) >= m:
                S.free_members()                                    # all found -> retire
            else:
                S.respawn(bounds, obj_func, [sp for sp, _ in solutions], avoid)

    if verbose:
        print(f"RS-SPSO: {len(solutions)}/{m} solutions in {time.time() - t0:.2f}s")
    return solutions                          # already distinct by construction
