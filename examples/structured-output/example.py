from automo.runtime import ModelOutputBatch

outputs = ModelOutputBatch(
    (
        {"action": "accept", "size": 2},
        {"action": "skip", "size": 0},
    ),
    output_name="action",
)
print(outputs)
