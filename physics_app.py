import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from PIL import Image

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="InnoMind LMS", page_icon="⚛️", layout="wide")

# --- DEBUG CONNECTION BLOCK ---
if "firebase" not in st.secrets:
    st.error("Secrets not found. Please add [firebase] to Streamlit Secrets.")
    st.stop()

# Connect to Firestore
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error(f"Failed to connect to Database: {e}")

# Connect to Gemini (Optional AI Fallback)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. HELPER FUNCTIONS ---

def get_metadata_options(field_name):
    """Fetches dropdown options from Firestore"""
    try:
        doc = db.collection('lms_metadata').document('structure').get()
        if doc.exists:
            return ["Select"] + doc.to_dict().get(field_name, [])
        return ["Select"]
    except:
        return ["Select"]

def get_ai_solution(question_text):
    """Fallback: Asks Gemini if answer is not in DB"""
    try:
        prompt = f"Solve this physics question in detail using LaTeX for math: {question_text}"
        response = model.generate_content(prompt)
        return response.text
    except:
        return "AI Service Unavailable."

# --- 3. MAIN APPLICATION ---

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# LOGIN SCREEN
if not st.session_state.logged_in:
    st.title("🎓 InnoMind Digital Campus")
    
    tab1, tab2 = st.tabs(["Student Login", "Guest Access"])
    
    with tab1:
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            # Simple check (You can upgrade this to real auth later)
            users = db.collection('physics_users').where('email', '==', email).where('password', '==', pwd).stream()
            if len(list(users)) > 0:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid Credentials")
    
    with tab2:
        st.info("Guest access allows viewing structure but limits content.")
        if st.button("Enter as Guest"):
            st.session_state.logged_in = True
            st.rerun()

else:
    # --- LOGGED IN DASHBOARD ---
    
    # SIDEBAR: THE HIERARCHY SELECTOR
    st.sidebar.title("📚 Course Navigator")
    
    # 1. Course Selection
    course = st.sidebar.selectbox("1. Course", get_metadata_options("courses"))
    board = st.sidebar.selectbox("2. Board/University", get_metadata_options("boards"))
    year = st.sidebar.selectbox("3. Year/Semester", get_metadata_options("years"))
    paper = st.sidebar.selectbox("4. Paper Name", get_metadata_options("papers"))
    block = st.sidebar.selectbox("5. Block/Part", get_metadata_options("blocks"))
    topic = st.sidebar.selectbox("6. Topic", get_metadata_options("topics"))
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # MAIN CONTENT AREA
    st.title(f"{topic if topic != 'Select' else 'Welcome to InnoMind'}")
    
    if "Select" in [course, board, year, paper, block, topic]:
        st.info("👈 Please select all options in the Sidebar to access content.")
        st.image("https://cdn.dribbble.com/users/118712/screenshots/3736506/books-stack.png", width=300)
    else:
        # FILTER: Show Content Types
        resource_type = st.radio("Select Resource Type:", 
            ["📖 Theory Notes", "📝 Assignments", "⚗️ Derivations", "🧮 Problems", 
             "❓ SAQs/PYQs (Search)", "☑️ MCQs (Quiz)"], 
            horizontal=True)

        st.markdown("---")

        # --- LOGIC 1: STATIC PDF FILES ---
        if resource_type in ["📖 Theory Notes", "📝 Assignments", "⚗️ Derivations", "🧮 Problems"]:
            # Map friendly name to DB name
            db_type_map = {
                "📖 Theory Notes": "Theory Note",
                "📝 Assignments": "Assignments",
                "⚗️ Derivations": "Derivations",
                "🧮 Problems": "Problems"
            }
            db_type = db_type_map[resource_type]
            
            st.subheader(f"{resource_type} for {topic}")
            
            # Query Firestore
            docs = db.collection('lms_static_files')\
                .where('topic', '==', topic)\
                .where('type', '==', db_type).stream()
            
            found = False
            for doc in docs:
                found = True
                data = doc.to_dict()
                with st.expander(f"📄 {data.get('title', 'Untitled')}"):
                    if data.get('is_drive_link'):
                        st.markdown(f"**[Click to Open PDF]({data['file_url']})**")
                    else:
                        st.write("File format not supported.")
            
            if not found:
                st.warning("No files uploaded for this section yet.")

        # --- LOGIC 2: SEARCHABLE DATABASE (SAQs, PYQs) ---
        elif resource_type == "❓ SAQs/PYQs (Search)":
            st.subheader("Search Question Bank")
            
            q_type = st.selectbox("Filter By:", ["SAQs", "PYQs", "Terminal Questions"])
            
            search_query = st.text_input("🔍 Search Question (Type keyword like 'Hamiltonian')", "")
            
            if search_query:
                # 1. Fetch ALL questions for this topic & type
                docs = db.collection('lms_qa_database')\
                    .where('topic', '==', topic)\
                    .where('type', '==', q_type).stream()
                
                results_found = False
                for doc in docs:
                    data = doc.to_dict()
                    # 2. Python-side "Contains" Search (Simple fuzzy match)
                    if search_query.lower() in data['question_text'].lower():
                        results_found = True
                        with st.container():
                            st.markdown(f"**Q:** {data['question_text']}")
                            with st.expander("Show Answer"):
                                st.latex(data['answer_latex'])
                                if data.get('image_url'):
                                    st.image(data['image_url'])
                            st.markdown("---")
                
                if not results_found:
                    st.warning("Question not found in Database.")
                    # AI FALLBACK
                    if st.button("🤖 Ask AI to Solve Instead?"):
                        with st.spinner("Generating Solution..."):
                            sol = get_ai_solution(search_query)
                            st.markdown("### AI Generated Solution:")
                            st.write(sol)

        # --- LOGIC 3: MCQs ---
        elif resource_type == "☑️ MCQs (Quiz)":
            st.subheader("Interactive Quiz")
            
            docs = db.collection('lms_mcqs')\
                .where('topic', '==', topic).stream()
            
            count = 0
            for doc in docs:
                count += 1
                data = doc.to_dict()
                st.markdown(f"**Q{count}. {data['question']}**")
                
                # Radio buttons for options
                opts = data['options']
                choice = st.radio(f"Select Answer for Q{count}", 
                                  [opts['A'], opts['B'], opts['C'], opts['D']], 
                                  key=doc.id)
                
                # Check Answer Logic
                if st.button(f"Check Answer Q{count}", key=f"btn_{doc.id}"):
                    # Map selection back to Key (A, B, C, D)
                    reverse_map = {v: k for k, v in opts.items()}
                    user_key = reverse_map[choice]
                    
                    if user_key == data['correct_key']:
                        st.success("✅ Correct!")
                    else:
                        st.error(f"❌ Incorrect. Correct was {data['correct_key']}")
                    
                    st.info(f"**Explanation:**")
                    st.latex(data['explanation_latex'])
                st.markdown("---")
            
            if count == 0:
                st.warning("No MCQs added for this topic yet.")
