(function attachSessionScoring(root, factory) {
    const scoring = factory();
    if (typeof module !== "undefined" && module.exports) {
        module.exports = scoring;
    }
    root.GreStudySession = scoring;
})(typeof window === "undefined" ? globalThis : window, function createSessionScoring() {
    "use strict";

    function summarize(questions) {
        const answered = questions.filter((question) => question.result);
        const missed = answered.filter((question) => !question.result.correct);
        return {
            answered: answered.length,
            correct: answered.length - missed.length,
            missed,
        };
    }

    return { summarize };
});
