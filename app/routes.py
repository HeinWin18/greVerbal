"""Page and JSON routes for the GRE Preparation Guide & Planner."""

from flask import Blueprint, current_app, jsonify, render_template, request
from pymongo.errors import PyMongoError

from app.database import DatabaseError, get_database

main = Blueprint("main", __name__)


@main.route("/")
def home():
    return render_template("index.html")


@main.route("/vocabulary")
def vocabulary():
    words, database_error = load_collection("vocabulary", "word")
    return render_template(
        "vocabulary.html", vocabulary=words, database_error=database_error
    )


@main.route("/practice", methods=["GET", "POST"])
def practice():
    questions, database_error = load_collection("verbal_questions", "question_id")
    selected_answers = request.form.getlist("answer") if request.method == "POST" else []
    feedback = None

    if request.method == "POST" and not database_error:
        question_id = request.form.get("question_id", "")
        question = next(
            (item for item in questions if item.get("question_id") == question_id),
            None,
        )
        if question is None:
            feedback = {"error": "That question could not be found. Refresh and try again."}
        elif not selected_answers:
            feedback = {"error": "Choose an answer before submitting."}
        elif any(answer not in question.get("choices", []) for answer in selected_answers):
            feedback = {"error": "Select an answer from the choices shown."}
        else:
            correct = answer_is_correct(question.get("correct_answer"), selected_answers)
            feedback = {
                "correct": correct,
                "correct_answer": question.get("correct_answer"),
                "explanation": question.get("explanation", ""),
                "question_id": question_id,
            }

    public_questions = [
        {
            key: value
            for key, value in question.items()
            if key not in {"correct_answer", "explanation"}
        }
        for question in questions
    ]
    return render_template(
        "practice.html",
        questions=public_questions,
        database_error=database_error,
        feedback=feedback,
        selected_answers=selected_answers,
    )


@main.route("/api/vocabulary")
def vocabulary_api():
    return collection_response("vocabulary", "word")


@main.route("/api/verbal-questions")
def verbal_questions_api():
    return collection_response(
        "verbal_questions", "question_id", hidden_fields={"correct_answer", "explanation"}
    )


def collection_response(collection_name, sort_key, hidden_fields=None):
    try:
        documents = list(
            get_database()[collection_name]
            .find({}, {"_id": 0})
            .sort(sort_key, 1)
        )
        for document in documents:
            for field in hidden_fields or ():
                document.pop(field, None)
        return jsonify(documents)
    except (DatabaseError, PyMongoError):
        current_app.logger.exception(
            "Failed to retrieve MongoDB collection '%s'.", collection_name
        )
        return jsonify({
            "error": "Study data is unavailable. Check your MongoDB connection and try again."
        }), 503


def load_collection(collection_name, sort_key):
    try:
        documents = list(
            get_database()[collection_name]
            .find({}, {"_id": 0})
            .sort(sort_key, 1)
        )
        return documents, None
    except (DatabaseError, PyMongoError):
        current_app.logger.exception(
            "Failed to load MongoDB collection '%s'.", collection_name
        )
        return [], "Study data is unavailable. Check your MongoDB connection and try again."


def answer_is_correct(correct_answer, selected_answers):
    """Compare submitted choices against a single- or multi-answer key."""
    if isinstance(correct_answer, list):
        return len(selected_answers) == len(set(selected_answers)) and set(
            selected_answers
        ) == set(correct_answer)
    return len(selected_answers) == 1 and selected_answers[0] == correct_answer
