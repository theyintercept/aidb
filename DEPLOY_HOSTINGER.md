# Deploying to Hostinger - Step-by-Step Guide

Complete guide for deploying the Learning Sequence Manager to Hostinger hosting.

## Prerequisites

- Active Hostinger hosting account (shared, VPS, or cloud)
- Python support enabled (most Hostinger plans support Python)
- SSH access or FTP access
- Domain or subdomain configured

## Deployment Steps

### Step 1: Prepare Files Locally

1. **Update production settings in `.env`:**
   ```env
   SECRET_KEY=<generate new key>
   ADMIN_USERNAME=<your username>
   ADMIN_PASSWORD=<strong password>
   DATABASE_PATH=learning_sequence_v2.db
   ```

2. **Generate new SECRET_KEY:**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Edit `app.py` - disable debug mode:**
   
   Change line 250 from:
   ```python
   app.run(host='0.0.0.0', port=8080, debug=True)
   ```
   
   To:
   ```python
   app.run(host='0.0.0.0', port=8080, debug=False)
   ```

4. **Test locally one more time:**
   ```bash
   python3 app.py
   ```
   Visit http://localhost:8080 and verify everything works.

### Step 2: Upload Files to Hostinger

#### Method A: Using FTP (FileZilla, cPanel File Manager)

1. Connect to your Hostinger account via FTP
2. Navigate to your web directory (usually `public_html` or `htdocs`)
3. Create a subdirectory for your app (e.g., `learning-sequence/`)
4. Upload these files:
   ```
   learning-sequence/
   ├── app.py
   ├── requirements.txt
   ├── .env
   ├── learning_sequence_v2.db
   └── templates/
       ├── base.html
       ├── login.html
       ├── index.html
       ├── cluster_detail.html
       └── element_detail.html
   ```

#### Method B: Using SSH (if available)

1. SSH into your server:
   ```bash
   ssh username@yourdomain.com
   ```

2. Navigate to web directory:
   ```bash
   cd public_html
   mkdir learning-sequence
   cd learning-sequence
   ```

3. Upload using scp from your local machine:
   ```bash
   scp -r /Users/bridgethorton/AIDB/* username@yourdomain.com:public_html/learning-sequence/
   ```

### Step 3: Set Up Python App in Hostinger

#### If using cPanel (Hostinger's Panel):

1. **Login to cPanel**
2. **Find "Setup Python App" or "Python Selector"**
3. **Create New Python Application:**
   - Python Version: 3.8 or higher
   - Application Root: `/home/username/public_html/learning-sequence`
   - Application URL: Choose your domain/subdomain
   - Application Startup File: `app.py`
   - Application Entry Point: `app`

4. **Click "Create"**

#### If using SSH/Command Line:

1. **Create virtual environment:**
   ```bash
   cd ~/public_html/learning-sequence
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Test the app:**
   ```bash
   python app.py
   ```

### Step 4: Configure WSGI (for production deployment)

Create a file called `passenger_wsgi.py` in your application root:

```python
import sys
import os

# Add your app directory to the Python path
INTERP = os.path.join(os.environ['HOME'], 'public_html', 'learning-sequence', 'venv', 'bin', 'python3')
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.insert(0, os.path.dirname(__file__))

# Import your Flask app
from app import app as application
```

### Step 5: Set File Permissions

```bash
chmod 755 app.py
chmod 755 passenger_wsgi.py
chmod 644 requirements.txt
chmod 600 .env
chmod 600 learning_sequence_v2.db
chmod 755 templates
chmod 644 templates/*.html
```

### Step 6: Configure Domain/Subdomain

1. **In Hostinger Panel:**
   - Go to Domains
   - Add subdomain (e.g., `sequences.yourdomain.com`)
   - Point document root to your app directory

2. **Or use main domain:**
   - Point main domain to app directory
   - Update DNS if needed

### Step 7: Enable SSL/HTTPS

1. **In Hostinger cPanel:**
   - Go to SSL/TLS
   - Install Let's Encrypt certificate (usually free)
   - Enable "Force HTTPS"

2. **Verify HTTPS is working:**
   - Visit https://yourdomain.com
   - Check for padlock icon

### Step 8: Configure Environment Variables (Optional, More Secure)

Instead of using `.env` file, you can set environment variables in cPanel:

1. **In cPanel:**
   - Find "Python App" settings
   - Add environment variables:
     - `SECRET_KEY`: your secret key
     - `ADMIN_USERNAME`: your username
     - `ADMIN_PASSWORD`: your password
     - `DATABASE_PATH`: learning_sequence_v2.db

2. **Update `app.py`** to handle missing `.env`:
   - The app already loads from environment variables as fallback
   - You can delete the `.env` file for extra security

### Step 9: Restart the Application

In cPanel Python App interface:
- Click "Restart" button

Or via SSH:
```bash
touch ~/public_html/learning-sequence/tmp/restart.txt
```

Or:
```bash
pkill -f app.py
python3 app.py &
```

### Step 10: Test Your Deployment

1. **Visit your URL:** https://yourdomain.com
2. **You should see the login page**
3. **Login with credentials from `.env`**
4. **Test all functionality:**
   - Browse clusters
   - Edit a cluster
   - View an element
   - Edit an element
   - Add/remove VC references

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'flask'"

**Solution:** Install dependencies in the right environment
```bash
cd ~/public_html/learning-sequence
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Permission denied" for database

**Solution:** Fix file permissions
```bash
chmod 600 learning_sequence_v2.db
chown username:username learning_sequence_v2.db
```

### Issue: "500 Internal Server Error"

**Solution:** Check error logs
```bash
tail -f ~/logs/error_log
```

Or in cPanel: "Errors" section

### Issue: App works on port 8080 but not on domain

**Solution:** You need to use WSGI (see Step 4). Flask's built-in server (`app.run()`) is for development only.

For production:
- Use `passenger_wsgi.py`
- Or use Gunicorn: `pip install gunicorn`
- Run: `gunicorn -w 4 -b 0.0.0.0:8080 app:app`

### Issue: Changes to .env not taking effect

**Solution:** Restart the application
```bash
touch ~/public_html/learning-sequence/tmp/restart.txt
```

### Issue: Database locked

**Solution:** SQLite doesn't handle concurrent writes well. If multiple processes access it:
1. Ensure only one app instance is running
2. Consider migrating to PostgreSQL for production with multiple apps

## Performance Optimization

### Enable Caching

Add to `app.py`:
```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@cache.cached(timeout=300)  # Cache for 5 minutes
def get_clusters():
    # ... query logic
```

### Use Gunicorn with Workers

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

### Database Optimization

For large datasets:
1. Add indexes to frequently queried columns
2. Use SQLite `PRAGMA` optimizations
3. Consider read-only replicas

## Backup Strategy

### Automated Backups

Create a backup script `backup.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$HOME/backups"
mkdir -p $BACKUP_DIR

# Backup database
cp ~/public_html/learning-sequence/learning_sequence_v2.db \
   $BACKUP_DIR/db_backup_$DATE.db

# Backup .env
cp ~/public_html/learning-sequence/.env \
   $BACKUP_DIR/env_backup_$DATE.txt

# Keep only last 30 days
find $BACKUP_DIR -name "db_backup_*.db" -mtime +30 -delete
find $BACKUP_DIR -name "env_backup_*.txt" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Make it executable and add to cron:
```bash
chmod +x backup.sh
crontab -e
# Add: 0 2 * * * ~/backup.sh  # Daily at 2 AM
```

### Manual Backup

```bash
cp learning_sequence_v2.db learning_sequence_v2.db.backup
```

## Monitoring

### Set Up Uptime Monitoring

Use services like:
- UptimeRobot (free)
- Pingdom
- StatusCake

Monitor: `https://yourdomain.com/login` (should return 200)

### Log Monitoring

Check logs regularly:
```bash
tail -f ~/logs/access_log
tail -f ~/logs/error_log
```

## Updating the App

When you make changes locally:

1. **Test locally first**
2. **Backup production database:**
   ```bash
   scp username@yourdomain.com:public_html/learning-sequence/learning_sequence_v2.db ./backup/
   ```
3. **Upload updated files:**
   ```bash
   scp app.py username@yourdomain.com:public_html/learning-sequence/
   ```
4. **Restart app:**
   ```bash
   ssh username@yourdomain.com "touch ~/public_html/learning-sequence/tmp/restart.txt"
   ```
5. **Test thoroughly**

## Security Checklist

Before going live:
- [ ] Strong password set in `.env`
- [ ] New `SECRET_KEY` generated
- [ ] Debug mode disabled (`debug=False`)
- [ ] HTTPS enabled with valid certificate
- [ ] File permissions set correctly
- [ ] `.env` not publicly accessible
- [ ] Database file not publicly accessible
- [ ] Backups configured and tested
- [ ] Monitoring set up

## Cost Considerations

### Hostinger Pricing (approximate)
- **Shared hosting:** $2-10/month (good for MVP, single user)
- **VPS:** $4-30/month (better performance, more control)
- **Cloud:** $10-60/month (best for multiple apps, high traffic)

For your use case (single user, multiple apps):
- Start with shared hosting for MVP
- Upgrade to VPS when adding more apps or users
- Consider cloud hosting if you need high availability

## Getting Help

### Hostinger Support
- Live chat (24/7)
- Knowledge base: https://support.hostinger.com
- Community forum

### Common Resources
- [Hostinger Python App Tutorial](https://support.hostinger.com/en/articles/how-to-deploy-python-application)
- [Flask Deployment Options](https://flask.palletsprojects.com/en/latest/deploying/)

## Next Steps After Deployment

Once your app is live and working:

1. **Create more apps/tools** that use the same database
2. **Consider API approach** for better multi-app architecture
3. **Add features:** file uploads, prerequisites, analysis views
4. **Collect feedback** and iterate
5. **Monitor usage** and optimize as needed

You now have a secure, production-ready learning sequence manager! 🎉
