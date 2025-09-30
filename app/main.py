import streamlit as st
import os
from datetime import date, datetime
from database.models import get_database, Person, Document
from utils.date_utils import get_expiry_status, days_until_expiry, format_date_friendly
from utils.photo_handler import save_uploaded_photo, get_photo_path, photo_exists

# Page configuration
st.set_page_config(
    page_title="Family Passport Manager",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Initialize database
db = get_database()

# CSS for mobile-first responsive design
def load_css():
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }

    .status-green { background-color: #d4edda; color: #155724; padding: 0.5rem; border-radius: 0.25rem; }
    .status-yellow { background-color: #fff3cd; color: #856404; padding: 0.5rem; border-radius: 0.25rem; }
    .status-orange { background-color: #ffeaa7; color: #d68910; padding: 0.5rem; border-radius: 0.25rem; }
    .status-red { background-color: #f8d7da; color: #721c24; padding: 0.5rem; border-radius: 0.25rem; }
    .status-gray { background-color: #f8f9fa; color: #6c757d; padding: 0.5rem; border-radius: 0.25rem; }

    .document-card {
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: white;
    }

    .person-card {
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: #f8f9fa;
    }

    @media (max-width: 768px) {
        .stSelectbox label, .stTextInput label, .stDateInput label {
            font-size: 0.9rem;
        }
        .stButton button {
            width: 100%;
            margin-bottom: 0.5rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def render_status_badge(status_color: str, status_text: str):
    """Render a status badge with color"""
    st.markdown(f'<div class="status-{status_color}">{status_text}</div>', unsafe_allow_html=True)

def dashboard_tab():
    """Main dashboard showing document status overview"""
    st.markdown('<h1 class="main-header">📘 Family Passport Manager</h1>', unsafe_allow_html=True)

    # Get all documents and people
    documents = db.get_documents()
    people = db.get_people()

    if not people:
        st.warning("👥 No family members added yet. Go to the Family tab to add people.")
        return

    if not documents:
        st.info("📄 No documents added yet. Go to the Documents tab to add your first document.")
        return

    # Create person lookup
    person_lookup = {p.id: p.name for p in people}

    # Group documents by urgency
    urgent_docs = []
    warning_docs = []
    current_docs = []

    for doc in documents:
        status_color, status_text = get_expiry_status(doc.expiry_date)
        doc_data = {
            'document': doc,
            'holder_name': person_lookup.get(doc.holder_id, "Unknown"),
            'status_color': status_color,
            'status_text': status_text,
            'days_left': days_until_expiry(doc.expiry_date)
        }

        if status_color == 'red':
            urgent_docs.append(doc_data)
        elif status_color in ['orange', 'yellow']:
            warning_docs.append(doc_data)
        else:
            current_docs.append(doc_data)

    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Family Members", len(people))
    with col2:
        st.metric("📄 Total Documents", len(documents))
    with col3:
        st.metric("🚨 Urgent", len(urgent_docs))
    with col4:
        st.metric("⚠️ Needs Attention", len(warning_docs))

    # Display documents by urgency
    if urgent_docs:
        st.markdown("### 🚨 Urgent Documents")
        for doc_data in urgent_docs:
            render_document_card(doc_data)

    if warning_docs:
        st.markdown("### ⚠️ Documents Needing Attention")
        for doc_data in warning_docs:
            render_document_card(doc_data)

    if current_docs:
        st.markdown("### ✅ Current Documents")
        for doc_data in current_docs:
            render_document_card(doc_data)

def render_document_card(doc_data):
    """Render a document card with status"""
    doc = doc_data['document']

    with st.container():
        st.markdown('<div class="document-card">', unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            st.write(f"**{doc.type.replace('_', ' ').title()}** - {doc.country}")
            st.write(f"👤 {doc_data['holder_name']}")

        with col2:
            st.write(f"📅 Expires: {format_date_friendly(doc.expiry_date)}")
            render_status_badge(doc_data['status_color'], doc_data['status_text'])

        with col3:
            if st.button("✏️ Edit", key=f"edit_{doc.id}"):
                st.session_state['edit_document_id'] = doc.id
                st.session_state['active_tab'] = 'Documents'
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

def family_tab():
    """Family management tab"""
    st.markdown("## 👥 Family Members")

    # Add new person form
    with st.expander("➕ Add New Family Member"):
        with st.form("add_person"):
            name = st.text_input("Full Name*")
            role = st.selectbox("Role*", ["parent", "child"])
            birth_date = st.date_input("Birth Date*", max_value=date.today())

            if st.form_submit_button("Add Person"):
                if name and birth_date:
                    person = Person(
                        id=None,
                        name=name,
                        role=role,
                        birth_date=birth_date
                    )
                    db.add_person(person)
                    st.success(f"✅ Added {name} to family")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields")

    # Display existing people
    people = db.get_people()

    if people:
        for person in people:
            with st.container():
                st.markdown('<div class="person-card">', unsafe_allow_html=True)

                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.write(f"**{person.name}**")
                    st.write(f"Role: {person.role.title()}")

                with col2:
                    st.write(f"🎂 Born: {format_date_friendly(person.birth_date)}")

                    # Show document count
                    person_docs = db.get_documents(person.id)
                    st.write(f"📄 Documents: {len(person_docs)}")

                with col3:
                    if st.button("🗑️ Delete", key=f"delete_person_{person.id}"):
                        db.delete_person(person.id)
                        st.success(f"Deleted {person.name}")
                        st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No family members added yet. Add your first family member above.")

def documents_tab():
    """Documents management tab"""
    st.markdown("## 📄 Documents")

    people = db.get_people()
    if not people:
        st.warning("👥 Please add family members first in the Family tab.")
        return

    # Check if editing existing document
    edit_doc_id = st.session_state.get('edit_document_id')
    edit_doc = None
    if edit_doc_id:
        edit_doc = db.get_document(edit_doc_id)
        if not edit_doc:
            st.session_state.pop('edit_document_id', None)

    # Document form
    form_title = "✏️ Edit Document" if edit_doc else "➕ Add New Document"
    with st.expander(form_title, expanded=bool(edit_doc)):
        with st.form("document_form"):
            # Person selection
            person_options = {p.id: f"{p.name} ({p.role})" for p in people}
            default_holder = edit_doc.holder_id if edit_doc else list(person_options.keys())[0]
            holder_id = st.selectbox("Document Holder*",
                                   options=list(person_options.keys()),
                                   format_func=lambda x: person_options[x],
                                   index=list(person_options.keys()).index(default_holder) if default_holder in person_options else 0)

            col1, col2 = st.columns(2)
            with col1:
                doc_type = st.selectbox("Document Type*",
                                      ["passport", "drivers_license", "nexus", "birth_certificate", "other"],
                                      index=["passport", "drivers_license", "nexus", "birth_certificate", "other"].index(edit_doc.type) if edit_doc else 0)
                country = st.text_input("Issuing Country/State*", value=edit_doc.country if edit_doc else "")

            with col2:
                document_number = st.text_input("Document Number*", value=edit_doc.document_number if edit_doc else "")
                status = st.selectbox("Status*",
                                    ["current", "application_submitted", "received_new"],
                                    index=["current", "application_submitted", "received_new"].index(edit_doc.status) if edit_doc else 0)

            col3, col4 = st.columns(2)
            with col3:
                issue_date = st.date_input("Issue Date",
                                         value=edit_doc.issue_date if edit_doc and edit_doc.issue_date else None,
                                         max_value=date.today())
                expiry_date = st.date_input("Expiry Date*",
                                          value=edit_doc.expiry_date if edit_doc else None,
                                          min_value=None if edit_doc else date.today())

            with col4:
                submission_date = st.date_input("Application Submitted Date",
                                              value=edit_doc.submission_date if edit_doc and edit_doc.submission_date else None,
                                              max_value=date.today())
                processing_estimate = st.text_input("Processing Time Estimate",
                                                   value=edit_doc.processing_estimate if edit_doc else "")

            # Photo upload
            st.markdown("📸 **Document Photo**")
            uploaded_file = st.file_uploader("Upload document photo", type=['jpg', 'jpeg', 'png'])

            # Notes
            notes = st.text_area("Notes", value=edit_doc.notes if edit_doc else "", height=100)

            submit_button = st.form_submit_button("Update Document" if edit_doc else "Add Document")

            if submit_button:
                if holder_id and doc_type and country and document_number and expiry_date:
                    # Handle photo upload
                    photo_filename = edit_doc.photo_filename if edit_doc else None
                    if uploaded_file:
                        photo_filename = save_uploaded_photo(uploaded_file)

                    document = Document(
                        id=edit_doc.id if edit_doc else None,
                        holder_id=holder_id,
                        type=doc_type,
                        country=country,
                        document_number=document_number,
                        issue_date=issue_date,
                        expiry_date=expiry_date,
                        status=status,
                        submission_date=submission_date,
                        processing_estimate=processing_estimate,
                        photo_filename=photo_filename,
                        notes=notes
                    )

                    if edit_doc:
                        db.update_document(document)
                        st.success("✅ Document updated successfully")

                        # Update calendar integration if status changed
                        if edit_doc.status != document.status:
                            person = db.get_person(document.holder_id)
                            if person:
                                from integrations.caldav_client import get_caldav_client
                                caldav_client = get_caldav_client()
                                caldav_client.update_renewal_status(document, person)

                        st.session_state.pop('edit_document_id', None)
                    else:
                        doc_id = db.add_document(document)
                        st.success("✅ Document added successfully")

                        # Create initial calendar reminder for new documents
                        person = db.get_person(document.holder_id)
                        if person:
                            from integrations.caldav_client import get_caldav_client
                            caldav_client = get_caldav_client()
                            caldav_client.create_renewal_reminder(document, person)

                    st.rerun()
                else:
                    st.error("Please fill in all required fields")

    # Cancel edit button outside the form
    if edit_doc:
        if st.button("Cancel Edit"):
            st.session_state.pop('edit_document_id', None)
            st.rerun()

    # Display existing documents
    st.markdown("### Current Documents")
    documents = db.get_documents()
    person_lookup = {p.id: p.name for p in people}

    if documents:
        for doc in documents:
            status_color, status_text = get_expiry_status(doc.expiry_date)

            with st.container():
                st.markdown('<div class="document-card">', unsafe_allow_html=True)

                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                with col1:
                    st.write(f"**{doc.type.replace('_', ' ').title()}**")
                    st.write(f"👤 {person_lookup.get(doc.holder_id, 'Unknown')}")
                    st.write(f"🌍 {doc.country}")

                with col2:
                    st.write(f"🔢 {doc.document_number}")
                    st.write(f"📅 Expires: {format_date_friendly(doc.expiry_date)}")
                    render_status_badge(status_color, status_text)

                with col3:
                    if doc.photo_filename and photo_exists(doc.photo_filename):
                        if st.button("📸 View Photo", key=f"photo_{doc.id}"):
                            st.image(get_photo_path(doc.photo_filename), width=300)

                    if doc.notes:
                        st.write(f"📝 {doc.notes[:50]}...")

                with col4:
                    if st.button("✏️ Edit", key=f"edit_doc_{doc.id}"):
                        st.session_state['edit_document_id'] = doc.id
                        st.rerun()

                    if st.button("🗑️ Delete", key=f"delete_doc_{doc.id}"):
                        db.delete_document(doc.id)
                        st.success("Document deleted")
                        st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No documents added yet. Add your first document above.")

def settings_tab():
    """Settings and configuration tab"""
    st.markdown("## ⚙️ Settings")

    # Theme settings
    st.markdown("### 🎨 Theme")
    current_theme = db.get_setting('theme', 'light')
    theme = st.selectbox("Theme", ['light', 'dark'], index=['light', 'dark'].index(current_theme))

    if theme != current_theme:
        db.set_setting('theme', theme)
        st.success("Theme updated")

    # Pushover Integration
    st.markdown("### 📬 Pushover Notifications")
    pushover_config = db.get_setting('pushover', {
        'enabled': False,
        'user_key': '',
        'api_token': '',
        'device': '',
        'sound': 'pushover'
    })

    pushover_enabled = st.checkbox("Enable Pushover Notifications", value=pushover_config.get('enabled', False))

    if pushover_enabled:
        col1, col2 = st.columns(2)
        with col1:
            user_key = st.text_input("User Key*", value=pushover_config.get('user_key', ''), type="password")
            device = st.text_input("Device (optional)", value=pushover_config.get('device', ''))

        with col2:
            api_token = st.text_input("API Token*", value=pushover_config.get('api_token', ''), type="password")
            sound = st.selectbox("Sound", ['pushover', 'bike', 'bugle', 'cashregister', 'classical', 'cosmic'],
                               index=['pushover', 'bike', 'bugle', 'cashregister', 'classical', 'cosmic'].index(pushover_config.get('sound', 'pushover')))

        # Save Pushover config
        new_pushover_config = {
            'enabled': pushover_enabled,
            'user_key': user_key,
            'api_token': api_token,
            'device': device,
            'sound': sound
        }

        if new_pushover_config != pushover_config:
            db.set_setting('pushover', new_pushover_config)
            st.success("Pushover settings saved")
            st.rerun()

        # Test connection
        if user_key and api_token:
            if st.button("🧪 Test Pushover Connection"):
                from integrations.pushover import send_test_notification
                success, message = send_test_notification()
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
    else:
        # Save disabled state
        if pushover_config.get('enabled', False):
            pushover_config['enabled'] = False
            db.set_setting('pushover', pushover_config)
            st.info("Pushover notifications disabled")

    # CalDAV Integration
    st.markdown("### 📅 Calendar Integration (CalDAV)")
    caldav_config = db.get_setting('caldav', {
        'enabled': False,
        'caldav_url': '',
        'username': '',
        'password': '',
        'calendar_name': 'Passport Renewals',
        'auto_discovery': True
    })

    caldav_enabled = st.checkbox("Enable Calendar Integration", value=caldav_config.get('enabled', False))

    if caldav_enabled:
        # Auto-discovery section
        with st.expander("🔍 Auto-Discovery (Nextcloud/Other Servers)"):
            auto_server = st.text_input("Server URL (e.g., https://nextcloud.example.com)", placeholder="https://nextcloud.example.com")
            auto_username = st.text_input("Username for auto-discovery")

            if st.button("🔍 Discover CalDAV URL") and auto_server and auto_username:
                from integrations.caldav_client import discover_caldav_url
                discovered_url = discover_caldav_url(auto_server, auto_username)
                if discovered_url:
                    st.success(f"✅ Discovered CalDAV URL: {discovered_url}")
                    caldav_config['caldav_url'] = discovered_url
                    caldav_config['username'] = auto_username
                    db.set_setting('caldav', caldav_config)
                    st.rerun()
                else:
                    st.error("❌ Could not auto-discover CalDAV URL. Please enter manually below.")

        # Manual configuration
        st.markdown("**Manual Configuration**")
        col1, col2 = st.columns(2)

        with col1:
            caldav_url = st.text_input("CalDAV URL*", value=caldav_config.get('caldav_url', ''),
                                     placeholder="https://nextcloud.example.com/remote.php/dav/calendars/username/")
            username = st.text_input("Username*", value=caldav_config.get('username', ''))

        with col2:
            password = st.text_input("Password*", value=caldav_config.get('password', ''), type="password")
            calendar_name = st.text_input("Calendar Name", value=caldav_config.get('calendar_name', 'Passport Renewals'))

        # Save CalDAV config
        new_caldav_config = {
            'enabled': caldav_enabled,
            'caldav_url': caldav_url,
            'username': username,
            'password': password,
            'calendar_name': calendar_name,
            'auto_discovery': caldav_config.get('auto_discovery', True)
        }

        if new_caldav_config != caldav_config:
            db.set_setting('caldav', new_caldav_config)
            st.success("CalDAV settings saved")
            st.rerun()

        # Test connection
        if caldav_url and username and password:
            if st.button("🧪 Test CalDAV Connection"):
                from integrations.caldav_client import test_caldav_connection
                success, message = test_caldav_connection()
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
    else:
        # Save disabled state
        if caldav_config.get('enabled', False):
            caldav_config['enabled'] = False
            db.set_setting('caldav', caldav_config)
            st.info("Calendar integration disabled")

    # Notification Settings
    st.markdown("### 🔔 Notification Settings")

    col1, col2 = st.columns(2)
    with col1:
        daily_summary = st.checkbox("Daily Summary Notifications", value=db.get_setting('daily_summary_enabled', True))
        db.set_setting('daily_summary_enabled', daily_summary)

    with col2:
        if st.button("🔔 Test Notifications Now"):
            from utils.notification_scheduler import get_notification_scheduler
            scheduler = get_notification_scheduler()
            result = scheduler.check_now()

            if result['success']:
                st.success(f"✅ Sent {result['notifications_sent']} notifications. "
                          f"Found {result['urgent_count']} urgent and {result['warning_count']} warning documents.")
            else:
                st.error("❌ Notification test failed")

    # Notification Schedule
    st.markdown("**Notification Schedule (Days Before Expiry)**")
    current_schedule = db.get_setting('notification_schedule', [180, 90, 30, 14, 7, 1])
    schedule_text = st.text_input("Notification Days", value=", ".join(map(str, current_schedule)))

    try:
        new_schedule = [int(x.strip()) for x in schedule_text.split(",")]
        if new_schedule != current_schedule:
            db.set_setting('notification_schedule', new_schedule)
            st.success("Notification schedule updated")
    except ValueError:
        st.error("Please enter valid numbers separated by commas")

    # Integration Status
    st.markdown("### 📊 Integration Status")

    # Get current status
    from integrations.pushover import get_pushover_client
    from integrations.caldav_client import get_caldav_client
    from utils.notification_scheduler import get_notification_scheduler

    pushover_client = get_pushover_client()
    caldav_client = get_caldav_client()
    scheduler = get_notification_scheduler()

    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:
        st.metric("📬 Pushover", "✅ Enabled" if pushover_client.enabled else "❌ Disabled")

    with status_col2:
        st.metric("📅 CalDAV", "✅ Enabled" if caldav_client.enabled else "❌ Disabled")

    with status_col3:
        scheduler_status = scheduler.get_status()
        st.metric("🔔 Scheduler", "✅ Running" if scheduler_status['running'] else "❌ Stopped")

    # Demo data management
    st.markdown("### 🧪 Demo Data")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Load Demo Data"):
            load_demo_data()
            st.success("Demo data loaded")
            st.rerun()

    with col2:
        if st.button("🗑️ Clear All Data"):
            if st.checkbox("I understand this will delete all data"):
                db.clear_all_data()
                st.success("All data cleared")
                st.rerun()

    # Statistics
    st.markdown("### 📊 Statistics")
    people_count = len(db.get_people())
    docs_count = len(db.get_documents())

    st.write(f"👥 Family Members: {people_count}")
    st.write(f"📄 Documents: {docs_count}")

    # Show notification history
    notification_history = db.get_setting('notification_history', {})
    if notification_history:
        st.write(f"🔔 Notifications Sent: {len(notification_history)} documents tracked")

def load_demo_data():
    """Load demo family data as specified in the design doc"""
    from datetime import datetime

    # Clear existing data first
    db.clear_all_data()

    # Add demo people
    demo_people = [
        Person(None, "John Doe", "parent", date(1985, 3, 15)),
        Person(None, "Jane Doe", "parent", date(1987, 7, 22)),
        Person(None, "Sarah Doe", "child", date(2010, 11, 8)),
        Person(None, "Tommy Doe", "child", date(2015, 9, 12))
    ]

    people_ids = {}
    for person in demo_people:
        person_id = db.add_person(person)
        people_ids[person.name] = person_id

    # Add demo documents
    demo_documents = [
        # John's documents - all current
        Document(None, people_ids["John Doe"], "passport", "USA", "123456789",
                date(2024, 5, 15), date(2029, 5, 15), "current"),
        Document(None, people_ids["John Doe"], "drivers_license", "California", "D1234567",
                date(2022, 3, 10), date(2027, 3, 10), "current"),

        # Jane's documents - some expiring soon for demo
        Document(None, people_ids["Jane Doe"], "passport", "Canada", "AB1234567",
                date(2025, 8, 22), date(2030, 8, 22), "current"),
        Document(None, people_ids["Jane Doe"], "nexus", "USA/Canada", "50123456",
                date(2021, 1, 15), date(2026, 1, 15), "current"),

        # Kids' documents - one expiring soon, one in renewal process
        Document(None, people_ids["Sarah Doe"], "passport", "USA", "987654321",
                date(2020, 11, 8), date(2025, 11, 8), "current"),  # Expires soon
        Document(None, people_ids["Tommy Doe"], "passport", "USA", "456789123",
                date(2020, 9, 12), date(2025, 9, 12), "application_submitted",
                date(2024, 8, 1), "6-8 weeks")
    ]

    for doc in demo_documents:
        db.add_document(doc)

def main():
    """Main application"""
    load_css()

    # Initialize session state
    if 'active_tab' not in st.session_state:
        st.session_state['active_tab'] = 'Dashboard'

    # Start notification scheduler on first run
    if 'scheduler_started' not in st.session_state:
        from utils.notification_scheduler import start_notification_scheduler
        start_notification_scheduler()
        st.session_state['scheduler_started'] = True

    # Sidebar navigation
    with st.sidebar:
        st.markdown("## 📘 Passport Manager")

        # Tab selection
        tab = st.radio("Navigation",
                      ['Dashboard', 'Family', 'Documents', 'Settings'],
                      index=['Dashboard', 'Family', 'Documents', 'Settings'].index(st.session_state.get('active_tab', 'Dashboard')))

        # Update active tab
        if tab != st.session_state.get('active_tab'):
            st.session_state['active_tab'] = tab
            # Clear edit state when changing tabs
            if 'edit_document_id' in st.session_state:
                st.session_state.pop('edit_document_id')

        # Quick stats in sidebar
        st.markdown("---")
        people_count = len(db.get_people())
        docs_count = len(db.get_documents())

        st.metric("👥 Family", people_count)
        st.metric("📄 Documents", docs_count)

        # Quick actions
        if people_count == 0:
            st.info("Add family members first")
        elif docs_count == 0:
            st.info("Add documents to get started")

    # Main content area
    if tab == 'Dashboard':
        dashboard_tab()
    elif tab == 'Family':
        family_tab()
    elif tab == 'Documents':
        documents_tab()
    elif tab == 'Settings':
        settings_tab()

if __name__ == "__main__":
    main()