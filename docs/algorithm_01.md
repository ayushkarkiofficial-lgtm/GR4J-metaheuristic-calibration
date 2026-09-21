# RS-SPSO — Algorithm (design notes)

Respawning Speciation-based Particle Swarm Optimization (RS-SPSO). Design notes
describing how the swarm is speciated into sub-swarms, how each sub-swarm converges
toward a distinct minimum, and how converged sub-swarms respawn to hunt the minima
still missing.

## Symbols

- `N` = max no. of particles
- `m` = no. of solutions required (i.e. no. of sub-swarms)
- `n` = rounddown(N / m, 0) = no. of particles in each sub-swarm
- total no. of particles = `n * m`

## class Particle

Initialize particle: assign position, velocity, p_best position, p_best score,
`swarm_id = 0` (free particle).

- update velocity

## def pso_converge

Initialize swarm.

    sorted_swarm = sorted(swarm, key=attrgetter('pBestScore'))

Define `seeds` array of size `m`.
Define `subswarm` array of size `m`, each containing an array of size `n`.

    seeds.append(sorted_swarm[0])

    for i in (1 to len(sorted_swarm)):
        # assign top n particles with minimum distance r as seed for each sub-swarm
        if distance between i and every seed in seeds > r:
            seeds.append(i)
        if len(seeds) >= m:
            break

If not enough seeds outside `r`, assign randomly (open question).

    for i in range(seeds):
        subswarm[i][0] = seeds[i]

    remaining = sorted(swarms) - seeds
    gap = n - 1

    # create sub_swarm
    for i in range(remaining):
        append remaining[gap*i : gap*(i+1)] to sub_swarm[i]

## Swarm IDs

Assign `particle.swarm_id` (better than keeping a separate array). Same `swarm_id`
attract, different `swarm_id` repel. Particle-particle force is weak; particle-swarm
or swarm-swarm force is stronger — this prevents convergence of two sub-swarms toward
the same solution.

`s_id` array contains the id of all swarms, e.g. `[1, 2, 3, ..., m]`.

    for s in sub_swarm:
        assign swarm_id = s+1 for all items in s
        # id 0 = free particle; id 1,2,3 = belongs to sub_swarm[0], [1], [2]

        # calculate velocity
        cognitive_vel = c1 * r1 * (particle.pBestPosition - particle.position)
        social_vel    = c2 * r2 * (sBestPosition - particle.position)   # sBest = swarm best
        particle.velocity = w*particle.velocity + cognitive_vel + social_vel

        if nearest swarm -> repulsion force

        # update position
        particle.update_position(bounds)
        score = obj_func(particle.position)
        if particle.pBestScore > score:
            particle.pBestScore = score
            particle.pBestPosition = particle.position.copy()

## Convergence and DE refinement

If a sub-swarm converges with error < max_error: record the solution.

If a sub-swarm cannot converge to the required accuracy, it is converted into
Differential Evolution (or any optimizer with many particles that excels at
single-minimum refinement).

Once a sub-swarm has served its purpose:

- assign its particles `swarm_id = 0` (they may now join other sub-swarms)
- drop it from `s_id`
- divide the freed (`swarm_id = 0`) particles among the remaining sub-swarms in `s_id`

Each freed particle shares its `pBest2` with the sub-swarm it joins. If `sBest > pBest2`
the swarm moves toward `pBest2`.

Reason: if a particle found a local minimum different from the one its sub-swarm
converged into, it shares that info with the new sub-swarm it joins.

The same process repeats — `s_id` shrinks and the no. of particles per remaining
sub-swarm grows — until all required solutions are found.
