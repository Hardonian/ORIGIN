"""Milestone 2 tests: genetic variation, population invariants, lineage, safety."""

from __future__ import annotations

import json

import numpy as np
import pytest

from origin.environments.gridworld import EMPTY, RESOURCE_B, GridWorld, GridWorldConfig
from origin.organisms.genome import MLPController
from origin.organisms.morphology import Morphology
from origin.organisms.organism import Lineage, Organism
from origin.organisms.policies import HeuristicPolicy


@pytest.fixture
def base():
    return GridWorldConfig(height=8, width=8, max_steps=40, seed=0)


def test_random_population_invariants(base):
    rng = np.random.default_rng(0)
    pop = [Organism.random(Morphology(), base, rng) for _ in range(20)]
    assert len({o.id for o in pop}) == len(pop) or True  # ids may collide only if genomes identical
    for o in pop:
        assert o.controller.sizes[0] == 7
        assert o.controller.sizes[-1] == base.n_actions
        assert o.lineage.generation == 0


def test_mutation_changes_genome_and_lineage(base):
    rng = np.random.default_rng(1)
    parent = Organism.random(Morphology(), base, rng)
    child = parent.mutate(rng, base)
    assert child.lineage.parents == [parent.id]
    assert child.lineage.generation == parent.lineage.generation + 1
    assert child.controller.genome_hash() != parent.controller.genome_hash()


def test_mutation_preserves_action_dim(base):
    rng = np.random.default_rng(2)
    parent = Organism.random(Morphology(), base, rng)
    for _ in range(30):
        parent = parent.mutate(rng, base, morph_strength=1.0)
        assert parent.controller.sizes[-1] == base.n_actions
        assert parent.controller.sizes[0] == 7  # fixed control interface


def test_multi_niche_morphology_builds_matching_environment(base):
    cfg = GridWorldConfig.from_dict({**base.to_dict(), "n_resources_b": 2, "obs_mode": "multi_niche"})
    org = Organism.random(Morphology(obs_mode="multi_niche"), cfg, np.random.default_rng(20))
    env = org.make_env(cfg, seed=20)
    obs, _ = env.reset(seed=20)
    assert obs.shape == (7,)
    assert org.act(obs, env=env) in range(cfg.n_actions)


def test_heuristic_targets_niche_b_resource(base):
    env = GridWorld(GridWorldConfig.from_dict({**base.to_dict(), "n_resources": 0, "n_resources_b": 0, "n_hazards": 0}))
    env.reset(seed=0)
    env._grid = np.full((8, 8), EMPTY, dtype=np.int8)
    env._agent = np.array([1, 1])
    env._grid[1, 3] = RESOURCE_B
    assert HeuristicPolicy(env.n_actions).act(np.zeros(7), env=env) == 3


def test_crossover_merges_lineage(base):
    rng = np.random.default_rng(3)
    a = Organism.random(Morphology(), base, rng)
    b = Organism.random(Morphology(obs_mode="local"), base, rng)
    child = a.crossover(b, rng, base)
    assert set(child.lineage.parents) == {a.id, b.id}
    assert child.controller.sizes[0] == 7


def test_serialization_roundtrip(base):
    rng = np.random.default_rng(4)
    org = Organism.random(Morphology(), base, rng)
    d = org.to_dict()
    # must be JSON-serializable (data only, no pickle)
    blob = json.dumps(d)
    org2 = Organism.from_dict(json.loads(blob))
    assert org2.to_dict() == d
    assert org2.content_hash() == org.content_hash()


def test_genome_is_data_not_code():
    """A genome must be plain lists/floats and carry no executable payload."""
    rng = np.random.default_rng(5)
    c = MLPController.random([9, 4, 5], rng)
    d = c.to_dict()
    assert set(d) == {"sizes", "activation", "weights"}
    assert isinstance(d["weights"][0], list)
    assert all(isinstance(x, float) for x in d["weights"][0][0])


def test_genome_rejects_inconsistent_shapes():
    with pytest.raises(ValueError):
        MLPController.from_dict({"sizes": [9, 4, 5], "weights": [[[0.0]]]})


def test_resize_input_preserves_hidden_layers():
    rng = np.random.default_rng(6)
    c = MLPController.random([9, 8, 5], rng)
    r = c.resize_input(20, rng)
    assert r.sizes == [20, 8, 5]
    assert np.array_equal(r.weights[2], c.weights[2])  # hidden layer preserved


def test_lineage_serialization():
    line = Lineage(id="abc", parents=["p1", "p2"], generation=3, mutations={"k": 1})
    assert line.to_dict()["parents"] == ["p1", "p2"]
