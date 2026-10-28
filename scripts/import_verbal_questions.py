
import json
from pathlib import Path

source = Path("data/gre_verbal_original_import.json")
destination = Path("data/gre_verbal_app_format.json")

records = json.loads(source.read_text(encoding="utf-8"))
converted = []

for record in records:
    item = record.copy()
    choices = item["choices"]
    answers = item["correct_answer"]

    if isinstance(choices, dict):
        labels = list(choices.keys())
        item["choices"] = list(choices.values())

        if isinstance(answers, list):
            item["correct_answer"] = [choices[a] for a in answers]
        else:
            item["correct_answer"] = choices[answers]

    elif isinstance(choices, list):
        item["choices"] = choices
        # If answers are labels, map them to the choice text.
        if isinstance(answers, list):
            item["correct_answer"] = answers
        else:
            item["correct_answer"] = answers

    converted.append(item)

destination.write_text(
    json.dumps(converted, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(f"Converted {len(converted)} questions to {destination}")
