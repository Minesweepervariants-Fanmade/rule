from minesweepervariants.abs.Rrule import AbstractClueRule

class RuleBT(AbstractClueRule):
    id = "BT"
    name = "Board-Shared"
    name.zh_CN = "副板共用"
    doc = "Auxiliary boards from different auxiliary board rules share the same board"
    doc.zh_CN = "不同副板规则的副板共用"
    tags = ["Original", "Aux Board", "Meta"]
