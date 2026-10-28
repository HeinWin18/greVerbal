const assert = require("node:assert/strict");
const test = require("node:test");
const { summarize } = require("../app/static/js/session_score.js");

test("session score counts completed answers and preserves missed questions", () => {
    const missedQuestion = { question_id: "q2", result: { correct: false } };
    const summary = summarize([
        { question_id: "q1", result: { correct: true } },
        missedQuestion,
        { question_id: "q3" },
    ]);

    assert.equal(summary.answered, 2);
    assert.equal(summary.correct, 1);
    assert.deepEqual(summary.missed, [missedQuestion]);
});

test("an unanswered session has a zero score", () => {
    assert.deepEqual(summarize([{ question_id: "q1" }]), {
        answered: 0,
        correct: 0,
        missed: [],
    });
});
