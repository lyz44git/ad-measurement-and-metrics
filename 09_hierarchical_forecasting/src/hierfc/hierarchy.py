"""US -> Census division -> state -> metro, with an explicit Remainder so every level sums to the US row.

Leaves are the member metros plus one Remainder leaf (US minus the members: non-metro areas and metros that are
not members). The Remainder is repeated as a pass-through node at the division and state levels. Node order follows
the usual convention: aggregate nodes first (US, divisions, states), then the leaves, so S = [C; I]."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

DIVISIONS = {
    "New England": "CT ME MA NH RI VT",
    "Middle Atlantic": "NJ NY PA",
    "East North Central": "IL IN MI OH WI",
    "West North Central": "IA KS MN MO NE ND SD",
    "South Atlantic": "DE DC FL GA MD NC SC VA WV",
    "East South Central": "AL KY MS TN",
    "West South Central": "AR LA OK TX",
    "Mountain": "AZ CO ID MT NV NM UT WY",
    "Pacific": "AK CA HI OR WA",
}
STATE_TO_DIV = {s: d for d, ss in DIVISIONS.items() for s in ss.split()}
REM = "Remainder"
LEVELS = ["US", "division", "state", "metro"]


@dataclass
class Hierarchy:
    nodes: list            # node ids, aggregates first then leaves
    level: np.ndarray      # level index 0..3 per node
    S: np.ndarray          # n x m summing matrix
    n_agg: int
    is_rem: np.ndarray     # True for the Remainder node at each level
    children: dict         # aggregate node index -> indices of its children one level down
    leaves: pd.DataFrame   # region, name, state (members) plus the Remainder row, in leaf order

    @property
    def n(self):
        return self.S.shape[0]

    @property
    def m(self):
        return self.S.shape[1]

    def aggregate(self, Y_leaves: np.ndarray) -> np.ndarray:
        """(m x ...) leaf values -> (n x ...) values for every node."""
        return np.tensordot(self.S, Y_leaves, axes=(1, 0))

    def leaf_values(self, Y_members: np.ndarray, us: np.ndarray) -> np.ndarray:
        """Append the Remainder leaf (US minus the members' sum) to the member rows."""
        rem = us - Y_members.sum(0)
        return np.vstack([Y_members, rem[None, :]])


def build(members: pd.DataFrame) -> Hierarchy:
    """members: region, name, state (any order). Unknown states raise."""
    bad = sorted(set(members.state) - set(STATE_TO_DIV))
    if bad:
        raise ValueError(f"states without a Census division: {bad}")
    mem = members.assign(division=members.state.map(STATE_TO_DIV)).sort_values(["division", "state", "name"])
    leaves = pd.concat([mem, pd.DataFrame([{"region": REM, "name": REM, "state": REM, "division": REM}])],
                       ignore_index=True)
    divs = sorted(mem.division.unique()) + [REM]
    states = sorted(mem.state.unique(), key=lambda s: (STATE_TO_DIV[s], s)) + [REM]
    m = len(leaves)
    rows, nodes, level = [], [], []
    rows.append(np.ones(m)); nodes.append("US"); level.append(0)
    for d in divs:
        rows.append(leaves.division.eq(d).to_numpy(float)); nodes.append(f"div:{d}"); level.append(1)
    for s in states:
        rows.append(leaves.state.eq(s).to_numpy(float)); nodes.append(f"state:{s}"); level.append(2)
    n_agg = len(rows)
    S = np.vstack([np.array(rows), np.eye(m)])
    nodes += [f"metro:{r}" for r in leaves.region]; level += [3] * m
    level = np.array(level)
    is_rem = np.array([nd.endswith(REM) for nd in nodes])
    # children: each aggregate node's nodes one level down whose leaves it contains
    children = {}
    for i in range(n_agg):
        lo = np.where(level == level[i] + 1)[0]
        children[i] = [j for j in lo if np.all(S[i] >= S[j]) and S[j].sum() > 0]
    return Hierarchy(nodes=nodes, level=level, S=S, n_agg=n_agg, is_rem=is_rem, children=children,
                     leaves=leaves.reset_index(drop=True))
