import unittest
from unittest.mock import Mock, patch

from app import create_app
from app.database import DatabaseConnectionError
from app.routes import answer_is_correct
from scripts.seed_data import VERBAL_QUESTIONS, VOCABULARY, seed_collection


class FakeCursor(list):
    def sort(self, key, direction):
        return FakeCursor(sorted(self, key=lambda item: item.get(key, ""), reverse=direction < 0))


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, query, projection):
        return FakeCursor(self.documents)


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
        self.assertIn(b"Study Vocabulary", response.data)
        self.assertIn(b"Practice Verbal Questions", response.data)
        self.assertIn(b'href="/vocabulary"', response.data)
        self.assertIn(b'href="/practice"', response.data)

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

    @patch("app.routes.get_database")
    def test_practice_page_does_not_reveal_answer_before_submission(self, get_database):
        get_database.return_value = self.database

        response = self.client.get("/practice")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"caustic", response.data)
        self.assertNotIn(b"Correct answer:", response.data)
        self.assertNotIn(b"The context indicates praise", response.data)

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

    def test_seed_uses_upserts_for_idempotency(self):
        collection = Mock()
        document = {"word": "abate", "definition": "less intense"}

        seed_collection(collection, [document], "word", "vocabulary")

        collection.update_one.assert_called_once_with(
            {"word": "abate"}, {"$set": document}, upsert=True
        )


if __name__ == "__main__":
    unittest.main()
