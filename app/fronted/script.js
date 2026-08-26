const API_URL = "http://127.0.0.1:8000/ask";


// ======================================================
// ASK QUESTION
// ======================================================

async function askQuestion() {

    const questionBox = document.getElementById("question");
    const answerBox = document.getElementById("answer");
    const loadingBox = document.getElementById("loading");
    const confidenceBox = document.getElementById("confidence");
    const statusBox = document.getElementById("status");
    const agentTypeBox = document.getElementById("agentType");
    const askButton = document.getElementById("askButton");

    const question = questionBox.value.trim();

    if (question === "") {
        alert("Please enter a question.");
        return;
    }

    try {

        if (loadingBox) {
            loadingBox.style.display = "block";
            loadingBox.innerText = "🤖 AI is thinking...";
        }

        if (askButton) {
            askButton.disabled = true;
        }

        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question
            })
        });


        if (!response.ok) {
            throw new Error("Server error: " + response.status);
        }


        const data = await response.json();

        console.log("Backend response:", data);


        // ==================================================
        // ANSWER
        // ==================================================

        let finalAnswer = data.answer || "No answer received.";

        if (data.ticket_id) {
            finalAnswer += "\n\n🎫 Ticket ID: " + data.ticket_id;
        }

        if (answerBox) {
            answerBox.innerText = finalAnswer;
        }


        // ==================================================
        // CONFIDENCE
        // ==================================================

        if (confidenceBox) {

            if (data.confidence !== undefined) {

                confidenceBox.innerText =
                    Math.round(data.confidence * 100) + "%";

            } else {

                confidenceBox.innerText = "-";
            }
        }


        // ==================================================
        // STATUS
        // ==================================================

        if (statusBox) {

            if (data.status === "ticket_created") {

                statusBox.innerText = "🎫 Ticket Created";

            } else if (data.status === "found") {

                statusBox.innerText = "Answered";

            } else {

                statusBox.innerText =
                    data.status || "Answered";
            }
        }


        // ==================================================
        // AGENT TYPE
        // ==================================================

        if (agentTypeBox) {

            agentTypeBox.innerText =
                data.type ||
                data.agent_type ||
                "AI Assistant";
        }


        // ==================================================
        // FRONTEND HISTORY
        // ==================================================

        addToHistory(
            question,
            finalAnswer,
            data.type || "AI Assistant"
        );


    } catch (error) {

        console.error("Student Help Desk Error:", error);

        if (answerBox) {
            answerBox.innerText =
                "Unable to connect to Student Help Desk server.";
        }

        if (statusBox) {
            statusBox.innerText = "Error";
        }

    } finally {

        if (loadingBox) {
            loadingBox.style.display = "none";
        }

        if (askButton) {
            askButton.disabled = false;
        }
    }
}


// ======================================================
// ADD FRONTEND HISTORY
// ======================================================

function addToHistory(question, answer, type) {

    const historyBox = document.getElementById("history");

    if (!historyBox) {
        return;
    }

    const item = document.createElement("div");

    item.className = "history-item";

    item.innerHTML = `
        <p><strong>👤 Question:</strong> ${escapeHtml(question)}</p>
        <p><strong>🤖 Answer:</strong> ${escapeHtml(answer)}</p>
        <p><strong>⚙️ Agent:</strong> ${escapeHtml(type)}</p>
    `;

    historyBox.prepend(item);
}


// ======================================================
// CLEAR CHAT
// ======================================================

function clearChat() {

    const questionBox = document.getElementById("question");
    const answerBox = document.getElementById("answer");
    const historyBox = document.getElementById("history");
    const confidenceBox = document.getElementById("confidence");
    const statusBox = document.getElementById("status");
    const agentTypeBox = document.getElementById("agentType");


    if (questionBox) {
        questionBox.value = "";
    }

    if (answerBox) {
        answerBox.innerText = "Your answer will appear here...";
    }

    if (historyBox) {
        historyBox.innerHTML = "";
    }

    if (confidenceBox) {
        confidenceBox.innerText = "-";
    }

    if (statusBox) {
        statusBox.innerText = "Waiting";
    }

    if (agentTypeBox) {
        agentTypeBox.innerText = "-";
    }


    fetch(
        "http://127.0.0.1:8000/clear-memory",
        {
            method: "POST"
        }
    ).catch(function (error) {
        console.log("Clear memory error:", error);
    });
}


// ======================================================
// SAFE HTML
// ======================================================

function escapeHtml(text) {

    const div = document.createElement("div");

    div.textContent = String(text);

    return div.innerHTML;
}


// ======================================================
// CTRL + ENTER
// ======================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const questionBox =
            document.getElementById("question");

        if (questionBox) {

            questionBox.addEventListener(
                "keydown",
                function (event) {

                    if (
                        event.ctrlKey &&
                        event.key === "Enter"
                    ) {

                        event.preventDefault();

                        askQuestion();
                    }
                }
            );
        }
    }
);