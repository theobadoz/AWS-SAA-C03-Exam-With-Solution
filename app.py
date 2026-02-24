import streamlit as st
import re

SOLUTION_FILE = "AWS SAA-03 Solution.txt"


def parse_questions(filepath):
    questions = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    current_question = []
    current_answer = []
    in_question = False
    in_answer = False

    for line in lines:
        line_stripped = line.strip()

        if re.match(r"^\s*\d+\]", line_stripped):
            if current_question and current_answer:
                questions.append(
                    {
                        "question": " ".join(current_question),
                        "answer": " ".join(current_answer),
                    }
                )
            current_question = [line_stripped]
            current_answer = []
            in_question = True
            in_answer = False
        elif in_question and re.match(r"^[A-D]\.", line_stripped):
            in_answer = True
            current_answer.append(line_stripped)
        elif in_answer and line_stripped:
            current_answer.append(line_stripped)
        elif in_question and not in_answer:
            current_question.append(line_stripped)

    if current_question and current_answer:
        questions.append(
            {
                "question": " ".join(current_question),
                "answer": " ".join(current_answer),
            }
        )

    return questions


def search_questions(questions, query):
    query_lower = query.lower()
    results = []

    for q in questions:
        if query_lower in q["question"].lower() or query_lower in q["answer"].lower():
            results.append(q)
        else:
            words = query_lower.split()
            match_count = sum(
                1
                for word in words
                if word in q["question"].lower() or word in q["answer"].lower()
            )
            if match_count > 0:
                q["match_score"] = match_count
                results.append(q)

    results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return results[:10]


def main():
    st.set_page_config(page_title="AWS SAA-C03 Q&A", page_icon="📚")

    st.title("AWS SAA-C03 Exam Q&A")
    st.markdown("Ask questions about AWS Solutions Architect concepts")

    questions = parse_questions(SOLUTION_FILE)
    st.session_state.total_questions = len(questions)

    query = st.text_input(
        "Ask a question:", placeholder="e.g., S3, EC2, RDS, CloudFront..."
    )

    if query:
        results = search_questions(questions, query)

        if results:
            st.markdown(f"Found {len(results)} relevant results:")
            for i, result in enumerate(results, 1):
                with st.expander(f"Q: {result['question'][:100]}...", expanded=True):
                    st.markdown(f"**Answer:** {result['answer']}")
        else:
            st.warning("No matching questions found. Try different keywords.")

    st.markdown("---")
    st.markdown(f"📚 Total questions in database: {len(questions)}")


if __name__ == "__main__":
    main()
