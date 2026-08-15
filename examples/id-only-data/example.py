from automo.refresh import HashSplit
from automo.runtime import DataSnapshot

snapshot = DataSnapshot(
    "ids",
    tuple({"id": f"item-{i}", "x": i} for i in range(20)),
    content_hash="demo",
)
partitions = HashSplit("id", seed=42).split(snapshot)
print(
    len(partitions.fit.row_indices),
    len(partitions.validation.row_indices),
    len(partitions.test.row_indices),
)
