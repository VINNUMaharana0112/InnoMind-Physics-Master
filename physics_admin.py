import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="Admin - Physics Master")

# Connect to Firebase
if not firebase_admin._apps:
    key_dict = st.secrets["firebase"]
    cred = credentials.Certificate(dict(key_dict))
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Simple Admin Password (Hardcoded for simplicity, or use secrets)
ADMIN_PASS = st.secrets.get("ADMIN_PASSWORD", "admin123") # Add to secrets.toml

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 Admin Login")
    pwd = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if pwd == ADMIN_PASS:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("Wrong password")

else:
    st.title("Admin Dashboard - Physics Master")
    
    tab1, tab2 = st.tabs(["💰 Payment Approvals", "📚 Add Resources"])
    
    with tab1:
        st.subheader("Pending Approvals")
        # Fetch users who have submitted payment but are not approved
        users_ref = db.collection('physics_users')
        pending_users = users_ref.where('payment_status', '==', 'submitted').stream()
        
        found = False
        for user in pending_users:
            found = True
            u_data = user.to_dict()
            with st.container(border=True):
                col1, col2, col3 = st.columns([2,2,1])
                with col1:
                    st.write(f"**Name:** {u_data['name']}")
                    st.write(f"**Email:** {u_data['email']}")
                with col2:
                    st.write(f"**Txn ID:** {u_data.get('transaction_id', 'N/A')}")
                    st.write(f"**Phone:** {u_data.get('phone', 'N/A')}")
                with col3:
                    if st.button(f"Approve", key=f"app_{user.id}"):
                        users_ref.document(user.id).update({'payment_status': 'approved'})
                        st.success(f"Approved {u_data['name']}")
                        st.rerun()
                    if st.button(f"Reject", key=f"rej_{user.id}"):
                        users_ref.document(user.id).update({'payment_status': 'pending'}) # Reset to pending so they can try again
                        st.warning("Rejected/Reset")
                        st.rerun()
        
        if not found:
            st.info("No pending payment approvals.")

        st.divider()
        st.subheader("All Users")
        if st.checkbox("Show All Users"):
            all_users = users_ref.stream()
            for u in all_users:
                d = u.to_dict()
                st.text(f"{d['name']} - {d['email']} - Status: {d.get('payment_status')}")

    with tab2:
        st.subheader("Upload Study Material")
        # Simple text/link uploader for now
        res_title = st.text_input("Title (e.g., Quantum Mechanics Unit 1)")
        res_cat = st.selectbox("Category", ["Notes", "Derivations", "SAQs", "Problems"])
        res_desc = st.text_area("Description")
        res_link = st.text_input("Google Drive/PDF Link (Optional)")
        res_content = st.text_area("Direct Text/LaTeX Content (Optional)")
        
        if st.button("Add Resource"):
            db.collection('physics_resources').add({
                'title': res_title,
                'category': res_cat,
                'description': res_desc,
                'link': res_link,
                'content': res_content,
                'date': firestore.SERVER_TIMESTAMP
            })
            st.success("Resource Added!")