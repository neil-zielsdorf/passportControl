Family Passport Manager - Detailed Design Specification for Claude Code
🎯 Project Overview
We've designed a self-hosted Family Passport Manager - a mobile-first web application for tracking government documents (passports, licenses, NEXUS cards, etc.) with smart expiry notifications and calendar integration. This is specifically built for homelab enthusiasts who want to keep sensitive family data private while having modern notification and workflow features.
🏗️ Architecture & Tech Stack
Core Technology Stack

Frontend: Streamlit (Python web framework) with custom CSS for mobile-first responsive design
Backend: Python 3.12 with SQLite database
Storage: Local file system for document photos
Deployment: Docker containerization with docker-compose
Default Port: 8270 (chosen to avoid common homelab conflicts)

Security Model

Local network only - No public internet exposure required
Tailscale integration - Secure remote access for families
Future WebAuthn support - Biometric authentication (Touch ID, Face ID, Windows Hello)
Encrypted sensitive fields - Document numbers encrypted in SQLite
Local file storage - Photos never leave your server

📱 User Experience Design
Mobile-First Approach

Primary interface: Phone/tablet for quick document updates
Camera integration: Capture passport photos directly in browser
Touch-friendly: Large buttons, swipe gestures, finger-optimized navigation
Responsive breakpoints: Adapts from phone to tablet to desktop
Dark/light themes: Toggle in sidebar, persistent user preference

Family-Centric Workflow

Parent control: Parents manage all family documents (realistic family dynamics)
Role-based access: Parents see everything, kids can see their own documents
Bulk management: Handle multiple family renewals efficiently
Travel planning: See all family document status for trip planning

🗄️ Database Schema
Three Main Tables
People Table
- id (PRIMARY KEY)
- name (TEXT) - Full name
- role (TEXT) - "parent" or "child"  
- birth_date (DATE)
- created_at (TIMESTAMP)

Documents Table
- id (PRIMARY KEY)
- holder_id (FOREIGN KEY to people)
- type (TEXT) - "passport", "drivers_license", "nexus", etc.
- country (TEXT) - Issuing country/state
- document_number (TEXT) - Encrypted sensitive field
- issue_date (DATE)
- expiry_date (DATE) - Critical for notifications
- status (TEXT) - "current", "application_submitted", "received_new"
- submission_date (DATE) - When renewal application submitted
- processing_estimate (TEXT) - User-reported processing time
- photo_filename (TEXT) - Local photo storage
- notes (TEXT) - User notes
- created_at, updated_at (TIMESTAMPS)

Settings Table
- key (TEXT PRIMARY KEY) 
- value (TEXT) - JSON-serialized configuration
- updated_at (TIMESTAMP)

🔔 Smart Notification System
6-Month International Travel Rule
This is the key insight that makes this app valuable:

Green (Safe): >6 months validity remaining
Yellow (Plan): 6-3 months remaining (plan renewal)
Orange (Act): 3 months-expiry (start renewal now)
Red (Critical): <1 month or expired (urgent/travel restricted)

Three-State Document Workflow
Simplified from complex government processes to what users actually track:

Current - Document valid, no action needed
Application Submitted - Renewal in progress with government
Received New Document - Update system with new expiry date

Notification Escalation

6 months out: "Plan renewal" - gentle reminder
3 months out: "Start process" - action needed
30 days: "Urgent" - expedited processing recommended
7 days: "Critical" - travel restrictions possible
1 day: "Emergency" - immediate action required

🔌 Integration Architecture
Pushover Integration (Primary Notifications)

Homelab standard: Most self-hosters already have Pushover ($5 one-time)
Dual parent accounts: Both parents get notifications with different preferences
Rich notifications: Deep links back to specific documents
Action buttons: "Application Submitted", "Remind me later"

Nextcloud CalDAV Integration

Auto-discovery: Detect local Nextcloud instances automatically
Apple Calendar sync: Native iOS integration via CalDAV standard
Event management: Create renewal reminders 6 months before expiry
Travel coordination: Calendar events for document renewal planning

Optional CloudFlare Tunnel

WAN access: For users who want external access without Tailscale
Security maintained: Still requires authentication
Easy toggle: Uncomment service in docker-compose

📁 Project Structure
passport-manager/
├── app/
│   ├── main.py                 # Main Streamlit application
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLite schema and operations
│   │   └── migrations.py       # Database version management
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── pushover.py         # Pushover notification service
│   │   ├── caldav_client.py    # Nextcloud calendar integration
│   │   └── email_client.py     # SMTP email notifications
│   ├── auth/
│   │   ├── __init__.py
│   │   └── webauthn.py         # Future biometric authentication
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── encryption.py       # Encrypt sensitive data
│   │   ├── photo_handler.py    # Image processing and storage
│   │   └── date_utils.py       # Date calculations and formatting
│   └── static/
│       ├── custom.css          # Mobile-first responsive CSS
│       └── themes.py           # Dark/light theme management
├── docker/
│   ├── Dockerfile              # Python 3.12 slim with dependencies
│   ├── docker-compose.yml      # Standard deployment
│   ├── docker-compose-cf.yml   # With CloudFlare Tunnel
│   └── unraid-template.xml     # Community Applications template
├── docs/
│   ├── setup.md               # Detailed setup instructions
│   ├── unraid-guide.md        # Unraid-specific installation
│   ├── integrations.md        # Pushover, CalDAV setup guides
│   └── troubleshooting.md     # Common issues and solutions
├── data/ (created at runtime)
│   ├── passport_manager.db    # SQLite database
│   ├── photos/               # Document photos
│   └── config.json           # Application configuration
├── requirements.txt           # Python dependencies
├── .env.example              # Environment configuration template
├── .gitignore                # Git ignore patterns
└── README.md                 # Comprehensive documentation


🎨 User Interface Design
Dashboard (Main Tab)

Status overview: Color-coded document cards
Urgency grouping: Urgent → Warning → Current
Quick actions: "Application Submitted", "Edit", "Received New"
Family stats: Number of documents, people, items needing attention

Family Tab

Member management: Add family members with roles
Person cards: Name, role, birth date
Document association: Link documents to family members

Documents Tab

Document CRUD: Add, edit, view detailed document information
Photo upload: Camera capture or file upload (JPG/PNG only)
Status management: Update workflow states
Notes and tracking: Processing estimates, reference numbers

Settings Tab

Theme toggle: Light/dark mode preference
Notification config: Pushover, email, webhook settings
Calendar integration: Nextcloud CalDAV setup
Data management: Export/import JSON backups
Demo data controls: Clear/recreate for testing

Mobile Navigation

Sidebar stats: Quick family overview
Tab-based layout: Easy thumb navigation
Floating action buttons: Add new documents/people
Swipe gestures: Navigate between documents

🔧 Configuration Management
Environment Variables
PORT=8270                    # Web interface port
TZ=America/Vancouver          # Timezone for date calculations
CF_TUNNEL_TOKEN=optional     # CloudFlare tunnel for WAN access
PUSHOVER_USER_KEY=optional   # Notification integration
PUSHOVER_API_TOKEN=optional
SMTP_SERVER=optional         # Email notifications
CALDAV_URL=optional          # Calendar integration

Runtime Configuration (config.json)
{
  "theme": "light",
  "demo_mode": true,
  "notifications": {
    "pushover": {"user_key": "", "api_token": ""},
    "email": {"smtp_server": "", "port": 587, "username": "", "password": ""}
  },
  "calendar": {
    "caldav_url": "", "username": "", "password": "", "enabled": false
  },
  "notification_schedule": [180, 90, 30, 14, 7, 1]  # Days before expiry
}

🚀 Deployment Strategy
Target Audience: Homelab Enthusiasts

Git clone workflow: git clone → docker-compose up -d
No registry dependencies: Build locally for transparency
Unraid Community Applications: One-click template installation
Proxmox LXC ready: Standard Docker deployment

Network Security

Local network binding: Default to 127.0.0.1 and private interfaces
Tailscale detection: Auto-bind to Tailscale interface if available
No port forwarding required: Encourage VPN-based remote access

Data Persistence

Single volume mount: ./data:/app/data
Backup strategy: JSON export for migration
Photo storage: Local filesystem with optimization
Database: SQLite for simplicity and portability

📊 Demo Data System
Sample Family Structure
demo_family = {
    "people": [
        {"name": "John Doe", "role": "parent", "birth_date": "1985-03-15"},
        {"name": "Jane Doe", "role": "parent", "birth_date": "1987-07-22"},
        {"name": "Sarah Doe", "role": "child", "birth_date": "2010-11-08"},
        {"name": "Tommy Doe", "role": "child", "birth_date": "2015-09-12"}
    ],
    "documents": [
        # John's documents - all current
        {"holder": "John", "type": "passport", "country": "USA", "expiry": "2029-05-15"},
        {"holder": "John", "type": "drivers_license", "country": "California", "expiry": "2027-03-10"},
        
        # Jane's documents - some expiring soon for demo
        {"holder": "Jane", "type": "passport", "country": "Canada", "expiry": "2030-08-22"},
        {"holder": "Jane", "type": "nexus", "country": "USA/Canada", "expiry": "2026-01-15"},
        
        # Kids' documents - one expiring soon, one in renewal process
        {"holder": "Sarah", "type": "passport", "country": "USA", "expiry": "2025-11-08"},  # Expires soon
        {"holder": "Tommy", "type": "passport", "country": "USA", "status": "application_submitted"}
    ]
}

Demo Features

Easy deletion: Clear demo data when ready for real use
Realistic scenarios: Mix of current, expiring, and in-process documents
Educational value: Shows all app features immediately
Family dynamics: Demonstrates parent-child document management

🎯 Key Success Metrics
User Experience Goals

10-minute setup: From git clone to working app
Mobile-first: 80% of interactions happen on phones
Family adoption: Both parents actively use the system
Notification effectiveness: Never miss a passport renewal again

Technical Goals

Zero external dependencies: Works completely offline
Homelab integration: Fits existing infrastructure (Unraid, Proxmox)
Security first: Sensitive data never leaves local network
Community adoption: Easy to share and deploy

🔮 Future Enhancement Roadmap
Phase 1 (MVP - What you're building now)

Core document tracking and workflow
Mobile-responsive interface
Demo data and basic notifications

Phase 2 (Integrations)

Pushover notification implementation
Nextcloud CalDAV calendar integration
Email/SMTP notification fallback

Phase 3 (Security & Auth)

WebAuthn biometric authentication
Data encryption for sensitive fields
Advanced user management

Phase 4 (Community Features)

Government processing time tracking
Travel requirement integration
Multi-language support
API for third-party integrations


📝 Implementation Notes for Claude Code
Development Priority

Start with core Streamlit app - Main interface and navigation
Implement database layer - SQLite schema and CRUD operations
Add photo handling - Upload, storage, display
Build responsive UI - Mobile-first CSS and theme system
Create demo data system - Sample family for testing
Add deployment files - Docker, compose, documentation

Key Technical Decisions Made

Streamlit over Flask/FastAPI: Rapid development, great for internal tools
SQLite over PostgreSQL: Simplicity, portability, perfect for family-scale data
Local files over S3: Privacy, simplicity, no external dependencies
Port 8270: Avoids common homelab conflicts (8080, 8000, etc.)
Parent-centric access: Matches real family document management patterns

Testing Strategy

Demo mode by default: Users can explore immediately
Realistic test data: Shows edge cases (expiring documents, renewals in progress)
Easy cleanup: One-click demo data removal
Mobile testing: Responsive design verification on phones/tablets

This design creates a production-ready, family-friendly document management system that addresses real-world needs while fitting perfectly into homelab environments. The focus on privacy, mobile usability, and realistic family workflows sets it apart from generic document management tools.