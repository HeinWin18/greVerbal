import unittest
from unittest.mock import Mock, patch

from app import create_app
from app.database import DatabaseConnectionError
from app.question_bank import is_valid_question
from app.routes import answer_is_correct
from scripts.seed_data import (
    VERBAL_QUESTIONS,
    VOCABULARY,
    seed_collection,
    seed_verbal_questions,
)


class FakeCursor(list):
    def sort(self, key, direction):
        return FakeCursor(sorted(self, key=lambda item: item.get(key, ""), reverse=direction < 0))


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, query, projection):
        return FakeCursor(self.documents)

    def find_one(self, query, projection):
        return next(
            (item for item in self.documents if item.get("question_id") == query.get("question_id")),
            None,
        )


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.database = {
            "vocabulary": FakeCollection([{
                "word": "abate",
                "definition": "to become less intense",
                "example": "The storm began to abate.",
                "difficulty": "Intermediate",
            }]),
            "verbal_questions": FakeCollection([{
                "question_id": "sample-01",
                "type": "text_completion",
                "prompt": "The critic's review was unexpectedly ____.",
                "choices": ["caustic", "laudatory"],
                "correct_answer": "laudatory",
                "explanation": "The context indicates praise.",
            }]),
        }

    def test_homepage_has_functional_study_buttons(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Make the most of your study time", response.data)
        self.assertIn(b"Start My Study Session", response.data)
        self.assertIn(b'href="/session"', response.data)
        self.assertNotIn(b"Study Vocabulary", response.data)
        self.assertNotIn(b"Practice Verbal Questions", response.data)

    @patch("app.routes.get_database")
    def test_vocabulary_page_displays_database_fields(self, get_database):
        get_database.return_value = self.database

        response = self.client.get("/vocabulary")

        self.assertEqual(response.status_code, 200)
        for value in (b"abate", b"to become less intense", b"The storm began", b"Intermediate"):
            self.assertIn(value, response.data)

    @patch("app.routes.get_database")
    def test_empty_vocabulary_shows_helpful_state(self, get_database):
        get_database.return_value = {
            "vocabulary": FakeCollection([]),
            "verbal_questions": FakeCollection([]),
        }

        response = self.client.get("/vocabulary")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No vocabulary entries yet", response.data)

    @patch("app.routes.get_database")
    def test_empty_practice_shows_helpful_state(self, get_database):
        get_database.return_value = {
            "vocabulary": FakeCollection([]),
            "verbal_questions": FakeCollection([]),
        }

        response = self.client.get("/practice")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No practice questions yet", response.data)

    @patch("app.routes.get_database")
    def test_unanswered_submission_gets_helpful_message(self, get_database):
        get_database.return_value = self.database

        response = self.client.post("/practice", data={"question_id": "sample-01"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Choose an answer before submitting", response.data)

    def test_stylesheet_is_served(self):
        response = self.client.get("/static/css/style.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"prefers-reduced-motion", response.data)
        response.close()

    def test_session_page_and_script_are_served(self):
        response = self.client.get("/session")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"data-session-root", response.data)
        self.assertIn(b"session_score.js", response.data)
        self.assertIn(b"study_session.js", response.data)
        response.close()

        response = self.client.get("/static/js/study_session.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"function showSummary()", response.data)
        self.assertIn(b"Review Missed Questions", response.data)
        self.assertIn(b"Restart Session", response.data)
        self.assertIn(b"currentIndex >= questions.length", response.data)
        self.assertIn(b"currentIndex = 0", response.data)
        response.close()

    @patch("app.routes.get_database")
    def test_practice_page_does_not_reveal_answer_before_submission(self, get_database):
        get_database.return_value = self.database

        response = self.client.get("/practice")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"caustic", response.data)
        self.assertNotIn(b"Correct answer:", response.data)
        self.assertNotIn(b"The context indicates praise", response.data)

    @patch("app.routes.get_database")
    def test_practice_page_displays_question_source(self, get_database):
        get_database.return_value = {
            "verbal_questions": FakeCollection([dict(VERBAL_QUESTIONS[0])])
        }

        response = self.client.get("/practice")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Source: GRE Verbal Prep original practice", response.data)
        self.assertIn(b"Text Completion", response.data)
        self.assertNotIn(b"Correct answer:", response.data)

    @patch("app.routes.get_database")
    def test_submitting_answer_shows_result_and_explanation(self, get_database):
        get_database.return_value = self.database

        response = self.client.post("/practice", data={
            "question_id": "sample-01",
            "answer": "caustic",
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Not quite", response.data)
        self.assertIn(b"Correct answer:", response.data)
        self.assertIn(b"laudatory", response.data)
        self.assertIn(b"The context indicates praise.", response.data)

    @patch("app.routes.get_database")
    def test_correct_answer_gets_feedback(self, get_database):
        get_database.return_value = self.database

        response = self.client.post("/practice", data={
            "question_id": "sample-01",
            "answer": "laudatory",
        })

        self.assertIn(b"Correct", response.data)
        self.assertIn(b"The context indicates praise.", response.data)

    @patch("app.routes.get_database")
    def test_question_api_does_not_expose_answer_or_explanation(self, get_database):
        get_database.return_value = self.database

        response = self.client.get("/api/verbal-questions")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("correct_answer", response.get_json()[0])
        self.assertNotIn("explanation", response.get_json()[0])

    @patch("app.routes.get_database")
    def test_database_error_is_handled(self, get_database):
        get_database.side_effect = DatabaseConnectionError("database unavailable")

        with self.assertLogs(level="ERROR"):
            response = self.client.get("/api/verbal-questions")

        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.get_json())
        self.assertNotIn("database unavailable", response.get_json()["error"])
        self.assertNotIn(b"Traceback", response.data)

    @patch("app.routes.get_database")
    def test_practice_database_failure_keeps_safe_error_behavior(self, get_database):
        get_database.side_effect = DatabaseConnectionError("private connection detail")

        with self.assertLogs(level="ERROR"):
            response = self.client.get("/practice")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Study data is unavailable", response.data)
        self.assertNotIn(b"private connection detail", response.data)

    @patch("app.routes.get_database")
    def test_session_uses_five_unique_questions_without_answers(self, get_database):
        questions = [
            {
                "question_id": f"q-{index}", "type": "text_completion",
                "prompt": f"Prompt {index}", "choices": ["A", "B"],
                "correct_answer": "A", "explanation": "A is supported.",
            }
            for index in range(7)
        ]
        get_database.return_value = {"verbal_questions": FakeCollection(questions)}

        response = self.client.get("/api/study-session")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["session_count"], 5)
        self.assertEqual(len({q["question_id"] for q in data["questions"]}), 5)
        self.assertTrue(all("correct_answer" not in q and "explanation" not in q for q in data["questions"]))

    @patch("app.routes.random.sample")
    @patch("app.routes.get_database")
    def test_multiple_sessions_can_draw_from_larger_bank(self, get_database, sample):
        questions = [
            {
                "question_id": f"bank-{index}", "type": "text_completion",
                "prompt": f"Prompt {index}", "choices": ["A", "B"],
                "correct_answer": "A", "explanation": "A fits.",
            }
            for index in range(10)
        ]
        get_database.return_value = {"verbal_questions": FakeCollection(questions)}
        sample.side_effect = [questions[:5], questions[5:]]

        first = self.client.get("/api/study-session").get_json()
        second = self.client.get("/api/study-session").get_json()

        first_ids = {item["question_id"] for item in first["questions"]}
        second_ids = {item["question_id"] for item in second["questions"]}
        self.assertEqual(first["available_count"], 10)
        self.assertEqual(second["available_count"], 10)
        self.assertEqual(len(first_ids), 5)
        self.assertEqual(len(second_ids), 5)
        self.assertTrue(first_ids.isdisjoint(second_ids))

    @patch("app.routes.get_database")
    def test_session_skips_invalid_and_duplicate_database_records(self, get_database):
        valid = {
            "question_id": "safe", "type": "text_completion", "prompt": "A ____.",
            "choices": ["clear", "unclear"], "correct_answer": "clear",
            "explanation": "The sentence supports clear.",
        }
        invalid = {**valid, "question_id": "bad", "correct_answer": "not a choice"}
        duplicate = {**valid, "prompt": "Duplicate ID."}
        get_database.return_value = {
            "verbal_questions": FakeCollection([valid, invalid, duplicate])
        }

        with self.assertLogs(level="WARNING"):
            response = self.client.get("/api/study-session")

        data = response.get_json()
        self.assertEqual(data["available_count"], 1)
        self.assertEqual([item["question_id"] for item in data["questions"]], ["safe"])

    @patch("app.routes.get_database")
    def test_session_answer_rejects_invalid_database_record(self, get_database):
        invalid = {
            "question_id": "broken", "type": "text_completion", "prompt": "A ____.",
            "choices": ["A", "B"], "correct_answer": "outside choices",
        }
        get_database.return_value = {"verbal_questions": FakeCollection([invalid])}

        response = self.client.post("/api/study-session/answer", json={
            "question_id": "broken", "answers": ["A"],
        })

        self.assertEqual(response.status_code, 404)

    @patch("app.routes.get_database")
    def test_session_exposes_source_metadata_without_answer(self, get_database):
        question = dict(VERBAL_QUESTIONS[0])
        get_database.return_value = {"verbal_questions": FakeCollection([question])}

        public_question = self.client.get("/api/study-session").get_json()["questions"][0]

        self.assertEqual(public_question["source"]["kind"], "original")
        self.assertNotIn("correct_answer", public_question)
        self.assertNotIn("explanation", public_question)

    @patch("app.routes.get_database")
    def test_session_uses_available_questions_and_handles_empty_set(self, get_database):
        get_database.return_value = {"verbal_questions": self.database["verbal_questions"]}
        response = self.client.get("/api/study-session")
        self.assertEqual(response.get_json()["session_count"], 1)

        get_database.return_value = {"verbal_questions": FakeCollection([])}
        response = self.client.get("/api/study-session")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["session_count"], 0)

    @patch("app.routes.get_database")
    def test_session_answer_returns_correctness_and_explanation(self, get_database):
        get_database.return_value = self.database

        correct = self.client.post("/api/study-session/answer", json={
            "question_id": "sample-01", "answers": ["laudatory"],
        })
        incorrect = self.client.post("/api/study-session/answer", json={
            "question_id": "sample-01", "answers": ["caustic"],
        })

        self.assertTrue(correct.get_json()["correct"])
        self.assertFalse(incorrect.get_json()["correct"])
        self.assertEqual(incorrect.get_json()["correct_answer"], "laudatory")
        self.assertIn("context indicates praise", incorrect.get_json()["explanation"])

    @patch("app.routes.get_database")
    def test_session_answer_checks_sentence_equivalence_and_invalid_answers(self, get_database):
        collection = FakeCollection([{
            "question_id": "se-01", "type": "sentence_equivalence",
            "prompt": "The account was ____.",
            "choices": ["judicious", "impartial", "ornate"],
            "correct_answer": ["judicious", "impartial"], "explanation": "Both fit.",
        }])
        get_database.return_value = {"verbal_questions": collection}

        correct = self.client.post("/api/study-session/answer", json={
            "question_id": "se-01", "answers": ["impartial", "judicious"],
        })
        invalid = self.client.post("/api/study-session/answer", json={
            "question_id": "se-01", "answers": ["unknown"],
        })

        self.assertTrue(correct.get_json()["correct"])
        self.assertEqual(invalid.status_code, 400)

    @patch("app.routes.get_database")
    def test_session_database_failures_are_safe_and_retryable(self, get_database):
        get_database.side_effect = DatabaseConnectionError("private connection details")

        with self.assertLogs(level="ERROR"):
            load_response = self.client.get("/api/study-session")
        with self.assertLogs(level="ERROR"):
            answer_response = self.client.post("/api/study-session/answer", json={
                "question_id": "sample-01", "answers": ["laudatory"],
            })

        self.assertEqual(load_response.status_code, 503)
        self.assertIn("try again", load_response.get_json()["error"])
        self.assertEqual(answer_response.status_code, 503)
        self.assertNotIn("private connection details", answer_response.get_json()["error"])


class AnswerCheckingTests(unittest.TestCase):
    def test_single_answer_requires_exact_match(self):
        self.assertTrue(answer_is_correct("B", ["B"]))
        self.assertFalse(answer_is_correct("B", ["A"]))
        self.assertFalse(answer_is_correct("B", ["B", "A"]))

    def test_sentence_equivalence_requires_both_answers(self):
        correct = ["judicious", "impartial"]
        self.assertTrue(answer_is_correct(correct, ["impartial", "judicious"]))
        self.assertFalse(answer_is_correct(correct, ["judicious"]))
        self.assertFalse(answer_is_correct(correct, ["judicious", "ornate"]))


class SeedTests(unittest.TestCase):
    def test_seed_dataset_has_requested_counts_and_vocabulary_difficulty(self):
        self.assertEqual(len(VOCABULARY), 10)
        self.assertEqual(len(VERBAL_QUESTIONS), 5)
        self.assertTrue(all(item.get("difficulty") for item in VOCABULARY))
        self.assertTrue(all(is_valid_question(item) for item in VERBAL_QUESTIONS))
        self.assertTrue(all(item["source"]["kind"] == "original" for item in VERBAL_QUESTIONS))

    def test_question_validator_rejects_incomplete_or_invalid_records(self):
        valid = {
            "question_id": "valid", "type": "text_completion", "prompt": "A ____.",
            "choices": ["clear", "unclear"], "correct_answer": "clear",
        }
        self.assertTrue(is_valid_question(valid))
        self.assertFalse(is_valid_question({**valid, "correct_answer": "missing"}))
        self.assertFalse(is_valid_question({**valid, "choices": ["same", "same"]}))
        self.assertFalse(is_valid_question({**valid, "type": "unknown"}))
        self.assertFalse(is_valid_question({**valid, "explanation": []}))
        self.assertFalse(is_valid_question({
            **valid, "type": "reading_comprehension", "passage": "",
        }))

    def test_seed_uses_upserts_for_idempotency(self):
        collection = Mock()
        document = {"word": "abate", "definition": "less intense"}

        seed_collection(collection, [document], "word", "vocabulary")

        collection.update_one.assert_called_once_with(
            {"word": "abate"}, {"$set": document}, upsert=True
        )

    def test_question_seed_skips_invalid_and_duplicate_ids(self):
        collection = Mock()
        question = dict(VERBAL_QUESTIONS[0])
        duplicate = {**question, "prompt": "A second record with the same ID."}
        invalid = {**question, "correct_answer": "not a choice"}

        seed_verbal_questions(collection, [question, duplicate, invalid])

        collection.update_one.assert_called_once_with(
            {"question_id": question["question_id"]},
            {"$set": question},
            upsert=True,
        )


if __name__ == "__main__":
    unittest.main()
