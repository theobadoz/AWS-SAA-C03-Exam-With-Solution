import streamlit as st
import re
import random
import json
import os
from datetime import datetime
import uuid

QUESTIONS_FILE = "AWS SAA-03 Questions.txt"
HISTORY_FILE = "quiz_history.json"


def parse_questions(filepath):
    questions = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.split("=" * 80)

    for block in blocks:
        if not block.strip():
            continue

        lines = block.strip().split("\n")
        if not lines:
            continue

        first_line = lines[0].strip()
        id_match = re.match(r"^(\d+)\]", first_line)
        if not id_match:
            continue

        q_id = int(id_match.group(1))
        question_text = first_line[id_match.end() :].strip()

        options = {}
        correct_answer = None

        for line in lines[1:]:
            line = line.strip()
            opt_match = re.match(r"^([A-D])[\.\)](.+)", line)
            if opt_match:
                opt_letter = opt_match.group(1)
                opt_text = opt_match.group(2).strip()
                if "[CORRECT]" in opt_text:
                    correct_answer = opt_letter
                    opt_text = opt_text.replace("[CORRECT]", "").strip()
                options[opt_letter] = opt_text

        if options:
            questions.append(
                {
                    "id": q_id,
                    "question": question_text,
                    "options": options,
                    "correct_answer": correct_answer,
                }
            )

    return questions


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def start_quiz(all_questions, num_questions, mode):
    all_questions_filtered = [
        q
        for q in all_questions
        if q.get("options")
        and len(q.get("options", {})) >= 2
        and q.get("correct_answer")
        and "Choose two" not in q.get("question", "")
    ]
    quiz_questions = random.sample(
        all_questions_filtered, min(num_questions, len(all_questions_filtered))
    )
    for i, q in enumerate(quiz_questions):
        q["user_answer"] = None
        q["answered"] = False

        correct_letter = q.get("correct_answer", "A")
        correct_text = q.get("options", {}).get(correct_letter, "")

        option_map = {}
        letters = ["A", "B", "C", "D"]
        for letter in letters:
            if letter in q.get("options", {}):
                opt_text = q["options"][letter]
                option_map[letter] = {
                    "text": opt_text[:200],
                    "type": "correct" if letter == correct_letter else "wrong",
                }

        q["quiz_options"] = option_map
        q["correct_answer"] = correct_letter

    return quiz_questions


def get_option_preview(text, max_len=100):
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def show_question(q, mode, idx):
    st.markdown(f"### Question {idx + 1} (ID: {q.get('id', '?')})")
    st.markdown(q["question"])
    st.markdown("---")

    quiz_options = q.get("quiz_options", {})
    option_letters = ["A", "B", "C", "D"]

    selected = st.radio(
        "Select your answer:",
        option_letters,
        format_func=lambda x: f"{x}. {quiz_options.get(x, {}).get('text', '')}"
        if x in quiz_options
        else x,
        key=f"question_{idx}",
        disabled=mode == "learning" and q.get("answered", False),
    )

    correct = q.get("correct_answer", "A")

    if mode == "learning":
        if not q.get("answered", False):
            if st.button("Submit Answer", key=f"submit_{idx}"):
                q["user_answer"] = selected
                q["answered"] = True
                st.rerun()
        else:
            user_ans = q.get("user_answer")
            is_correct = user_ans == correct

            if is_correct:
                st.success("✓ Correct!")
            else:
                st.error(f"✗ Incorrect. The correct answer is {correct}.")

            st.markdown(
                f"**Explanation:** {quiz_options.get(correct, {}).get('text', '')}"
            )
    else:
        q["user_answer"] = selected


def show_results(quiz_questions, mode):
    st.markdown("---")
    st.markdown("## Quiz Results")

    score = 0
    for i, q in enumerate(quiz_questions):
        quiz_options = q.get("quiz_options", {})
        correct = q.get("correct_answer", "A")

        user_ans = q.get("user_answer")
        is_correct = user_ans == correct

        if is_correct:
            score += 1

        with st.expander(f"Question {i + 1}", expanded=True):
            st.markdown(f"**Q:** {q['question'][:150]}...")

            for letter in ["A", "B", "C", "D"]:
                if letter in quiz_options:
                    opt_data = quiz_options[letter]
                    prefix = (
                        "✓"
                        if opt_data["type"] == "correct"
                        else ("→" if letter == user_ans else " ")
                    )
                    st.markdown(f"{prefix} **{letter}.** {opt_data['text']}")

            if is_correct:
                st.success(f"✓ Correct")
            else:
                st.error(f"✗ Your answer: {user_ans or 'None'} | Correct: {correct}")

    percentage = (score / len(quiz_questions)) * 100
    st.markdown(f"### Score: {score}/{len(quiz_questions)} ({percentage:.1f}%)")

    return score, len(quiz_questions), percentage


def show_history():
    st.markdown("## Quiz History")
    history = load_history()

    if not history:
        st.info("No quiz history yet. Take your first quiz!")
        return

    for attempt in reversed(history[-10:]):
        date = datetime.fromisoformat(attempt["date"]).strftime("%Y-%m-%d %H:%M")
        mode_str = "Learning" if attempt["mode"] == "learning" else "Test"
        st.markdown(
            f"**{date}** - {attempt['score']}/{attempt['total']} ({attempt['percentage']:.1f}%) - {mode_str}"
        )

    if len(history) > 1:
        st.markdown("### Progress Overview")
        scores = [h["percentage"] for h in history]
        avg = sum(scores) / len(scores)
        best = max(scores)
        recent_avg = sum(scores[-5:]) / min(len(scores), 5)

        col1, col2, col3 = st.columns(3)
        col1.metric("Average Score", f"{avg:.1f}%")
        col2.metric("Best Score", f"{best:.1f}%")
        col3.metric("Recent Average (last 5)", f"{recent_avg:.1f}%")


def main():
    st.set_page_config(page_title="AWS SAA-C03 Quiz", page_icon="📚")

    questions = parse_questions(QUESTIONS_FILE)

    if "quiz_active" not in st.session_state:
        st.session_state.quiz_active = False
    if "quiz_questions" not in st.session_state:
        st.session_state.quiz_questions = []
    if "quiz_mode" not in st.session_state:
        st.session_state.quiz_mode = "learning"
    if "history" not in st.session_state:
        st.session_state.history = load_history()

    tab1, tab2 = st.tabs(["📝 Quiz", "📊 History"])

    with tab1:
        if not st.session_state.quiz_active:
            st.title("AWS SAA-C03 Practice Quiz")

            valid_count = len(
                [
                    q
                    for q in questions
                    if len(q.get("options", {})) >= 2
                    and "Choose two" not in q.get("question", "")
                ]
            )
            st.markdown(
                f"Database: **{valid_count} questions** (with full multiple choice options from exam)"
            )

            col1, col2 = st.columns(2)
            with col1:
                num_questions = st.selectbox(
                    "Number of questions", options=[10, 20, 40, 65, 100], index=2
                )
            with col2:
                mode = st.radio(
                    "Quiz mode",
                    ["learning", "real_test"],
                    format_func=lambda x: "Learning (answers after each question)"
                    if x == "learning"
                    else "Real Test (answers at end)",
                )

            if st.button("Start Quiz", type="primary"):
                st.session_state.quiz_questions = start_quiz(
                    questions, num_questions, mode
                )
                st.session_state.quiz_active = True
                st.session_state.quiz_mode = mode
                st.session_state.current_question = 0
                st.rerun()
        else:
            quiz_questions = st.session_state.quiz_questions
            current = st.session_state.current_question
            mode = st.session_state.quiz_mode

            col1, col2 = st.columns([3, 1])
            with col1:
                st.title(f"Question {current + 1}/{len(quiz_questions)}")
            with col2:
                if st.button("End Quiz", type="secondary"):
                    score, total, percentage = show_results(quiz_questions, mode)

                    history = load_history()
                    history.append(
                        {
                            "id": str(uuid.uuid4()),
                            "date": datetime.now().isoformat(),
                            "score": score,
                            "total": total,
                            "percentage": percentage,
                            "mode": mode,
                        }
                    )
                    save_history(history)
                    st.session_state.history = history

                    st.session_state.quiz_active = False
                    st.session_state.quiz_questions = []
                    st.rerun()

            if current < len(quiz_questions):
                show_question(quiz_questions[current], mode, current)

                nav_col1, nav_col2 = st.columns(2)
                if current > 0:
                    if nav_col1.button("← Previous"):
                        st.session_state.current_question -= 1
                        st.rerun()
                if current < len(quiz_questions) - 1:
                    if nav_col2.button("Next →"):
                        st.session_state.current_question += 1
                        st.rerun()
                else:
                    if nav_col2.button("Finish Quiz"):
                        score, total, percentage = show_results(quiz_questions, mode)

                        history = load_history()
                        history.append(
                            {
                                "id": str(uuid.uuid4()),
                                "date": datetime.now().isoformat(),
                                "score": score,
                                "total": total,
                                "percentage": percentage,
                                "mode": mode,
                            }
                        )
                        save_history(history)
                        st.session_state.history = history

                        st.session_state.quiz_active = False
                        st.session_state.quiz_questions = []
                        st.rerun()

    with tab2:
        show_history()


if __name__ == "__main__":
    main()
