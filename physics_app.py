import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from PIL import Image

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="InnoMind Physics Master", layout="wide")

# Connect to Gemini AI
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("⚠️ AI Key Missing. Please add GOOGLE_API_KEY to secrets.")

# Connect to Firebase
if not firebase_admin._apps:
    key_dict = st.secrets["firebase"]
    cred = credentials.Certificate(dict(key_dict))
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- 2. SESSION STATE MANAGEMENT ---
if 'user_doc' not in st.session_state:
    st.session_state.user_doc = None
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 3. HELPER FUNCTIONS ---
def login_user(email, password):
    users_ref = db.collection('physics_users') # New Collection for Physics App
    query = users_ref.where('email', '==', email).where('password', '==', password).stream()
    for doc in query:
        return doc
    return None

def register_user(email, password, name, phone):
    users_ref = db.collection('physics_users')
    # Check if exists
    if len(list(users_ref.where('email', '==', email).stream())) > 0:
        return False
    
    # Create new user with "pending" status
    new_user = {
        'name': name,
        'email': email,
        'password': password,
        'phone': phone,
        'payment_status': 'pending',  # Default is locked
        'joined_date': firestore.SERVER_TIMESTAMP
    }
    users_ref.add(new_user)
    return True

def get_ai_solution(prompt, image=None):
    """Sends physics question to Gemini AI"""
    system_prompt = """
    You are an expert Physics Professor for M.Sc. students. 
    Solve the problem step-by-step. 
    Use LaTeX for all mathematical equations (enclose in $ signs). 
    Explain the physical concepts clearly.
    """
    try:
        if image:
            response = model.generate_content([system_prompt, prompt, image])
        else:
            response = model.generate_content([system_prompt, prompt])
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# --- 4. MAIN APP LOGIC ---

# sidebar for Login/Signup
if not st.session_state.logged_in:
    st.title("⚛️ InnoMind Physics Master")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = login_user(email, password)
            if user:
                st.session_state.user_doc = user.to_dict()
                st.session_state.user_id = user.id
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid email or password.")
                
    with tab2:
        new_name = st.text_input("Full Name")
        new_email = st.text_input("Email Address")
        new_phone = st.text_input("Phone Number")
        new_pass = st.text_input("Create Password", type="password")
        if st.button("Create Account"):
            if register_user(new_email, new_pass, new_name, new_phone):
                st.success("Account created! Please Login.")
            else:
                st.error("Email already exists.")

else:
    # USER IS LOGGED IN
    user_data = st.session_state.user_doc
    
    # --- CHECK PAYMENT STATUS ---
    if user_data.get('payment_status') != 'approved':
        st.warning("🔒 Access Restricted")
        st.info(f"Welcome, {user_data['name']}! To access the Physics Solver and Exams, please complete the one-time payment.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Step 1: Pay Fees")
            st.markdown("**Amount: ₹999 (Lifetime)**") # You can change price
            # REPLACE WITH YOUR ACTUAL QR CODE IMAGE LINK OR UPLOAD
            st.image("https://upload.wikimedia.org/wikipedia/commons/d/d0/QR_code_for_mobile_English_Wikipedia.svg", caption="Scan to Pay via UPI", width=200)
            st.markdown("**UPI ID:** your-upi-id@bank") 
            
        with col2:
            st.markdown("### Step 2: Verify")
            st.write("After paying, enter the Transaction ID below. Admin will approve within 24 hours.")
            txn_id = st.text_input("Transaction ID / Reference No.")
            if st.button("Submit for Approval"):
                # Update user doc with txn id
                db.collection('physics_users').document(st.session_state.user_id).update({
                    'transaction_id': txn_id,
                    'payment_status': 'submitted'
                })
                st.success("Submitted! Please wait for Admin approval.")
                
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
            
    else:
        # --- MAIN APP (PAID USER) ---
        st.sidebar.title(f"👨‍🎓 {user_data['name']}")
        st.sidebar.success("✅ Premium Member")
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()

        menu = st.sidebar.radio("Menu", ["🤖 AI Physics Solver", "📝 Exam Portal", "📚 Resources"])

        if menu == "🤖 AI Physics Solver":
            st.header("💡 Instant Physics Solutions")
            st.markdown("Ask any question regarding **M.Sc. Physics, NET, GATE**, or specific derivations.")
            
            input_method = st.radio("Input Method:", ["Type Question", "Upload Image"])
            
            user_question = ""
            user_image = None
            
            if input_method == "Type Question":
                user_question = st.text_area("Type your question here (LaTeX supported):", height=150)
            else:
                uploaded_file = st.file_uploader("Upload an image of the problem", type=["jpg", "png", "jpeg"])
                if uploaded_file:
                    user_image = Image.open(uploaded_file)
                    st.image(user_image, caption="Uploaded Problem", use_container_width=True)
                    user_question = st.text_input("Add any specific instructions (optional):")

            if st.button("Get Solution"):
                if user_question or user_image:
                    with st.spinner("Analyzing Physics concepts..."):
                        # Call AI
                        if input_method == "Upload Image" and user_image:
                            solution = get_ai_solution(user_question if user_question else "Solve this", user_image)
                        else:
                            solution = get_ai_solution(user_question)
                        
                        st.markdown("### 🎓 Detailed Solution:")
                        st.markdown(solution) # Markdown renders LaTeX automatically
                        
                        # Save query to history (optional)
                else:
                    st.warning("Please provide a question or image.")

        elif menu == "📝 Exam Portal":
            st.header("NET/GATE Mock Tests")
            st.info("No active tests scheduled at the moment.")
            # You can paste your previous Exam logic here later

        elif menu == "📚 Resources":
            st.header("Study Material")
            st.write("Access your Notes, SAQs, and Derivations here.")
            # This fetches from a 'resources' collection you will fill as Admin
            docs = db.collection('physics_resources').stream()
            for doc in docs:
                res = doc.to_dict()
                with st.expander(f"📄 {res['title']} ({res['category']})"):
                    st.write(res['description'])
                    if 'link' in res:
                        st.markdown(f"[Download/View PDF]({res['link']})")
                    if 'content' in res:
                        st.markdown(res['content'])