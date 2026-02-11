import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="LMS Admin (Drive Mode)", layout="wide")

# --- 1. SETUP & AUTH ---
if "firebase" not in st.secrets:
    st.error("Secrets not found. Please add [firebase] to Streamlit Secrets.")
    st.stop()

# Connect to Firestore ONLY (No Storage Bucket needed)
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. HELPER FUNCTIONS ---

def get_metadata_options(field_name):
    """Fetches the list of options (Courses, Boards, etc.) from Firestore"""
    doc_ref = db.collection('lms_metadata').document('structure')
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        return data.get(field_name, [])
    return []

def hierarchy_selectors():
    """Generates the 6 Dropdowns for Course Structure"""
    st.markdown("#### 1. Select Hierarchy")
    col1, col2, col3 = st.columns(3)
    
    # Fetch options dynamically
    courses = ["Select"] + get_metadata_options("courses")
    boards = ["Select"] + get_metadata_options("boards")
    years = ["Select"] + get_metadata_options("years")
    papers = ["Select"] + get_metadata_options("papers")
    blocks = ["Select"] + get_metadata_options("blocks")
    topics = ["Select"] + get_metadata_options("topics")

    with col1:
        course = st.selectbox("Course", options=courses)
        board = st.selectbox("Board/Univ", options=boards)
    with col2:
        year = st.selectbox("Year/Sem", options=years)
        paper = st.selectbox("Paper Name", options=papers)
    with col3:
        block = st.selectbox("Block/Part", options=blocks)
        topic = st.selectbox("Topic", options=topics)
    
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

password = st.text_input("Admin Password", type="password")
if password == "admin123":  # Change this later!
    st.success("Logged In")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Upload PDF Links", "❓ Upload Q&A (Searchable)", "☑️ Upload MCQs", "⚙️ Manage Dropdowns"])

    # --- TAB 1: STATIC PDFs (Google Drive Links) ---
    with tab1:
        st.header("Add Notes/Assignments")
        st.info("Paste the Google Drive 'Share' link for your PDF here.")
        
        hierarchy = hierarchy_selectors()
        
        st.markdown("#### 2. Resource Details")
        res_type = st.selectbox("Resource Type", ["Theory Note", "Assignments", "Derivations", "Problems"])
        title = st.text_input("Title (e.g., 'Unit 1: Hamiltonian Dynamics')")
        link = st.text_input("Paste Google Drive Link")
        
        if st.button("Save Resource Link"):
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
        
        hierarchy = hierarchy_selectors()
        
        st.markdown("#### 2. Q&A Entry")
        qa_type = st.selectbox("Q&A Type", ["SAQs", "PYQs", "Terminal Questions"])
        
        # The SEARCHABLE text
        question_text = st.text_area("Question Text", placeholder="Type the exact question here...")
        
        # The ANSWER (LaTeX)
        st.markdown("##### Answer (LaTeX Supported)")
        answer_latex = st.text_area("Answer", height=150, placeholder="Use $E=mc^2$ for equations.")
        if answer_latex:
            st.markdown("**Preview:**")
            st.markdown(answer_latex)
            
        # Optional Image Link
        image_link = st.text_input("Explanation Image URL (Optional)", placeholder="Paste image link if any")
        
        if st.button("Save Q&A"):
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
        hierarchy = hierarchy_selectors()

        st.markdown("#### 2. MCQ Details")
        mcq_question = st.text_area("Question Stem")
        
        c1, c2 = st.columns(2)
        with c1:
            opt_a = st.text_input("Option A")
            opt_b = st.text_input("Option B")
        with c2:
            opt_c = st.text_input("Option C")
            opt_d = st.text_input("Option D")
            
        correct = st.selectbox("Correct Key", ["A", "B", "C", "D"])
        explanation = st.text_area("Explanation (LaTeX allowed)")
        
        if st.button("Save MCQ"):
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
            new_val = st.text_input(f"Add New {label}", key=category)
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
