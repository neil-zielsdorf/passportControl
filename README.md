# Family Passport Manager

A self-hosted, mobile-first web application for tracking family government documents (passports, licenses, NEXUS cards, etc.) with smart expiry notifications and privacy-focused design.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd passportControl
   ```

2. **Set up environment (optional)**
   ```bash
   cp .env.example .env
   # Edit .env with your encryption key and other settings
   ```

3. **Start the application**
   ```bash
   cd docker
   docker-compose up -d
   ```

4. **Access the application**
   - Open your browser to `http://localhost:8270`
   - Click "Load Demo Data" in Settings to see example family data

### With CloudFlare Tunnel (Optional)
For external access without port forwarding:

```bash
cd docker
docker-compose -f docker-compose-cf.yml up -d
```

## 📱 Features

### Core Functionality
- **Family-centric document management** - Parents manage all documents, children see their own
- **Mobile-first responsive design** - Optimized for phones and tablets
- **Document photo storage** - Upload and view document photos
- **Smart expiry tracking** - Color-coded status based on 6-month international travel rule
- **AES encryption** - Sensitive document numbers encrypted at rest

### Document Status System
- 🟢 **Safe** - More than 6 months until expiry
- 🟡 **Plan Renewal** - 6-3 months remaining
- 🟠 **Act Now** - 3 months to expiry
- 🔴 **Critical/Urgent** - Less than 1 month or expired

### Supported Document Types
- Passports
- Driver's Licenses
- NEXUS Cards
- Birth Certificates
- Custom document types

## 🔒 Security & Privacy

- **Local network only** - No external dependencies
- **AES encryption** - Document numbers encrypted in database
- **Local file storage** - Photos never leave your server
- **Configurable encryption key** - Set your own encryption key

## 📊 Demo Data

The application includes realistic demo data to showcase features:
- Sample family of 4 (2 parents, 2 children)
- Mix of current, expiring, and renewal-in-progress documents
- Demonstrates all notification states

Access via Settings → Load Demo Data

## ⚙️ Configuration

### Environment Variables
```bash
PORT=8270                           # Web interface port
TZ=America/Vancouver               # Timezone for date calculations
ENCRYPTION_KEY=your-encryption-key # AES encryption key (change this!)
CF_TUNNEL_TOKEN=optional          # CloudFlare tunnel token
```

### Data Directory
All data is stored in the `data/` directory:
- `passport_manager.db` - SQLite database
- `photos/` - Document photos
- `config.json` - Application settings

## 🐳 Docker Deployment

### Standard Deployment
```bash
cd docker
docker-compose up -d
```

### With CloudFlare Tunnel
```bash
cd docker
docker-compose -f docker-compose-cf.yml up -d
```

### Building from Source
```bash
docker build -f docker/Dockerfile -t passport-manager .
docker run -p 8270:8270 -v ./data:/app/data passport-manager
```

## 🔧 Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app/main.py --server.port=8270
```

### Project Structure
```
passportControl/
├── app/
│   ├── main.py              # Main Streamlit application
│   ├── database/
│   │   └── models.py        # Database models and operations
│   └── utils/
│       ├── encryption.py    # AES encryption utilities
│       ├── date_utils.py    # Date calculations
│       └── photo_handler.py # Photo upload and storage
├── docker/                  # Docker configuration
├── data/                    # Runtime data (created automatically)
└── docs/                    # Documentation
```

## 🏠 Homelab Integration

### Unraid
- Compatible with Community Applications
- Single volume mount: `./data:/app/data`
- Default port 8270 avoids common conflicts

### Proxmox LXC
- Standard Docker deployment works in LXC containers
- Ensure Docker is installed in the container

### Tailscale Integration
- Bind to Tailscale interface for secure remote access
- No port forwarding required

## 🔮 Roadmap

### Current Features (MVP)
- ✅ Core document tracking
- ✅ Mobile-responsive interface
- ✅ Photo upload and storage
- ✅ AES encryption
- ✅ Demo data system

### Planned Integrations
- 📬 Pushover notifications
- 📅 CalDAV calendar integration
- 📧 SMTP email notifications
- 🔐 WebAuthn biometric authentication

## 📚 Documentation

- [Setup Guide](docs/setup.md) - Detailed installation instructions
- [Unraid Guide](docs/unraid-guide.md) - Unraid-specific setup
- [Integrations](docs/integrations.md) - Pushover, CalDAV setup
- [Troubleshooting](docs/troubleshooting.md) - Common issues

## 🤝 Contributing

This project is designed for homelab enthusiasts who value privacy and simplicity. Contributions are welcome!

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Support

For issues and feature requests, please create an issue in the repository.

---

**Privacy First** 🛡️ **Family Focused** 👨‍👩‍👧‍👦 **Homelab Ready** 🏠