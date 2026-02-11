import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="LMS Admin (Link Mode)", layout="wide")

# --- 1. SETUP & AUTH ---
# Check for secrets
if "firebase" not in st.secrets:
    st.error("Secrets not found. Please add [firebase] to Streamlit Secrets.")
    st.stop()

# Connect to Firestore (No Storage Bucket needed for this version)
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error(f"Failed to connect to Database: {e}")
    st.stop()

# --- 2. HELPER FUNCTIONS ---

def get_metadata_options(field_name):
    """Fetches the list of options (Courses, Boards, etc.) from Firestore"""
    try:
        doc_ref = db.collection('lms_metadata').document('structure')
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return data.get(field_name, [])
        return []
    except:
        return []

def hierarchy_selectors(key_suffix):
    """
    Generates the 6 Dropdowns for Course Structure.
    'key_suffix' ensures widgets in different tabs have unique IDs.
    """
    st.markdown("#### 1. Select Hierarchy")
    col1, col2, col3 = st.columns(3)
    
    # Fetch options dynamically
    courses = ["Select"] + get_metadata_options("courses")
    boards = ["Select"] + get_metadata_options("boards")
    years = ["Select"] + get_metadata_options("years")
    papers = ["Select"] + get_metadata_options("papers")
    blocks = ["Select"] + get_metadata_options("blocks")
    topics = ["Select"] + get_metadata_options("topics")

    # We add 'key=...' to every widget so Streamlit knows they are different
    with col1:
        course = st.selectbox("Course", options=courses, key=f"course_{key_suffix}")
        board = st.selectbox("Board/Univ", options=boards, key=f"board_{key_suffix}")
    with col2:
        year = st.selectbox("Year/Sem", options=years, key=f"year_{key_suffix}")
        paper = st.selectbox("Paper Name", options=papers, key=f"paper_{key_suffix}")
    with col3:
        block = st.selectbox("Block/Part", options=blocks, key=f"block_{key_suffix}")
        topic = st.selectbox("Topic", options=topics, key=f"topic_{key_suffix}")
    
    # Validation
    if "Select" in [course, board, year, paper, block, topic]:
        st.warning("⚠️ Please select all 6 hierarchy fields to proceed.")
        return None
        
    return {
        "course": course, "board": board, "year": year, 
        "paper": paper, "block": block, "topic": topic
    }

# --- 3. MAIN ADMIN INTERFACE ---
st.title("🛠️ LMS Admin (Link Mode)")

# SESSION STATE FOR LOGIN
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# LOGIN SCREEN
if not st.session_state.admin_logged_in:
    password = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if password == "admin123":  # Change this later!
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("Incorrect Password")
    st.stop()  # Stops the app here if not logged in

# --- APP CONTENT (Only runs if logged in) ---

if st.button("Logout"):
    st.session_state.admin_logged_in = False
    st.rerun()

st.success("✅ Logged In as Admin")

tab1, tab2, tab3, tab4 = st.tabs(["📄 PDF Links", "❓ Q&A Database", "☑️ MCQs", "⚙️ Manage Dropdowns"])

# --- TAB 1: STATIC PDFs (Google Drive Links) ---
with tab1:
    st.header("Add Notes/Assignments")
    st.info("Paste the Google Drive 'Share' link for your PDF here.")
    
    # PASS UNIQUE KEY 'tab1'
    hierarchy = hierarchy_selectors(key_suffix="tab1")
    
    st.markdown("#### 2. Resource Details")
    res_type = st.selectbox("Resource Type", ["Theory Note", "Assignments", "Derivations", "Problems"], key="res_type_tab1")
    title = st.text_input("Title (e.g., 'Unit 1: Hamiltonian Dynamics')", key="title_tab1")
    link = st.text_input("Paste Google Drive Link", key="link_tab1")
    
    if st.button("Save Resource Link", key="btn_save_tab1"):
        if hierarchy and title and link:
            data = hierarchy.copy()
            data.update({
                "type": res_type, 
                "title": title, 
                "file_url": link,
                "is_drive_link": True
            })
            db.collection('lms_static_files').add(data)
            st.success(f"✅ Saved: {title}")

# --- TAB 2: SEARCHABLE Q&A (SAQs/PYQs) ---
with tab2:
    st.header("Add Searchable Questions")
    st.info("Students will search for these. You must type the answer here.")
    
    # PASS UNIQUE KEY 'tab2'
    hierarchy = hierarchy_selectors(key_suffix="tab2")
    
    st.markdown("#### 2. Q&A Entry")
    qa_type = st.selectbox("Q&A Type", ["SAQs", "PYQs", "Terminal Questions"], key="qa_type_tab2")
    
    # The SEARCHABLE text
    question_text = st.text_area("Question Text", placeholder="Type the exact question here...", key="q_text_tab2")
    
    # The ANSWER (LaTeX)
    st.markdown("##### Answer (LaTeX Supported)")
    answer_latex = st.text_area("Answer", height=150, placeholder="Use $E=mc^2$ for equations.", key="ans_latex_tab2")
    if answer_latex:
        st.markdown("**Preview:**")
        st.markdown(answer_latex)
        
    # Optional Image Link
    image_link = st.text_input("Explanation Image URL (Optional)", placeholder="Paste image link if any", key="img_link_tab2")
    
    if st.button("Save Q&A", key="btn_save_tab2"):
        if hierarchy and question_text and answer_latex:
            data = hierarchy.copy()
            data.update({
                "type": qa_type,
                "question_text": question_text, # This is what we search!
                "answer_latex": answer_latex,
                "image_url": image_link
            })
            db.collection('lms_qa_database').add(data)
            st.success("✅ Q&A Saved to Database!")

# --- TAB 3: MCQs ---
with tab3:
    st.header("Add Multiple Choice Questions")
    
    # PASS UNIQUE KEY 'tab3'
    hierarchy = hierarchy_selectors(key_suffix="tab3")

    st.markdown("#### 2. MCQ Details")
    mcq_question = st.text_area("Question Stem", key="mcq_q_tab3")
    
    c1, c2 = st.columns(2)
    with c1:
        opt_a = st.text_input("Option A", key="opt_a")
        opt_b = st.text_input("Option B", key="opt_b")
    with c2:
        opt_c = st.text_input("Option C", key="opt_c")
        opt_d = st.text_input("Option D", key="opt_d")
        
    correct = st.selectbox("Correct Key", ["A", "B", "C", "D"], key="correct_key")
    explanation = st.text_area("Explanation (LaTeX allowed)", key="mcq_expl")
    
    if st.button("Save MCQ", key="btn_save_mcq"):
        if hierarchy and mcq_question and opt_a:
                data = hierarchy.copy()
                data.update({
                    "question": mcq_question,
                    "options": {"A": opt_a, "B": opt_b, "C": opt_c, "D": opt_d},
                    "correct_key": correct,
                    "explanation_latex": explanation
                })
                db.collection('lms_mcqs').add(data)
                st.success("✅ MCQ Saved!")

# --- TAB 4: MANAGE STRUCTURE (The Dropdowns) ---
with tab4:
    st.header("⚙️ Configure Dropdowns")
    st.warning("You must add items here first, or the dropdowns in other tabs will be empty!")
    
    # Get current structure
    doc_ref = db.collection('lms_metadata').document('structure')
    struct_doc = doc_ref.get()
    current_data = struct_doc.to_dict() if struct_doc.exists else {}
    
    col1, col2 = st.columns(2)
    
    # Helper to add items
    def add_item(category, label):
        new_val = st.text_input(f"Add New {label}", key=f"input_{category}")
        if st.button(f"Save {label}", key=f"btn_{category}"):
            current_list = current_data.get(category, [])
            if new_val and new_val not in current_list:
                current_list.append(new_val)
                doc_ref.set({category: current_list}, merge=True)
                st.success(f"Added {new_val}")
                st.rerun()
        with st.expander(f"View Current {label}s"):
            st.write(current_data.get(category, []))

    with col1:
        add_item("courses", "Course")
        add_item("boards", "Board/Univ")
        add_item("years", "Year/Sem")
    
    with col2:
        add_item("papers", "Paper Name")
        add_item("blocks", "Block/Part")
        add_item("topics", "Topic")
