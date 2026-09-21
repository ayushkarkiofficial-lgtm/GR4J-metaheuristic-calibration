# RS-SPSO — Pseudocode (v2)

## parameters
- N  = max no. of particles
- m  = no. of solutions required (= no. of species)
- n  = floor(N / m)          # particles per species (1 seed + n-1 members)
- r  = species radius        # SEED SPACING only, NOT member assignment
- sep                        # two optima counted "the same" if closer than sep (<< r)
- c1, c2, w                  # cognitive, social, inertia weights
- pos_tol / patience         # convergence radius / stall patience before DE refine

## the two roles of r (key idea)
- r selects seeds: two seeds must be > r apart so each seeds a distinct basin.
- r does NOT gate member assignment: every particle goes to its NEAREST seed
  that still has capacity. "No seed within r" never strands a particle -> nearest wins.

---

## class Particle
    position, velocity
    pBestPosition, pBestScore
    swarm_id = 0                  # 0 = free; 1..m = member of species[id-1]

    update_velocity(sBestPosition):
        r1, r2 = random_vector(dim), random_vector(dim)   # RESAMPLE every step
        cognitive = c1 * r1 * (pBestPosition - position)
        social    = c2 * r2 * (sBestPosition - position)
        repulsion = repulsion_force(self)                 # bounded, see below
        velocity  = w*velocity + cognitive + social + repulsion

    update_position(bounds):
        position += velocity ; clip position to bounds

---

## seed selection  (best-first sort, distance > r)
    sorted_swarm = sort(swarm, key=pBestScore, ascending=True)   # best (lowest) first
    seeds = [ sorted_swarm[0] ]
    for p in sorted_swarm[1:]:
        if distance(p, every s in seeds) > r:     # far from ALL seeds -> new basin
            seeds.append(p)
        if len(seeds) == m: break
    # if < m seeds outside r: greedily add the most-isolated leftover (farthest-point)

## member assignment  (nearest seed with capacity)
    for i, s in enumerate(seeds): species[i] = [s]; s.swarm_id = i+1
    for p in (sorted_swarm - seeds):
        for s in seeds ordered by distance(p, s) ascending:
            if len(species[s.index]) < n: species[s.index].append(p); break

---

## repulsion_force(p)   # the isolation part -- MUST be capped
    q = nearest particle with q.swarm_id != p.swarm_id
    d = distance(p, q)
    strength = k_swarm if q.swarm_id != 0 else k_particle    # swarm-swarm >> particle
    return clip( strength * (p.position - q.position)/(d^2 + eps), -v_repel_max, +v_repel_max )

---

## main loop  (RESPAWN, not recycle)
    initialize N particles ; build seeds + species (above)
    solutions = []
    while solutions < m and iteration < max_iteration:
        for each active species S:
            sBest = best pBest in S
            for p in S:
                p.update_velocity(sBest) ; p.update_position(bounds) ; p.evaluate()
            update S.sBest ; bump S.stall_counter if no improvement

        for each active species S:
            if radius(S) < pos_tol:  cand = S.sBest
            elif S.stall_counter >= patience:  cand = differential_evolution(S, local box)
            else:  continue
            if cand is farther than sep from every recorded solution:
                record cand as a NEW solution
            if solutions == m:
                retire S
            else:
                # RESPAWN: relocate S's OWN particles to random positions > r/2 from every
                # found optimum, reset their pBest/velocity, keep S active. Converged
                # species become explorers hunting the minima still missing -- they do NOT
                # rejoin neighbours (that only reinforced already-found optima and collapsed
                # diversity), and they never freeze as free reserve.
                S.respawn(bounds, found_optima)

    return solutions          # distinct by construction (sep check)
