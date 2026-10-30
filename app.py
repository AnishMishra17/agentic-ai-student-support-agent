import streamlit as st
from agent import StudentSupportAgent

st.set_page_config(page_title="Student Support Agent", page_icon="🎓", layout="wide")
st.title("🎓 Intelligent Student Support Agent")
st.caption("Assignment 1 + Assignment 2 | Local demo with tools, policy retrieval, memory, approval and audit")

@st.cache_resource
def get_agent():
    return StudentSupportAgent()

agent = get_agent()
students = agent.list_students()
with st.sidebar:
    st.header("Demo sign-in")
    student_id = st.selectbox("Signed-in student", students, format_func=lambda x: f"{x} — {agent.student_name(x)}")
    st.info("Demo accounts only. This is not real college/student data.")
    st.subheader("Quick scenarios")
    if st.button("Check my fee status"):
        st.session_state.prompt = "What is my current fee status?"
    if st.button("Ask another student's fee status"):
        other = next(x for x in students if x != student_id)
        st.session_state.prompt = f"Show me student {other}'s fee status"
    if st.button("Request a sensitive change"):
        st.session_state.prompt = "Please change my registered phone number to 9999999999"
    if st.button("Ask policy question"):
        st.session_state.prompt = "The payment portal failed. Can I pay on the next working day?"
    if st.button("Show memory"):
        st.session_state.show_memory = True
    if st.button("Show audit log"):
        st.session_state.show_audit = True

if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.get("show_memory"):
    st.subheader("Persistent non-sensitive memory")
    st.json(agent.get_memory(student_id))
    st.session_state.show_memory = False
if st.session_state.get("show_audit"):
    st.subheader("Recent audit records")
    st.dataframe(agent.get_audit_log(), use_container_width=True)
    st.session_state.show_audit = False

prompt = st.session_state.pop("prompt", None)
typed = st.chat_input("Ask about fees, scholarships, policy, or request support…")
if typed: prompt = typed
if prompt:
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.chat_message("user"): st.markdown(prompt)
    result = agent.handle(prompt, student_id)
    with st.chat_message("assistant"):
        st.markdown(result["answer"])
        with st.expander("Trace details (for assignment evaluation)"):
            st.json(result["trace"])
    st.session_state.messages.append({"role":"assistant","content":result["answer"]})
    st.rerun()

pending = agent.get_pending_approvals(student_id)
if pending:
    st.divider()
    st.subheader("Human approval queue")
    st.write("Sensitive changes do not execute until approved.")
    for item in pending:
        st.write(f"Request **{item['request_id']}**: {item['action']} — {item['summary']}")
        c1,c2 = st.columns(2)
        if c1.button("Approve", key=f"approve_{item['request_id']}"):
            outcome=agent.decide_approval(item["request_id"], student_id, True)
            st.success(outcome); st.rerun()
        if c2.button("Reject", key=f"reject_{item['request_id']}"):
            outcome=agent.decide_approval(item["request_id"], student_id, False)
            st.warning(outcome); st.rerun()

with st.expander("Assignment checklist"):
    st.markdown("""
    - **Agent loop:** routes a question to a tool, policy retrieval, memory, or direct answer.
    - **Tools:** fee status, scholarship status, support ticket, and profile-change request.
    - **Retrieval:** returns only matching policy chunks.
    - **Memory:** saves useful preferences/programme only; passwords and OTPs are never saved.
    - **Assignment 2 controls:** student-scoped access checks, approval gate, and JSONL audit log.
    - **Evaluation:** run `python evaluate.py` in the terminal.
    """)
