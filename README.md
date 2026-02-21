# Learning Sequence Manager

A secure Flask web application for managing Victorian Numeracy learning sequences, built around cognitive load theory.

## Features

### MVP Scope (Implemented)
✅ Browse clusters by year level (Foundation, Year 1, Year 2)  
✅ View cluster details with elements  
✅ Edit cluster fields (title, rationale, sequence notes, published status)  
✅ View element details  
✅ Edit element fields (title, objective, teacher notes, CPA stage, intrinsic load)  
✅ Add/remove Victorian Curriculum 2.0 references to clusters  
✅ Secure authentication (username/password)  

### Coming Soon
- Resource upload (PDF, DOC, images, PowerPoint)
- Element prerequisites management
- Slideshow viewer for PowerPoint
- Analysis views (prerequisite chains, load distribution)

## Security Features

- ✅ Session-based authentication
- ✅ Password protection via environment variables
- ✅ CSRF protection (Flask built-in)
- ✅ Input validation on all forms
- ✅ No hardcoded credentials
- ✅ .gitignore prevents sensitive files from being committed

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example file and edit it:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
SECRET_KEY=your-very-long-random-secret-key-here
ADMIN_USERNAME=your_username
ADMIN_PASSWORD=your_secure_password
DATABASE_PATH=learning_sequence_v2.db
```

**Important:** Generate a strong SECRET_KEY. You can use Python to generate one:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Ensure Database File Exists

Make sure `learning_sequence_v2.db` is in the project directory. If you don't have it yet, you can create it from the schema:

```bash
sqlite3 learning_sequence_v2.db < schema_v2_1.sql
```

### 4. Run the Application

```bash
python app.py
```

The app will start on **http://localhost:8080**

### 5. Login

Open your browser and go to `http://localhost:8080`. Login with the username and password you set in the `.env` file.

## Deployment to Hostinger

### Prerequisites
- Python 3.8+ installed on server
- SSH access to your Hostinger account
- Database file uploaded to server

### Steps

1. **Upload files via FTP or SSH:**
   - `app.py`
   - `requirements.txt`
   - `.env` (with production credentials)
   - `learning_sequence_v2.db`
   - `templates/` folder
   - `uploads/` folder (create empty)

2. **Install dependencies on server:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up WSGI (if using cPanel/Hostinger panel):**
   - Create a Python app in cPanel
   - Point it to `app.py`
   - Set environment to production
   - Configure domain/subdomain

4. **Security checklist for production:**
   - [ ] Change `SECRET_KEY` to a strong random value
   - [ ] Change `ADMIN_PASSWORD` to a strong password
   - [ ] Set `debug=False` in `app.py` (line 250)
   - [ ] Use HTTPS (enable SSL certificate)
   - [ ] Restrict database file permissions (`chmod 600 learning_sequence_v2.db`)
   - [ ] Set `.env` file permissions (`chmod 600 .env`)
   - [ ] Regular backups of database file

5. **Optional: Use environment variables from hosting panel**
   - Many hosts let you set environment variables in the control panel
   - Remove `.env` file and use panel variables instead (more secure)

## Project Structure

```
AIDB/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not committed)
├── .env.example               # Template for environment variables
├── .gitignore                 # Prevents sensitive files from git
├── learning_sequence_v2.db    # SQLite database (not committed)
├── schema_v2_1.sql            # Database schema reference
├── HANDOVER.md                # Project brief
├── README.md                  # This file
└── templates/                 # HTML templates
    ├── base.html              # Base template with nav and styling
    ├── login.html             # Login page
    ├── index.html             # Browse clusters by year
    ├── cluster_detail.html    # View/edit cluster
    └── element_detail.html    # View/edit element
```

## Database Schema Overview

- **Year Levels:** Foundation, Year 1-6
- **Strands:** Number, Algebra, Measurement, Space, Statistics
- **Clusters:** 83 clusters grouped by year level (#101-125, #201-225, #301-333)
- **Elements:** 291 elements with CPA stages and intrinsic load levels
- **VC References:** Links to Victorian Curriculum 2.0 content descriptions

Hierarchy: **Year Level → Cluster → Element → Resource**

## Tech Stack

- **Backend:** Flask 3.0 (Python)
- **Database:** SQLite 3
- **Frontend:** Bootstrap 5.3, Bootstrap Icons
- **Templates:** Jinja2
- **Security:** Werkzeug password utilities, Flask sessions

## Support

For issues or questions, refer to `HANDOVER.md` for detailed schema information and requirements.
