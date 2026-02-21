# Security Documentation

This document outlines the security measures implemented in the Learning Sequence Manager and best practices for deployment.

## ✅ Implemented Security Features

### 1. Authentication & Authorization
- **Session-based authentication** using Flask's secure session management
- **Password protection** - only authenticated users can access the application
- **Single admin user** model (appropriate for single-user deployment)
- **Environment variable credentials** - no hardcoded passwords
- **Logout functionality** - properly clears session data

### 2. Session Security
- **SECRET_KEY** - Cryptographically random secret key for session signing
- **Secure session cookies** - Protected against tampering
- **Session timeout** - Sessions expire when browser closes (default Flask behavior)

### 3. Input Validation
- **Form validation** - All inputs are validated before database operations
- **SQL parameterization** - All database queries use parameterized statements (prevents SQL injection)
- **CSRF protection** - Flask's built-in CSRF protection via session tokens

### 4. Data Protection
- **Environment variables** - Sensitive configuration stored in `.env` file
- **.gitignore** - Prevents sensitive files from being committed to version control
- **No hardcoded secrets** - All credentials and keys loaded from environment

### 5. File Security
- **Restricted file access** - Database and `.env` file should have restrictive permissions
- **Separate uploads folder** - User uploads isolated from application code
- **No directory traversal** - File paths are validated (for future file upload feature)

### 6. Database Security
- **Read-only queries** - Use `query_db()` helper for SELECT queries
- **Write isolation** - Use `execute_db()` helper for INSERT/UPDATE/DELETE
- **Connection management** - Proper connection opening/closing
- **No sensitive data exposure** - Views exclude BLOB data from listings

## 🔒 Production Deployment Checklist

### Before Deploying to Hostinger

1. **Change Default Credentials**
   ```env
   ADMIN_USERNAME=your_unique_username
   ADMIN_PASSWORD=YourStr0ng!P@ssw0rd
   ```

2. **Regenerate SECRET_KEY**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copy the output and update `SECRET_KEY` in `.env`

3. **Disable Debug Mode**
   Edit `app.py` line 250:
   ```python
   app.run(host='0.0.0.0', port=8080, debug=False)  # Change to False
   ```

4. **Set File Permissions**
   ```bash
   chmod 600 .env
   chmod 600 learning_sequence_v2.db
   chmod 755 app.py
   ```

5. **Enable HTTPS**
   - Install SSL certificate (Let's Encrypt, Hostinger SSL, etc.)
   - Ensure all traffic uses HTTPS (configure in hosting panel)
   - Never use HTTP for production

6. **Secure Database Backups**
   - Set up automatic backups of `learning_sequence_v2.db`
   - Store backups securely (encrypted if possible)
   - Test restore procedures regularly

7. **Review Server Configuration**
   - Disable directory listing
   - Hide server version information
   - Configure firewall rules (if applicable)
   - Limit upload file sizes (when implementing file uploads)

8. **Environment Variables on Server**
   - Use hosting panel environment variables (more secure than `.env` file)
   - Or ensure `.env` is outside document root
   - Never expose `.env` via web server

## 🛡️ Security Measures for Multi-App Usage

Since you want to use this database across multiple apps/websites:

### Option 1: API Gateway Pattern (Recommended)
```
[Database] ← [Flask API (this app)] ← [Multiple Frontend Apps]
                      ↓
              API Key Authentication
```

**To implement:**
1. Add API key generation and validation
2. Create REST API endpoints
3. Issue unique API keys for each consuming app
4. Log all API access for auditing

### Option 2: Database Replication
```
[Master DB] → [Replicas for each app]
     ↓
  Read-only
```

**Note:** SQLite doesn't natively support replication. Consider:
- Upgrade to PostgreSQL for true replication
- Use file-based sync (rsync, cloud storage)
- Accept eventual consistency

### Option 3: Shared Database with Row-Level Security
- Migrate to PostgreSQL
- Implement row-level security policies
- Each app gets its own database user with limited permissions

## 🚨 Security Warnings

### Current Limitations (Single-User MVP)

❌ **No rate limiting** - Vulnerable to brute force attacks  
❌ **No account lockout** - Unlimited login attempts  
❌ **No password strength requirements** - User must choose strong password  
❌ **No multi-factor authentication (MFA)** - Single factor (password) only  
❌ **No audit logging** - No record of who changed what  
❌ **No IP restrictions** - Accessible from any IP address  

### Recommendations for Production

If exposing to the internet:

1. **Add Rate Limiting**
   ```bash
   pip install Flask-Limiter
   ```

2. **Add Account Lockout**
   - Track failed login attempts
   - Lock account after 5 failed attempts
   - Require cooldown period or email reset

3. **Add Audit Logging**
   - Log all data modifications (who, what, when)
   - Store logs separately from application
   - Regular log review

4. **Add IP Whitelisting**
   - Restrict access to known IP addresses
   - Use VPN for remote access

5. **Consider Two-Factor Authentication**
   - Use TOTP (Google Authenticator, Authy)
   - Or email-based verification codes

## 🔐 Password Security Best Practices

### For Admin Password

- **Minimum 12 characters**
- Mix of uppercase, lowercase, numbers, symbols
- No dictionary words
- No personal information
- Unique (not used elsewhere)

**Example strong passwords:**
- `mK9#vL2@nX4!pQ8$`
- `Tr0pic@l-P@rr0t-2026!`
- `C0gnitive$L0ad#Theory!`

### Storing Passwords

Currently using plain text in `.env` (acceptable for single user on secure server).

For multi-user systems:
- Hash passwords using bcrypt or Argon2
- Store only hashes, never plain text
- Salt each password individually

## 🔍 Security Monitoring

### Things to Monitor

1. **Failed login attempts** - Unusually high = potential attack
2. **Database file size** - Unexpected growth = potential issue
3. **Server logs** - Look for suspicious activity
4. **File integrity** - Verify `app.py` hasn't been modified
5. **Backup success** - Ensure backups are working

### Set Up Alerts

- Failed login threshold (e.g., 10 failures in 1 hour)
- Database file modification (outside application)
- Disk space warnings
- SSL certificate expiration

## 📞 Incident Response

If you suspect a security breach:

1. **Immediately change passwords** in `.env`
2. **Regenerate SECRET_KEY**
3. **Check database for unauthorized changes**
4. **Review server logs** for suspicious activity
5. **Restore from backup** if data integrity compromised
6. **Update all accessing applications** with new credentials

## 🔄 Regular Security Maintenance

### Weekly
- [ ] Review server logs for anomalies
- [ ] Verify backups are running

### Monthly
- [ ] Test database restore procedure
- [ ] Review and rotate API keys (when implemented)
- [ ] Check for package updates: `pip list --outdated`

### Quarterly
- [ ] Change admin password
- [ ] Regenerate SECRET_KEY
- [ ] Security audit of code changes
- [ ] Review access logs

### Annually
- [ ] Full security review
- [ ] Penetration testing (if budget allows)
- [ ] Update security documentation

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [SQLite Security](https://www.sqlite.org/security.html)

## 📧 Security Contact

For security concerns or questions about this implementation, document them in your project notes for future reference.
