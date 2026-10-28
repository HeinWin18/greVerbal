"""Seed a small original GRE verbal dataset into empty collections."""

from app import create_app
from app.database import DatabaseError, get_database, test_connection
from app.question_bank import is_valid_question
from pymongo.errors import PyMongoError


VOCABULARY = [
    {"word": "abate", "definition": "to become less intense or widespread", "example": "After several hours, the storm began to abate.", "difficulty": "Intermediate"},
    {"word": "ameliorate", "definition": "to make a difficult situation better", "example": "The new policy was designed to ameliorate housing shortages.", "difficulty": "Advanced"},
    {"word": "assiduous", "definition": "showing persistent care and effort", "example": "Her assiduous review of the evidence improved the report.", "difficulty": "Advanced"},
    {"word": "conundrum", "definition": "a confusing or difficult problem", "example": "The committee faced a conundrum with no easy solution.", "difficulty": "Intermediate"},
    {"word": "ephemeral", "definition": "lasting for a very short time", "example": "The popularity of the trend proved ephemeral.", "difficulty": "Advanced"},
    {"word": "equivocal", "definition": "open to more than one interpretation; ambiguous", "example": "The witness gave an equivocal response to the question.", "difficulty": "Advanced"},
    {"word": "laconic", "definition": "using very few words", "example": "His laconic reply ended the discussion.", "difficulty": "Advanced"},
    {"word": "mitigate", "definition": "to make something less severe or harmful", "example": "Planting trees can help mitigate urban heat.", "difficulty": "Intermediate"},
    {"word": "pragmatic", "definition": "focused on practical results", "example": "They chose a pragmatic solution that fit the budget.", "difficulty": "Intermediate"},
    {"word": "repudiate", "definition": "to reject or deny the truth of something", "example": "The researcher used new data to repudiate the earlier claim.", "difficulty": "Advanced"},
]

VERBAL_QUESTIONS = [
    {
        "question_id": "text-completion-01",
        "type": "text_completion",
        "prompt": "Although the critic was known for severe reviews, her response to the debut novel was unexpectedly ____; she praised its careful pacing and original voice.",
        "choices": ["caustic", "laudatory", "equivocal", "perfunctory", "irrelevant"],
        "correct_answer": "laudatory",
        "explanation": "The contrast with severe reviews and the praise that follows indicate an approving response. ‘Laudatory’ means expressing praise.",
    },
    {
        "question_id": "text-completion-02",
        "type": "text_completion",
        "prompt": "Because the committee had only one afternoon to review the proposal, its discussion was necessarily ____ rather than exhaustive.",
        "choices": ["cursory", "dogmatic", "protracted", "scrupulous", "tangential"],
        "correct_answer": "cursory",
        "explanation": "A short time limit prevents an exhaustive review. ‘Cursory’ means quick and not thorough.",
    },
    {
        "question_id": "sentence_equivalence-01",
        "type": "sentence_equivalence",
        "prompt": "The historian’s account is unusually ____: it distinguishes confirmed facts from later legends.",
        "choices": ["fastidious", "judicious", "impartial", "ornate", "speculative", "vague"],
        "correct_answer": ["judicious", "impartial"],
        "explanation": "Both ‘judicious’ and ‘impartial’ fit an account that carefully separates evidence from legend and produce similar meanings in the sentence.",
    },
    {
        "question_id": "reading-comprehension-01",
        "type": "reading_comprehension",
        "passage": "A city expanded its network of small parks. Researchers later found that nearby blocks were cooler on summer afternoons, though the effect was strongest where tree cover was dense.",
        "prompt": "Which conclusion is best supported by the passage?",
        "choices": ["Every neighborhood became cooler by the same amount.", "Small parks may reduce local heat, especially when they include many trees.", "Tree cover had no measurable relationship to temperature.", "The parks were built primarily to increase property values."],
        "correct_answer": "Small parks may reduce local heat, especially when they include many trees.",
        "explanation": "The researchers observed cooler nearby blocks and a stronger effect where tree cover was dense. The other choices add claims the passage does not support.",
    },
    {
        "question_id": "reading-comprehension-02",
        "type": "reading_comprehension",
        "passage": "Some early maps appear inaccurate by modern standards. Yet their makers often prioritized routes, landmarks, and boundaries that mattered to travelers and local communities rather than uniform measurement.",
        "prompt": "The passage suggests that early maps should be evaluated primarily by considering their:",
        "choices": ["usefulness for the purposes of their makers", "agreement with modern satellite images", "lack of decorative features", "ability to show every location at one scale"],
        "correct_answer": "usefulness for the purposes of their makers",
        "explanation": "The passage emphasizes what mapmakers chose to represent for travelers and communities, rather than modern precision or uniform scale.",
    },
]

# These questions were written for this application. The section names describe
# the question format and are not citations to an external book or website.
for question in VERBAL_QUESTIONS:
    question["source"] = {
        "kind": "original",
        "title": "GRE Verbal Prep original practice",
        "section": question["type"].replace("_", " ").title(),
        "url": None,
    }


def seed_collection(collection, documents, key_field, label):
    for document in documents:
        collection.update_one(
            {key_field: document[key_field]},
            {"$set": document},
            upsert=True,
        )
    print(f"Seeded {len(documents)} {label} records without duplicating keys.")


def seed_verbal_questions(collection, documents):
    """Upsert valid, uniquely identified questions and skip bad imports."""
    seen_ids = set()
    seeded = 0
    skipped = 0
    for document in documents:
        if not is_valid_question(document):
            skipped += 1
            continue
        question_id = document["question_id"]
        if question_id in seen_ids:
            skipped += 1
            continue
        seen_ids.add(question_id)
        collection.update_one(
            {"question_id": question_id},
            {"$set": document},
            upsert=True,
        )
        seeded += 1
    print(f"Seeded {seeded} verbal questions; skipped {skipped} invalid or duplicate records.")


def main():
    app = create_app()
    with app.app_context():
        try:
            test_connection()
            database = get_database()
            seed_collection(database["vocabulary"], VOCABULARY, "word", "vocabulary")
            seed_verbal_questions(
                database["verbal_questions"],
                VERBAL_QUESTIONS,
            )
        except DatabaseError as exc:
            raise SystemExit(f"Seed failed: {exc}") from exc
        except PyMongoError as exc:
            raise SystemExit(
                "Seed failed while writing to MongoDB. Check Atlas access and try again."
            ) from exc


if __name__ == "__main__":
    main()
