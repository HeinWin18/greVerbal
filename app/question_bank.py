"""Validation helpers for the GRE verbal question-bank schema."""

QUESTION_TYPES = {
    "text_completion",
    "sentence_equivalence",
    "reading_comprehension",
}


def is_valid_question(question):
    """Return whether a question has enough valid data to safely practice it.

    Source metadata is optional for legacy records. When present, it is kept
    verbatim and surfaced by the UI as attribution.
    """
    if not isinstance(question, dict):
        return False
    if not isinstance(question.get("question_id"), str) or not question["question_id"].strip():
        return False
    if question.get("type") not in QUESTION_TYPES:
        return False
    if not isinstance(question.get("prompt"), str) or not question["prompt"].strip():
        return False
    if "explanation" in question and (
        not isinstance(question["explanation"], str) or not question["explanation"].strip()
    ):
        return False

    choices = question.get("choices")
    if (
        not isinstance(choices, list)
        or len(choices) < 2
        or any(not isinstance(choice, str) or not choice.strip() for choice in choices)
        or len(set(choices)) != len(choices)
    ):
        return False

    answer = question.get("correct_answer")
    if question["type"] == "sentence_equivalence":
        if (
            not isinstance(answer, list)
            or len(answer) != 2
            or any(not isinstance(item, str) or item not in choices for item in answer)
            or len(set(answer)) != 2
        ):
            return False
    elif not isinstance(answer, str) or answer not in choices:
        return False

    if question["type"] == "reading_comprehension":
        passage = question.get("passage")
        if not isinstance(passage, str) or not passage.strip():
            return False
    elif "passage" in question and (
        not isinstance(question["passage"], str) or not question["passage"].strip()
    ):
        return False

    source = question.get("source")
    if source is not None:
        if not isinstance(source, dict):
            return False
        if source.get("kind") not in {"original", "licensed"}:
            return False
        if not isinstance(source.get("title"), str) or not source["title"].strip():
            return False
        if "section" in source and not isinstance(source["section"], str):
            return False
        if source.get("url") is not None and not isinstance(source["url"], str):
            return False
    return True


def unique_valid_questions(documents):
    """Keep the first valid record for each question ID; skip malformed data."""
    questions = []
    seen_ids = set()
    for document in documents:
        if not is_valid_question(document):
            continue
        question_id = document["question_id"]
        if question_id in seen_ids:
            continue
        seen_ids.add(question_id)
        questions.append(document)
    return questions
