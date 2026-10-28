(() => {
    "use strict";

    const root = document.querySelector("[data-session-root]");
    if (!root) return;

    const status = root.querySelector("[data-session-status]");
    const stage = root.querySelector("[data-session-stage]");
    let questions = [];
    let currentIndex = 0;
    let reviewIndex = 0;
    let busy = false;

    function makeButton(label, onClick, className = "study-button") {
        const button = document.createElement("button");
        button.type = "button";
        button.className = className;
        button.textContent = label;
        button.addEventListener("click", onClick);
        return button;
    }

    function setStatus(message, isError = false) {
        status.textContent = message;
        status.classList.toggle("session-error", isError);
    }

    function retryPanel(message) {
        stage.replaceChildren(makeButton("Retry", startSession));
        setStatus(message, true);
    }

    function startSession() {
        questions = [];
        currentIndex = 0;
        reviewIndex = 0;
        stage.replaceChildren();
        setStatus("Loading your questions…");
        fetch(root.dataset.questionsUrl)
            .then((response) => {
                if (!response.ok) throw new Error("Unable to load questions");
                return response.json();
            })
            .then((data) => {
                questions = Array.isArray(data.questions) ? data.questions : [];
                if (!questions.length) {
                    retryPanel("No verbal questions are available yet. Please retry in a moment.");
                    return;
                }
                if (questions.length < data.limit) {
                    setStatus(`Only ${questions.length} question${questions.length === 1 ? " is" : "s are"} available, so this session will use the available questions.`);
                } else {
                    setStatus(`Question 1 of ${questions.length}`);
                }
                renderQuestion();
            })
            .catch(() => retryPanel("Study questions could not be loaded. Check your connection and retry."));
    }

    function renderQuestion() {
        const question = questions[currentIndex];
        setStatus(`Question ${currentIndex + 1} of ${questions.length}`);
        renderQuestionCard(question, false);
    }

    function renderQuestionCard(question, isReview) {
        const card = document.createElement("article");
        card.className = "question-card session-question-card";
        const label = document.createElement("p");
        label.className = "question-label";
        label.textContent = `${(question.type || "VERBAL").replaceAll("_", " ").toUpperCase()}${question.type === "sentence_equivalence" ? " · SELECT TWO" : ""}`;
        card.append(label);

        if (question.passage) {
            const passage = document.createElement("p");
            passage.className = "passage";
            passage.textContent = question.passage;
            card.append(passage);
        }
        const prompt = document.createElement("h2");
        prompt.textContent = question.prompt;
        card.append(prompt);

        renderSource(card, question.source);

        if (isReview) {
            renderReviewFeedback(card, question);
        } else {
            renderAnswerForm(card, question);
        }
        stage.replaceChildren(card);
    }

    function renderSource(card, source) {
        if (!source || !source.title) return;
        const attribution = document.createElement("p");
        attribution.className = "question-source";
        attribution.append(document.createTextNode(`Source: ${source.title}`));
        if (source.section) attribution.append(document.createTextNode(` · ${source.section}`));
        if (typeof source.url === "string") {
            try {
                const url = new URL(source.url, window.location.href);
                if (url.protocol === "https:" || url.protocol === "http:") {
                    const link = document.createElement("a");
                    link.href = url.href;
                    link.textContent = " View source";
                    link.target = "_blank";
                    link.rel = "noopener noreferrer";
                    attribution.append(link);
                }
            } catch (_error) {
                // Ignore malformed source links while retaining the attribution.
            }
        }
        card.append(attribution);
    }

    function renderAnswerForm(card, question) {
        const form = document.createElement("form");
        form.className = "session-answer-form";
        const fieldset = document.createElement("fieldset");
        fieldset.className = "answer-options";
        const legend = document.createElement("legend");
        legend.className = "visually-hidden";
        legend.textContent = question.type === "sentence_equivalence" ? "Select two answers" : "Select one answer";
        fieldset.append(legend);

        question.choices.forEach((choice, index) => {
            const label = document.createElement("label");
            label.className = "answer-choice";
            const input = document.createElement("input");
            input.type = question.type === "sentence_equivalence" ? "checkbox" : "radio";
            input.name = "answer";
            input.value = choice;
            input.id = `session-choice-${index}`;
            const text = document.createElement("span");
            text.textContent = choice;
            label.append(input, text);
            fieldset.append(label);
        });

        const submit = document.createElement("button");
        submit.type = "submit";
        submit.className = "study-button";
        submit.textContent = "Submit Answer";
        form.append(fieldset, submit);
        form.addEventListener("submit", (event) => submitAnswer(event, form, question));
        card.append(form);
    }

    async function submitAnswer(event, form, question) {
        event.preventDefault();
        if (busy || question.result) return;
        const answers = Array.from(form.querySelectorAll("input:checked"), (input) => input.value);
        if (!answers.length) {
            setStatus("Choose an answer before submitting.", true);
            return;
        }
        busy = true;
        const submit = form.querySelector("button[type='submit']");
        submit.disabled = true;
        setStatus("Checking your answer…");
        try {
            const response = await fetch(root.dataset.answerUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question_id: question.question_id, answers }),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "Your answer could not be checked.");
            question.result = { ...result, answers };
            showFeedback(question);
        } catch (error) {
            setStatus(error.message || "Your answer could not be checked. Please retry.", true);
            submit.disabled = false;
        } finally {
            busy = false;
        }
    }

    function showFeedback(question) {
        const card = stage.querySelector(".question-card");
        const form = card.querySelector("form");
        form.remove();
        const feedback = document.createElement("div");
        feedback.className = `feedback ${question.result.correct ? "feedback-correct" : "feedback-incorrect"}`;
        feedback.setAttribute("role", "status");
        const heading = document.createElement("h3");
        heading.textContent = question.result.correct ? "Correct" : "Not quite";
        feedback.append(heading);
        if (!question.result.correct) {
            const correct = document.createElement("p");
            const strong = document.createElement("strong");
            strong.textContent = "Correct answer: ";
            correct.append(strong, document.createTextNode(Array.isArray(question.result.correct_answer) ? question.result.correct_answer.join(", ") : question.result.correct_answer));
            feedback.append(correct);
        }
        const explanation = document.createElement("p");
        explanation.textContent = question.result.explanation;
        feedback.append(explanation);
        const next = currentIndex + 1 < questions.length ? "Continue" : "See Session Result";
        feedback.append(makeButton(next, () => {
            currentIndex += 1;
            if (currentIndex >= questions.length) showSummary();
            else renderQuestion();
        }));
        card.append(feedback);
        setStatus(`Question ${currentIndex + 1} of ${questions.length} · Answer checked`);
    }

    function showSummary() {
        const { answered, correct, missed } = window.GreStudySession.summarize(questions);
        setStatus("Session complete");
        const card = document.createElement("section");
        card.className = "session-summary";
        const heading = document.createElement("h2");
        heading.textContent = "Session complete.";
        const result = document.createElement("p");
        result.className = "session-score";
        result.textContent = `You answered ${correct} of ${answered} correctly.`;
        const copy = document.createElement("p");
        copy.textContent = missed.length ? "Review the explanations for the questions you missed, or start another session." : "You got every question right. Start another session whenever you’re ready.";
        card.append(heading, result, copy);
        if (missed.length) card.append(makeButton("Review Missed Questions", () => reviewMissedQuestions()));
        card.append(makeButton("Restart Session", startSession, "study-button button-secondary"));
        stage.replaceChildren(card);
    }

    function reviewMissedQuestions() {
        reviewIndex = 0;
        renderMissedQuestion();
    }

    function renderMissedQuestion() {
        const missed = questions.filter((question) => question.result && !question.result.correct);
        if (reviewIndex >= missed.length) {
            showSummary();
            return;
        }
        setStatus(`Reviewing missed question ${reviewIndex + 1} of ${missed.length}`);
        const question = missed[reviewIndex];
        renderQuestionCard(question, true);
        const feedback = stage.querySelector(".feedback");
        feedback.append(makeButton(reviewIndex + 1 < missed.length ? "Next Missed Question" : "Back to Session Result", () => {
            reviewIndex += 1;
            renderMissedQuestion();
        }));
    }

    function renderReviewFeedback(card, question) {
        const feedback = document.createElement("div");
        feedback.className = "feedback feedback-incorrect";
        const heading = document.createElement("h3");
        heading.textContent = "Review";
        const answer = document.createElement("p");
        const strong = document.createElement("strong");
        strong.textContent = "Correct answer: ";
        answer.append(strong, document.createTextNode(Array.isArray(question.result.correct_answer) ? question.result.correct_answer.join(", ") : question.result.correct_answer));
        const explanation = document.createElement("p");
        explanation.textContent = question.result.explanation;
        feedback.append(heading, answer, explanation);
        card.append(feedback);
    }

    startSession();
})();
