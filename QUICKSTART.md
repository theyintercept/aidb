# Quick Start Guide

Get the Learning Sequence Manager running in 3 minutes.

## Method 1: Automatic Setup (Recommended)

```bash
./setup.sh
```

Then edit `.env` to set your password, and run:

```bash
python3 app.py
```

## Method 2: Manual Setup

### 1. Install dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Configure credentials

The `.env` file has been created with default credentials:
- Username: `admin`
- Password: `changeme123`

**⚠️ IMPORTANT:** Change the password before deploying to production!

Edit `.env` and update `ADMIN_PASSWORD` to something secure.

### 3. Run the app

```bash
python3 app.py
```

### 4. Open in browser

Go to: **http://localhost:8080**

Login with your credentials from `.env`

## What You Can Do

### Browse and Edit Clusters
- View all clusters organized by year level (Foundation, Year 1, Year 2)
- Edit cluster titles, rationales, and sequence notes
- Mark clusters as published/draft

### Manage Elements
- View elements within each cluster
- Edit learning objectives, teacher notes, audio scripts
- Set CPA stages (Concrete, Pictorial, Abstract)
- Set intrinsic load levels (Low, Medium, High)

### Link Victorian Curriculum References
- Add VC 2.0 codes to clusters
- View full content descriptions
- Remove references when needed

## Security Features

✅ **Password protected** - Only you can access  
✅ **Session-based auth** - Secure login sessions  
✅ **Environment variables** - No hardcoded secrets  
✅ **Input validation** - Protected against bad data  
✅ **HTTPS ready** - Works with SSL certificates  

## Deploying to Hostinger

1. **Upload these files via FTP/SSH:**
   - `app.py`
   - `requirements.txt`
   - `.env` (with production password!)
   - `learning_sequence_v2.db`
   - `templates/` folder

2. **Create Python app in cPanel:**
   - Select Python 3.8+
   - Point to `app.py`
   - Set domain/subdomain

3. **Install dependencies on server:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Security checklist:**
   - Change `ADMIN_PASSWORD` to a strong password
   - Set file permissions: `chmod 600 .env learning_sequence_v2.db`
   - Enable SSL certificate for HTTPS
   - Change `debug=False` in `app.py`

5. **Test it:**
   - Go to your domain
   - Login with your credentials
   - Start editing!

## Troubleshooting

### "Module not found" error
```bash
pip3 install -r requirements.txt
```

### "Database file not found"
Make sure `learning_sequence_v2.db` is in the same folder as `app.py`

### "Invalid credentials"
Check your `.env` file - make sure `ADMIN_USERNAME` and `ADMIN_PASSWORD` match what you're typing

### Port 8080 already in use
Edit `app.py` line 250 and change `8080` to another port like `8081`

### Can't see database changes
The app reads directly from the SQLite file. Make sure you're editing the right database file.

## Need Help?

- Check `README.md` for full documentation
- Review `HANDOVER.md` for database schema details
- View `schema_v2_1.sql` for database structure

## Next Steps

After the MVP is working, we can add:
- Resource upload (PDF, DOC, PowerPoint, images)
- Element prerequisites visualization
- Slideshow viewer for PowerPoint files
- Analysis views (load distribution, bridging elements)
