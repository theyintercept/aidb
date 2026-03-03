import os
import sqlite3
import threading
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
import io
import re
from urllib.parse import quote, unquote

# Load environment variables (from app dir so .env is found when run via systemd/other cwd)
_load_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_load_env_path)
if not os.path.isfile(_load_env_path):
    load_dotenv()  # fallback: cwd

app = Flask(__name__)
CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))  # Restrict in production
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DATABASE'] = os.getenv('DATABASE_PATH', 'learning_sequence_v2.db')
# UPLOAD_FOLDER: use env, or put uploads next to the database (so Railway Volume holds both)
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER') or os.path.join(
    os.path.dirname(os.path.abspath(app.config['DATABASE'])),
    'uploads'
)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
DB_UPLOAD_MAX = 3 * 1024 * 1024 * 1024  # 3GB for database upload

# URL signer for temporary public file access (expires in 1 hour)
url_serializer = URLSafeTimedSerializer(app.secret_key)

def _resolve_resource_file(resource):
    """Return (file_obj_or_path, mimetype, download_name) for sending, or None if not found.
    Prefers file_data (BLOB), falls back to file_path (filesystem)."""
    if resource.get('file_data'):
        return (io.BytesIO(resource['file_data']), resource.get('mime_type'), resource.get('file_name'))
    if resource.get('file_path'):
        fp = resource['file_path'].lstrip('/')
        # file_path may be 'uuid_file.pdf' (flat) or '123/filename.pdf' (subdir from migration)
        if '..' in fp or fp.startswith('/'):
            return None
        path = os.path.join(app.config['UPLOAD_FOLDER'], fp)
        if os.path.exists(path):
            return (path, resource.get('mime_type'), resource.get('file_name'))
    return None

def _api_base_url():
    """Base URL for API responses (download_url etc). Use HTTPS on Railway."""
    public = os.getenv('AIDB_PUBLIC_URL', '').strip().rstrip('/')
    if public:
        return public
    base = request.url_root.rstrip('/')
    if base.startswith('http://'):
        if request.headers.get('X-Forwarded-Proto') == 'https':
            return 'https://' + base[7:]
        if 'railway.app' in (request.host or ''):
            return 'https://' + base[7:]
    return base

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'ppt': 'application/vnd.ms-powerpoint',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'webp': 'image/webp'
}

# Files stored in database (as BLOB)
BLOB_EXTENSIONS = ['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp']
# Files stored in file system
FILE_EXTENSIONS = ['ppt', 'pptx']

# ============================================================
# DATABASE HELPERS
# ============================================================

def get_db():
    """Get database connection"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

def query_db(query, args=(), one=False):
    """Execute a query and return results"""
    db = get_db()
    cur = db.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    db.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Execute a write query (INSERT, UPDATE, DELETE)"""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    lastrowid = cur.lastrowid
    cur.close()
    db.close()
    return lastrowid

# ============================================================
# FILE UPLOAD HELPERS
# ============================================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_extension(filename):
    """Get file extension in lowercase"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def get_mime_type(extension):
    """Get MIME type for file extension"""
    return ALLOWED_EXTENSIONS.get(extension.lower(), 'application/octet-stream')

# Extension → format code for API (so website shows real type from file_url/filename, not default PDF)
EXTENSION_TO_FORMAT = {
    'pdf': 'PDF', 'doc': 'DOC', 'docx': 'DOCX', 'ppt': 'PPT', 'pptx': 'PPTX',
    'png': 'IMG', 'jpg': 'IMG', 'jpeg': 'IMG', 'gif': 'IMG', 'webp': 'IMG',
}

def _format_from_url_or_filename(file_url, file_name):
    """Derive format code from file URL or filename for API response."""
    for s in (file_url, file_name):
        if not s or not isinstance(s, str):
            continue
        # Take last path segment and get extension
        part = s.split('/')[-1].split('?')[0]
        if '.' in part:
            ext = part.rsplit('.', 1)[1].lower()
            if ext in EXTENSION_TO_FORMAT:
                return EXTENSION_TO_FORMAT[ext]
    return None

# ============================================================
# AUTHENTICATION
# ============================================================

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check credentials from environment variables
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin')
        
        if username == admin_username and password == admin_password:
            session['logged_in'] = True
            session['username'] = username
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('Successfully logged out.', 'info')
    return redirect(url_for('login'))

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
@login_required
def index():
    """Home page - browse clusters by year level"""
    year_levels = query_db('SELECT * FROM year_levels ORDER BY display_order')
    
    # Get clusters grouped by year level with elements
    clusters_by_year = {}
    for year in year_levels:
        clusters_raw = query_db('''
            SELECT c.id, c.cluster_number, c.title, c.year_level_id, c.strand_id, 
                   s.name as strand_name, c.is_published,
                   GROUP_CONCAT(vc.code, ', ') as vc_codes
            FROM clusters c
            LEFT JOIN strands s ON c.strand_id = s.id
            LEFT JOIN vc_references vc ON c.id = vc.cluster_id
            WHERE c.year_level_id = ?
            GROUP BY c.id
            ORDER BY c.cluster_number
        ''', [year['id']])
        
        # For each cluster, get its elements with resource counts
        clusters_with_elements = []
        for cluster in clusters_raw:
            elements = query_db('''
                SELECT e.id, e.element_number, e.title, e.is_published,
                       ce.sequence_order,
                       cpa.name as cpa_name,
                       ill.name as load_name,
                       csl.name as stability_name,
                       (SELECT COUNT(*) FROM resources WHERE element_id = e.id) as resource_count
                FROM cluster_elements ce
                JOIN elements e ON ce.element_id = e.id
                LEFT JOIN cpa_stages cpa ON e.cpa_stage_id = cpa.id
                LEFT JOIN intrinsic_load_levels ill ON e.intrinsic_load_id = ill.id
                LEFT JOIN concept_stability_levels csl ON e.concept_stability_id = csl.id
                WHERE ce.cluster_id = ?
                ORDER BY ce.sequence_order
            ''', [cluster['id']])
            
            # Convert cluster Row to dict and add elements
            cluster_dict = dict(cluster)
            cluster_dict['elements'] = elements
            clusters_with_elements.append(cluster_dict)
        
        clusters_by_year[year['code']] = {
            'name': year['name'],
            'clusters': clusters_with_elements
        }
    
    return render_template('index.html', 
                         year_levels=year_levels, 
                         clusters_by_year=clusters_by_year)

@app.route('/cluster/<int:cluster_id>')
@login_required
def cluster_detail(cluster_id):
    """View cluster detail"""
    # Get cluster info
    cluster = query_db('''
        SELECT c.*, yl.name as year_level_name, s.name as strand_name
        FROM clusters c
        LEFT JOIN year_levels yl ON c.year_level_id = yl.id
        LEFT JOIN strands s ON c.strand_id = s.id
        WHERE c.id = ?
    ''', [cluster_id], one=True)
    
    if not cluster:
        flash('Cluster not found', 'danger')
        return redirect(url_for('index'))
    
    # Get elements in this cluster
    elements = query_db('''
        SELECT e.id, e.element_number, e.title, e.learning_objective, 
               e.teacher_notes, e.audio_script, e.cpa_stage_id, e.intrinsic_load_id,
               e.concept_stability_id, e.is_published, ce.sequence_order, 
               cpa.name as cpa_name, ill.name as load_name, csl.name as stability_name
        FROM cluster_elements ce
        JOIN elements e ON ce.element_id = e.id
        LEFT JOIN cpa_stages cpa ON e.cpa_stage_id = cpa.id
        LEFT JOIN intrinsic_load_levels ill ON e.intrinsic_load_id = ill.id
        LEFT JOIN concept_stability_levels csl ON e.concept_stability_id = csl.id
        WHERE ce.cluster_id = ?
        ORDER BY ce.sequence_order
    ''', [cluster_id])
    
    # Get VC references for this cluster
    vc_refs = query_db('''
        SELECT vr.*, vcd.strand, vcd.level_band
        FROM vc_references vr
        LEFT JOIN vc_content_descriptions vcd ON vr.code = vcd.code
        WHERE vr.cluster_id = ?
        ORDER BY vr.code
    ''', [cluster_id])
    
    # Get available VC codes for adding (not already linked)
    existing_codes = [ref['code'] for ref in vc_refs]
    if existing_codes:
        placeholders = ','.join('?' * len(existing_codes))
        available_vc = query_db(f'''
            SELECT code, strand, level_band, description
            FROM vc_content_descriptions
            WHERE code NOT IN ({placeholders})
            ORDER BY code
        ''', existing_codes)
    else:
        available_vc = query_db('''
            SELECT code, strand, level_band, description
            FROM vc_content_descriptions
            ORDER BY code
        ''')
    
    # Get cluster resources (reference materials)
    cluster_resources = query_db('''
        SELECT id, resource_type, title, file_name, mime_type, url
        FROM cluster_resources
        WHERE cluster_id = ?
        ORDER BY resource_type, title
    ''', [cluster_id])
    
    return render_template('cluster_detail.html', 
                         cluster=cluster, 
                         elements=elements, 
                         vc_refs=vc_refs, 
                         available_vc=available_vc,
                         cluster_resources=cluster_resources)

@app.route('/cluster/<int:cluster_id>/edit', methods=['POST'])
@login_required
def cluster_edit(cluster_id):
    """Edit cluster fields"""
    title = request.form.get('title')
    rationale = request.form.get('rationale')
    sequence_notes = request.form.get('sequence_notes')
    is_published = 1 if request.form.get('is_published') else 0
    
    execute_db('''
        UPDATE clusters 
        SET title = ?, rationale = ?, sequence_notes = ?, is_published = ?
        WHERE id = ?
    ''', [title, rationale, sequence_notes, is_published, cluster_id])
    
    flash('Cluster updated successfully!', 'success')
    return redirect(url_for('cluster_detail', cluster_id=cluster_id))

@app.route('/cluster/<int:cluster_id>/vc/add', methods=['POST'])
@login_required
def cluster_add_vc(cluster_id):
    """Add VC reference to cluster"""
    vc_code = request.form.get('vc_code')
    
    # Get the full description from master table
    vc_desc = query_db('''
        SELECT description, url
        FROM vc_content_descriptions
        WHERE code = ?
    ''', [vc_code], one=True)
    
    if vc_desc:
        execute_db('''
            INSERT INTO vc_references (cluster_id, code, description, url)
            VALUES (?, ?, ?, ?)
        ''', [cluster_id, vc_code, vc_desc['description'], vc_desc['url']])
        flash(f'VC reference {vc_code} added successfully!', 'success')
    else:
        flash('VC code not found', 'danger')
    
    return redirect(url_for('cluster_detail', cluster_id=cluster_id))

@app.route('/cluster/<int:cluster_id>/vc/<int:vc_ref_id>/remove', methods=['POST'])
@login_required
def cluster_remove_vc(cluster_id, vc_ref_id):
    """Remove VC reference from cluster"""
    execute_db('DELETE FROM vc_references WHERE id = ? AND cluster_id = ?', 
               [vc_ref_id, cluster_id])
    flash('VC reference removed successfully!', 'success')
    return redirect(url_for('cluster_detail', cluster_id=cluster_id))

@app.route('/element/<int:element_id>')
@login_required
def element_detail(element_id):
    """View element detail"""
    element = query_db('''
        SELECT e.*, 
               cpa.name as cpa_name, cpa.code as cpa_code,
               ill.name as load_name, ill.code as load_code,
               csl.name as stability_name, csl.code as stability_code
        FROM elements e
        LEFT JOIN cpa_stages cpa ON e.cpa_stage_id = cpa.id
        LEFT JOIN intrinsic_load_levels ill ON e.intrinsic_load_id = ill.id
        LEFT JOIN concept_stability_levels csl ON e.concept_stability_id = csl.id
        WHERE e.id = ?
    ''', [element_id], one=True)
    
    if not element:
        flash('Element not found', 'danger')
        return redirect(url_for('index'))
    
    # Get clusters this element belongs to
    clusters = query_db('''
        SELECT c.id, c.cluster_number, c.title, yl.name as year_level_name
        FROM cluster_elements ce
        JOIN clusters c ON ce.cluster_id = c.id
        JOIN year_levels yl ON c.year_level_id = yl.id
        WHERE ce.element_id = ?
        ORDER BY c.cluster_number
    ''', [element_id])
    
    # Get available CPA stages, load levels, and stability levels for dropdowns
    cpa_stages = query_db('SELECT * FROM cpa_stages ORDER BY display_order')
    load_levels = query_db('SELECT * FROM intrinsic_load_levels ORDER BY display_order')
    stability_levels = query_db('SELECT * FROM concept_stability_levels ORDER BY display_order')
    
    # Get resources attached to this element (without BLOB data for listing)
    # Order by category display order, then by title
    resources = query_db('''
        SELECT r.id, r.title, r.description, r.audience, r.uploaded_at,
               r.file_name, r.file_size_bytes, r.resource_category_id,
               rc.name as category_name, rc.icon as category_icon, rc.display_order,
               ff.name as format_name, ff.icon as format_icon, ff.code as format_code,
               r.file_path, ff.stored_in_db
        FROM resources r
        LEFT JOIN resource_categories rc ON r.resource_category_id = rc.id
        LEFT JOIN file_formats ff ON r.file_format_id = ff.id
        WHERE r.element_id = ?
        ORDER BY rc.display_order, r.title
    ''', [element_id])
    
    # Get available resource categories and file formats
    resource_categories = query_db('SELECT * FROM resource_categories ORDER BY display_order')
    
    return render_template('element_detail.html', 
                         element=element, 
                         clusters=clusters,
                         cpa_stages=cpa_stages,
                         load_levels=load_levels,
                         stability_levels=stability_levels,
                         resources=resources,
                         resource_categories=resource_categories)

@app.route('/element/<int:element_id>/edit', methods=['POST'])
@login_required
def element_edit(element_id):
    """Edit element fields"""
    title = request.form.get('title')
    learning_objective = request.form.get('learning_objective')
    teacher_notes = request.form.get('teacher_notes')
    audio_script = request.form.get('audio_script')
    cpa_stage_id = request.form.get('cpa_stage_id')
    intrinsic_load_id = request.form.get('intrinsic_load_id')
    concept_stability_id = request.form.get('concept_stability_id')
    is_published = 1 if request.form.get('is_published') else 0
    
    execute_db('''
        UPDATE elements 
        SET title = ?, learning_objective = ?, teacher_notes = ?, 
            audio_script = ?, cpa_stage_id = ?, intrinsic_load_id = ?, 
            concept_stability_id = ?, is_published = ?
        WHERE id = ?
    ''', [title, learning_objective, teacher_notes, audio_script, 
          cpa_stage_id, intrinsic_load_id, concept_stability_id or None, is_published, element_id])
    
    flash('Element updated successfully!', 'success')
    return redirect(url_for('element_detail', element_id=element_id))

@app.route('/element/<int:element_id>/resource/upload', methods=['POST'])
@login_required
def resource_upload(element_id):
    """Upload a resource to an element"""
    # Check if file was uploaded
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('element_detail', element_id=element_id))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('element_detail', element_id=element_id))
    
    if not allowed_file(file.filename):
        flash('File type not allowed. Please upload PDF, DOC, DOCX, PPT, PPTX, or image files.', 'danger')
        return redirect(url_for('element_detail', element_id=element_id))
    
    # Get form data
    title = request.form.get('title', file.filename)
    description = request.form.get('description', '')
    resource_category_id = request.form.get('resource_category_id')
    audience = request.form.get('audience', 'both')
    
    if not resource_category_id:
        flash('Please select a resource category', 'danger')
        return redirect(url_for('element_detail', element_id=element_id))
    
    # Get file info
    filename = secure_filename(file.filename)
    extension = get_file_extension(filename)
    mime_type = get_mime_type(extension)
    
    # Get file format ID from database
    file_format = query_db('SELECT id FROM file_formats WHERE code = ?', 
                          [extension.upper()], one=True)
    if not file_format:
        # Use OTHER format as fallback
        file_format = query_db('SELECT id FROM file_formats WHERE code = ?', 
                              ['OTHER'], one=True)
    
    file_format_id = file_format['id'] if file_format else None
    
    # Store all files on disk (works on Hostinger, Railway with Volume, etc.)
    import uuid
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file.save(file_path)

    execute_db('''
        INSERT INTO resources (element_id, title, description, resource_category_id,
                             file_format_id, audience, file_path, file_size_bytes,
                             file_name, mime_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [element_id, title, description, resource_category_id, file_format_id,
          audience, unique_filename, os.path.getsize(file_path), filename, mime_type])
    flash(f'Resource "{title}" uploaded successfully!', 'success')
    
    return redirect(url_for('element_detail', element_id=element_id))

@app.route('/resource/<int:resource_id>/download')
@login_required
def resource_download(resource_id):
    """Download a resource (BLOB or file_path)"""
    resource = query_db('SELECT r.* FROM resources r WHERE r.id = ?', [resource_id], one=True)
    if not resource:
        flash('Resource not found', 'danger')
        return redirect(url_for('index'))
    resolved = _resolve_resource_file(resource)
    if not resolved:
        flash('File not found on server', 'danger')
        return redirect(url_for('index'))
    return send_file(resolved[0], mimetype=resolved[1] or 'application/octet-stream',
                     as_attachment=True, download_name=resolved[2])

@app.route('/resource/<int:resource_id>/view')
@login_required
def resource_view(resource_id):
    """View a resource in browser (PDFs/images inline, Word/PowerPoint with viewer)"""
    resource = query_db('''
        SELECT r.*, ff.stored_in_db, ff.code as format_code
        FROM resources r
        LEFT JOIN file_formats ff ON r.file_format_id = ff.id
        WHERE r.id = ?
    ''', [resource_id], one=True)
    
    if not resource:
        flash('Resource not found', 'danger')
        return redirect(url_for('index'))
    
    # Check if we're on localhost or production
    is_localhost = request.host.startswith('127.0.0.1') or request.host.startswith('localhost')
    
    # For Word documents
    if resource['format_code'] == 'DOC':
        if is_localhost:
            return render_template('word_viewer.html', resource=resource, is_localhost=True)
        else:
            token = url_serializer.dumps(resource_id, salt='resource-viewer')
            public_url = url_for('resource_public', token=token, _external=True)
            return render_template('word_viewer.html', resource=resource, is_localhost=False, viewer_url=public_url)
    
    # For PowerPoint
    if resource['format_code'] == 'PPTX':
        if is_localhost:
            return render_template('pptx_viewer.html', resource=resource, is_localhost=True)
        else:
            token = url_serializer.dumps(resource_id, salt='resource-viewer')
            public_url = url_for('resource_public', token=token, _external=True)
            return render_template('pptx_viewer.html', resource=resource, is_localhost=False, viewer_url=public_url)
    
    # For PDFs and images, serve directly (BLOB or file_path)
    resolved = _resolve_resource_file(resource)
    if not resolved:
        flash('File not found on server', 'danger')
        return redirect(url_for('element_detail', element_id=resource['element_id']))
    return send_file(resolved[0], mimetype=resolved[1], as_attachment=False)

@app.route('/resource/<int:resource_id>/raw')
@login_required
def resource_raw(resource_id):
    """Serve raw resource file (for embedding in viewers)"""
    resource = query_db('SELECT r.* FROM resources r WHERE r.id = ?', [resource_id], one=True)
    if not resource:
        flash('Resource not found', 'danger')
        return redirect(url_for('index'))
    resolved = _resolve_resource_file(resource)
    if not resolved:
        flash('File not found on server', 'danger')
        return redirect(url_for('index'))
    return send_file(resolved[0], mimetype=resolved[1], as_attachment=False)

@app.route('/resource/<int:resource_id>/signed_url')
@login_required
def resource_signed_url(resource_id):
    """Generate a temporary signed URL for external viewers (expires in 1 hour)"""
    # Generate signed token
    token = url_serializer.dumps(resource_id, salt='resource-viewer')
    
    # Return public URL with token
    public_url = url_for('resource_public', token=token, _external=True)
    return jsonify({'url': public_url, 'expires_in': '1 hour'})

@app.route('/public/resource/<token>')
def resource_public(token):
    """Serve resource via temporary signed URL (no login required)"""
    try:
        # Verify token (expires in 1 hour)
        resource_id = url_serializer.loads(token, salt='resource-viewer', max_age=3600)
    except:
        return "This link has expired or is invalid. Please generate a new viewing link.", 403
    
    resource = query_db('SELECT r.* FROM resources r WHERE r.id = ?', [resource_id], one=True)
    if not resource:
        return "Resource not found", 404
    resolved = _resolve_resource_file(resource)
    if not resolved:
        return "File not found on server", 404
    return send_file(resolved[0], mimetype=resolved[1], as_attachment=False, download_name=resolved[2])

@app.route('/resource/<int:resource_id>/edit', methods=['POST'])
@login_required
def resource_edit(resource_id):
    """Edit resource metadata"""
    resource = query_db('SELECT element_id FROM resources WHERE id = ?', [resource_id], one=True)
    
    if not resource:
        flash('Resource not found', 'danger')
        return redirect(url_for('index'))
    
    element_id = resource['element_id']
    
    # Get form data
    title = request.form.get('title')
    description = request.form.get('description', '')
    resource_category_id = request.form.get('resource_category_id')
    audience = request.form.get('audience', 'both')
    
    if not title or not resource_category_id:
        flash('Title and category are required', 'danger')
        return redirect(url_for('element_detail', element_id=element_id))
    
    # Update resource
    execute_db('''
        UPDATE resources
        SET title = ?, description = ?, resource_category_id = ?, audience = ?
        WHERE id = ?
    ''', [title, description, resource_category_id, audience, resource_id])
    
    flash('Resource updated successfully!', 'success')
    return redirect(url_for('element_detail', element_id=element_id))

@app.route('/resource/<int:resource_id>/delete', methods=['POST'])
@login_required
def resource_delete(resource_id):
    """Delete a resource"""
    resource = query_db('SELECT r.* FROM resources r WHERE r.id = ?', [resource_id], one=True)
    if not resource:
        flash('Resource not found', 'danger')
        return redirect(url_for('index'))
    
    element_id = resource['element_id']
    
    # Delete file from file system if stored on disk
    if resource.get('file_path'):
        fp = resource['file_path'].lstrip('/')
        if '..' not in fp and not fp.startswith('/'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], fp)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
    
    # Delete from database
    execute_db('DELETE FROM resources WHERE id = ?', [resource_id])
    
    flash('Resource deleted successfully!', 'success')
    return redirect(url_for('element_detail', element_id=element_id))

# ============================================================
# PUBLIC API (read-only, for website integration)
# ============================================================

@app.route('/api')
def api_root():
    """API info and available endpoints"""
    base = request.url_root.rstrip('/')
    return jsonify({
        'name': 'AIDB Learning Sequence API',
        'version': '1.0',
        'endpoints': {
            'year_levels': f'{base}/api/year-levels',
            'clusters': f'{base}/api/clusters?year=level-00|level-01|level-02',
            'cluster_detail': f'{base}/api/cluster/<cluster_number>',
            'resource_download': f'{base}/api/resource/<id>/download',
            'stats': f'{base}/api/stats'
        }
    })

def _row_to_dict(row):
    """Convert sqlite3.Row to dict for JSON serialization"""
    return dict(row) if row else None


def _slugify_path_segment(seg):
    """Match frontend toSlug: lowercase, spaces/underscores → hyphens, keep &."""
    if not seg or not isinstance(seg, str):
        return seg
    s = seg.strip()
    if not s:
        return s
    s = re.sub(r'\s+&\s+', '-&-', s)
    s = re.sub(r'[\s_]+', '-', s)
    s = s.lower()
    s = re.sub(r'-+', '-', s).strip('-')
    return s


def _slugify_path(path_after_level):
    """Slugify path after level to match Hostinger (same as frontend slugifyPath)."""
    if not path_after_level or not isinstance(path_after_level, str):
        return path_after_level
    try:
        decoded = unquote(path_after_level.replace('+', ' '))
    except Exception:
        decoded = path_after_level
    segments = decoded.split('/')
    out = []
    for seg in segments:
        slug = _slugify_path_segment(seg)
        out.append(quote(slug, safe='') if slug else seg)
    return '/'.join(out)


def _normalise_file_url(file_url):
    """Rewrite to Hostinger: https://api.theyintercept.com.au/00-learning-sequences/level-0x/...
    Files are at public_html/00-learning-sequences/. Handles old api/files/Level0x and /api/00-learning-sequences/ inputs.
    Slugifies path after level to match frontend and Hostinger file layout."""
    if not file_url or not isinstance(file_url, str):
        return file_url
    # Hostinger: learning sequence PDFs are on main domain (theyintercept.com.au), not api subdomain
    base = 'https://theyintercept.com.au'
    file_prefix = '/00-learning-sequences'
    # Already correct (and optionally re-slugify path after level for consistency)
    if file_url.startswith(base + file_prefix + '/'):
        rest = file_url[len(base + file_prefix + '/'):].lstrip('/')
        parts = rest.split('/', 1)
        if parts and parts[0] in ('level-00', 'level-01', 'level-02'):
            path_after = parts[1] if len(parts) > 1 else ''
            if path_after:
                slugged = _slugify_path(path_after)
                return base + file_prefix + '/' + parts[0] + '/' + slugged
        return file_url
    # Strip any host to get path
    if '://' in file_url:
        path_only = file_url.split('://', 1)[1].split('/', 1)[-1] if '/' in file_url.split('://', 1)[1] else ''
    else:
        path_only = file_url.lstrip('/')
    path_only = '/' + path_only if path_only else ''
    level_map = {'Level00': 'level-00', 'Level01': 'level-01', 'Level02': 'level-02'}
    # Old API path: /api/files/Level01/...
    if '/api/files/' in path_only:
        idx = path_only.find('/api/files/') + len('/api/files/')
        rest = path_only[idx:].lstrip('/')
        parts = rest.split('/', 1)
        if parts and parts[0] in level_map:
            path_after = parts[1] if len(parts) > 1 else ''
            slugged = _slugify_path(path_after)
            return base + file_prefix + '/' + level_map[parts[0]] + ('/' + slugged if slugged else '')
    # Already /api/00-learning-sequences/ but wrong host
    if '/api/00-learning-sequences/' in path_only:
        idx = path_only.find('/api/00-learning-sequences/') + len('/api/00-learning-sequences/')
        path_after = path_only[idx:]
        slugged = _slugify_path(path_after)
        return base + file_prefix + '/' + slugged
    # /00-learning-sequences/...
    if '/00-learning-sequences/' in path_only:
        idx = path_only.find('/00-learning-sequences/') + len('/00-learning-sequences/')
        path_after = path_only[idx:]
        slugged = _slugify_path(path_after)
        return base + file_prefix + '/' + slugged
    # Bare level-00|level-01|level-02/... (e.g. https://api.../level-01/...)
    for level in ('level-00', 'level-01', 'level-02'):
        if path_only == '/' + level + '/' or path_only.startswith('/' + level + '/'):
            path_after = path_only[len('/' + level):].lstrip('/')
            slugged = _slugify_path(path_after)
            return base + file_prefix + '/' + level + ('/' + slugged if slugged else '')
    return file_url

@app.route('/api/year-levels')
def api_year_levels():
    """List year levels (level-00, level-01, level-02, etc.)"""
    rows = query_db('SELECT id, code, name, display_order FROM year_levels ORDER BY display_order')
    return jsonify([_row_to_dict(r) for r in rows])

@app.route('/api/stats')
def api_stats():
    """Database stats: resource count, total file size, breakdown by format"""
    total = query_db('''
        SELECT COUNT(*) as count,
               COALESCE(SUM(CASE WHEN file_data IS NOT NULL AND length(file_data) > 0 THEN file_size_bytes ELSE 0 END), 0) as blob_bytes,
               COALESCE(SUM(CASE WHEN file_path IS NOT NULL AND length(file_path) > 0 THEN file_size_bytes ELSE 0 END), 0) as filesystem_bytes
        FROM resources
    ''', one=True)
    by_format = query_db('''
        SELECT ff.code as format_code,
               COUNT(r.id) as count,
               COALESCE(SUM(CASE WHEN r.file_data IS NOT NULL AND length(r.file_data) > 0 THEN r.file_size_bytes ELSE 0 END), 0) as blob_bytes
        FROM resources r
        JOIN file_formats ff ON r.file_format_id = ff.id
        GROUP BY ff.code
        ORDER BY count DESC
    ''')
    blob_mb = (total['blob_bytes'] or 0) / (1024 * 1024)
    fs_mb = (total['filesystem_bytes'] or 0) / (1024 * 1024)
    return jsonify({
        'resource_count': total['count'] or 0,
        'total_blob_bytes': total['blob_bytes'] or 0,
        'total_blob_mb': round(blob_mb, 2),
        'total_filesystem_bytes': total['filesystem_bytes'] or 0,
        'total_filesystem_mb': round(fs_mb, 2),
        'by_format': [
            {
                'format': r['format_code'],
                'count': r['count'],
                'blob_mb': round((r['blob_bytes'] or 0) / (1024 * 1024), 2)
            }
            for r in by_format
        ]
    })

# Map website/year-levels v2 style codes to DB codes (production may use F, Y1, Y2...)
YEAR_CODE_ALIASES = {
    'level00': 'F', 'level01': 'Y1', 'level02': 'Y2', 'level03': 'Y3',
    'level04': 'Y4', 'level05': 'Y5', 'level06': 'Y6',
}

def _normalize_year_code(code):
    """Normalize for lookup: lowercase, no hyphens."""
    if not code:
        return ''
    return (code or '').strip().lower().replace('-', '')

def _resolve_year_code(year_code):
    """Resolve request year param to DB code. Accepts level-00 (→ F), Y1, F, etc."""
    norm = _normalize_year_code(year_code)
    # First try direct match (e.g. level-00 in DB)
    row = query_db('SELECT id, code FROM year_levels WHERE LOWER(TRIM(REPLACE(code, "-", ""))) = ?', [norm], one=True)
    if row:
        return row
    # Map website codes to production DB codes (F, Y1, Y2, ...)
    db_code = YEAR_CODE_ALIASES.get(norm)
    if db_code:
        row = query_db('SELECT id, code FROM year_levels WHERE code = ?', [db_code], one=True)
        if row:
            return row
    return None

@app.route('/api/clusters')
def api_clusters():
    """List clusters for a year level. ?year=level-00|level-01|level-02 or F|Y1|Y2 (default: level-00)."""
    year_code = (request.args.get('year') or 'level-00').strip()
    year_level = _resolve_year_code(year_code)
    if not year_level:
        return jsonify({'error': f'Unknown year: {year_code}'}), 400

    clusters_raw = query_db('''
        SELECT c.id, c.cluster_number, c.title, c.year_level_id, c.strand_id,
               yl.code as year_code, yl.name as year_level_name,
               s.name as strand_name, c.is_published
        FROM clusters c
        LEFT JOIN year_levels yl ON c.year_level_id = yl.id
        LEFT JOIN strands s ON c.strand_id = s.id
        WHERE c.year_level_id = ?
        ORDER BY c.cluster_number
    ''', [year_level['id']])

    clusters = []
    for c in clusters_raw:
        cluster = _row_to_dict(c)
        # Get VC references for this cluster (first URL used as curriculumUrl)
        vc_refs = query_db('''
            SELECT vr.code, vr.url FROM vc_references vr WHERE vr.cluster_id = ?
            ORDER BY vr.id LIMIT 1
        ''', [c['id']], one=True)
        cluster['curriculum_url'] = vc_refs['url'] if vc_refs else None

        # Get elements for this cluster
        elements = query_db('''
            SELECT e.id, e.element_number, e.title, e.learning_objective, e.audio_script,
                   ce.sequence_order,
                   cpa.name as cpa_name, ill.name as load_name, csl.name as stability_name
            FROM cluster_elements ce
            JOIN elements e ON ce.element_id = e.id
            LEFT JOIN cpa_stages cpa ON e.cpa_stage_id = cpa.id
            LEFT JOIN intrinsic_load_levels ill ON e.intrinsic_load_id = ill.id
            LEFT JOIN concept_stability_levels csl ON e.concept_stability_id = csl.id
            WHERE ce.cluster_id = ?
            ORDER BY ce.sequence_order
        ''', [c['id']])
        cluster['elements'] = []
        for el in elements:
            el_dict = _row_to_dict(el)
            # Get resources for this element
            resources = query_db('''
                SELECT r.id, r.title, r.file_name, r.audience, r.file_url, r.drive_url,
                       rc.name as category_name, rc.code as category_code,
                       ff.code as format_code
                FROM resources r
                LEFT JOIN resource_categories rc ON r.resource_category_id = rc.id
                LEFT JOIN file_formats ff ON r.file_format_id = ff.id
                WHERE r.element_id = ?
                ORDER BY rc.display_order, r.title
            ''', [el['id']])
            base_url = _api_base_url()
            el_dict['resources'] = []
            for r in resources:
                file_url = _normalise_file_url(r['file_url'])
                download_url = file_url if file_url else f"{base_url}/api/resource/{r['id']}/download"
                format_code = _format_from_url_or_filename(r['file_url'], r['file_name']) or r['format_code']
                el_dict['resources'].append({
                    'id': r['id'],
                    'title': r['title'],
                    'category': r['category_name'],
                    'category_code': r['category_code'],
                    'format': format_code,
                    'audience': r['audience'],
                    'download_url': download_url,
                    'file_url': file_url,
                    'drive_url': r['drive_url']
                })
            cluster['elements'].append(el_dict)
        clusters.append(cluster)

    return jsonify(clusters)

@app.route('/api/cluster/<int:cluster_number>')
def api_cluster_detail(cluster_number):
    """Get single cluster with elements and resources by cluster_number"""
    cluster = query_db('''
        SELECT c.id, c.cluster_number, c.title, c.rationale, c.sequence_notes,
               yl.code as year_code, yl.name as year_level_name,
               s.name as strand_name, c.is_published
        FROM clusters c
        LEFT JOIN year_levels yl ON c.year_level_id = yl.id
        LEFT JOIN strands s ON c.strand_id = s.id
        WHERE c.cluster_number = ?
    ''', [cluster_number], one=True)
    if not cluster:
        return jsonify({'error': 'Cluster not found'}), 404

    result = _row_to_dict(cluster)
    elements = query_db('''
        SELECT e.id, e.element_number, e.title, e.learning_objective,
               ce.sequence_order,
               cpa.name as cpa_name, ill.name as load_name, csl.name as stability_name
        FROM cluster_elements ce
        JOIN elements e ON ce.element_id = e.id
        LEFT JOIN cpa_stages cpa ON e.cpa_stage_id = cpa.id
        LEFT JOIN intrinsic_load_levels ill ON e.intrinsic_load_id = ill.id
        LEFT JOIN concept_stability_levels csl ON e.concept_stability_id = csl.id
        WHERE ce.cluster_id = ?
        ORDER BY ce.sequence_order
    ''', [cluster['id']])
    base_url = _api_base_url()
    result['elements'] = []
    for el in elements:
        el_dict = _row_to_dict(el)
        el_dict['resources'] = []
        resources = query_db('''
            SELECT r.id, r.title, r.file_name, r.audience, r.file_url, r.drive_url,
               rc.name as category_name, rc.code as category_code,
               ff.code as format_code
            FROM resources r
            LEFT JOIN resource_categories rc ON r.resource_category_id = rc.id
            LEFT JOIN file_formats ff ON r.file_format_id = ff.id
            WHERE r.element_id = ?
            ORDER BY rc.display_order, r.title
        ''', [el['id']])
        for r in resources:
            file_url = _normalise_file_url(r['file_url'])
            download_url = file_url if file_url else f"{base_url}/api/resource/{r['id']}/download"
            format_code = _format_from_url_or_filename(r['file_url'], r['file_name']) or r['format_code']
            el_dict['resources'].append({
                'id': r['id'],
                'title': r['title'],
                'category': r['category_name'],
                'category_code': r['category_code'],
                'format': format_code,
                'audience': r['audience'],
                'download_url': download_url,
                'file_url': file_url,
                'drive_url': r['drive_url']
            })
        result['elements'].append(el_dict)
    return jsonify(result)

@app.route('/api/resource/<int:resource_id>/download')
def api_resource_download(resource_id):
    """Public download/view for a resource (for website links).
    PDFs and images are served inline so browsers preview them directly.
    All other formats (DOCX, PPTX, etc.) are served as attachments."""
    row = query_db('SELECT r.* FROM resources r WHERE r.id = ?', [resource_id], one=True)
    if not row:
        return jsonify({'error': 'Resource not found'}), 404
    # sqlite3.Row has no .get(); convert to dict for _resolve_resource_file and redirect logic
    resource = {k: row[k] for k in row.keys()}

    resolved = _resolve_resource_file(resource)
    if not resolved:
        # Redirect to file_url (e.g. production 00-learning-sequences) when file not stored locally.
        # Use normalised URL to match Hostinger: public_html/00-learning-sequences/ (no /api/ in path)
        file_url = resource.get('file_url')
        if file_url and isinstance(file_url, str) and file_url.strip().startswith('http'):
            redirect_url = _normalise_file_url(file_url.strip())
            return redirect(redirect_url, code=302)
        return jsonify({
            'error': 'File not found',
            'detail': 'Resource file is missing. Run scripts/extract_blobs_to_files.py locally, then upload the database and uploads folder to your server.'
        }), 404

    mime = resolved[1] or 'application/octet-stream'
    inline_types = {'application/pdf', 'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
    as_attachment = mime not in inline_types
    return send_file(
        resolved[0],
        mimetype=mime,
        as_attachment=as_attachment,
        download_name=resolved[2] or 'download'
    )

# ============================================================
# LEARNING SEQUENCE STATIC FILES (Hostinger 00-learning-sequences)
# ============================================================
# When the web server doesn't serve /00-learning-sequences/ directly, the API can
# serve them. Set LEARNING_SEQUENCES_PATH to the full path of the folder on the server
# (e.g. /home/uXXX/domains/api.theyintercept.com.au/public_html/00-learning-sequences).

def _learning_sequences_root():
    root = os.getenv('LEARNING_SEQUENCES_PATH', '').strip()
    if root and os.path.isdir(root):
        return root
    return None

@app.route('/api/debug-learning-sequences')
def debug_learning_sequences():
    """Safe debug: is LEARNING_SEQUENCES_PATH set and a valid directory? (no secrets)."""
    raw = os.getenv('LEARNING_SEQUENCES_PATH', '')
    root = _learning_sequences_root()
    return jsonify({
        'LEARNING_SEQUENCES_PATH_set': bool(raw.strip()),
        'path_is_directory': root is not None,
        'resolved_path': root if root else '(not set or not a directory)',
        'cwd': os.getcwd(),
        'app_dir': os.path.dirname(os.path.abspath(__file__)),
    })

@app.route('/api/00-learning-sequences/<path:filepath>')
def serve_00_learning_sequences(filepath):
    """Serve PDFs and other files from the 00-learning-sequences folder (Hostinger)."""
    root = _learning_sequences_root()
    if not root:
        return jsonify({
            'error': 'Learning sequences path not configured',
            'detail': 'Set LEARNING_SEQUENCES_PATH to the full path of 00-learning-sequences on the server.'
        }), 404
    if '..' in filepath or filepath.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    try:
        return send_from_directory(root, filepath, as_attachment=False)
    except Exception:
        return jsonify({'error': 'File not found'}), 404

# ============================================================
# CLUSTER RESOURCES (REFERENCE MATERIALS)
# ============================================================

@app.route('/cluster_resource/<int:resource_id>/download')
@login_required
def cluster_resource_download(resource_id):
    """Download a cluster resource"""
    resource = query_db('''
        SELECT * FROM cluster_resources WHERE id = ?
    ''', [resource_id], one=True)
    
    if not resource:
        flash('Resource not found', 'danger')
        return redirect(url_for('index'))
    
    if resource['file_data']:
        # Serve from BLOB
        return send_file(
            io.BytesIO(resource['file_data']),
            mimetype=resource['mime_type'],
            as_attachment=True,
            download_name=resource['file_name']
        )
    else:
        flash('File not found', 'danger')
        return redirect(url_for('cluster_detail', cluster_id=resource['cluster_id']))

@app.route('/cluster_resource/<int:resource_id>/view')
@login_required
def cluster_resource_view(resource_id):
    """View a cluster resource inline"""
    resource = query_db('''
        SELECT * FROM cluster_resources WHERE id = ?
    ''', [resource_id], one=True)
    
    if not resource:
        flash('Resource not found', 'danger')
        return redirect(url_for('index'))
    
    if resource['file_data']:
        # Serve from BLOB
        return send_file(
            io.BytesIO(resource['file_data']),
            mimetype=resource['mime_type'],
            as_attachment=False,
            download_name=resource['file_name']
        )
    else:
        flash('File not found', 'danger')
        return redirect(url_for('cluster_detail', cluster_id=resource['cluster_id']))

# ============================================================
# DATABASE SEEDING / UPLOAD (for Railway volume updates)
# ============================================================

_original_max_content = None

@app.before_request
def _allow_large_db_upload():
    """Allow up to 3GB for database upload route"""
    global _original_max_content
    if request.path == '/admin/seed-database' and request.method == 'POST':
        _original_max_content = app.config.get('MAX_CONTENT_LENGTH')
        app.config['MAX_CONTENT_LENGTH'] = DB_UPLOAD_MAX

@app.after_request
def _reset_max_content(resp):
    global _original_max_content
    if _original_max_content is not None:
        app.config['MAX_CONTENT_LENGTH'] = _original_max_content
        _original_max_content = None
    return resp

@app.route('/admin/seed-database', methods=['GET', 'POST'])
def seed_database():
    """Upload database file or download from URL. Protected by admin password.
    Use ?key=YOUR_ADMIN_PASSWORD for auth. Supports:
    - POST multipart: file field with .db file
    - POST JSON: {"url": "https://..."} to download from URL"""
    import urllib.request

    key = request.args.get('key', '')
    expected = os.getenv('ADMIN_PASSWORD', '')
    if not key or key != expected:
        return jsonify({'error': 'Unauthorized'}), 401

    db_path = app.config['DATABASE']

    if request.method == 'GET':
        exists = os.path.exists(db_path)
        size = os.path.getsize(db_path) if exists else 0
        # Return JSON only if explicitly requested
        if request.args.get('format') == 'json':
            return jsonify({
                'database_path': db_path,
                'exists': exists,
                'size_bytes': size,
                'usage': 'POST with file= (multipart) or JSON {"url": "https://..."}'
            })
        return render_template('upload_database.html', exists=exists, size=size, key=key)

    target_dir = os.path.dirname(db_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    tmp_path = db_path + '.tmp'

    # Option 1: Direct file upload (multipart)
    if 'file' in request.files:
        f = request.files['file']
        if f.filename and f.filename.lower().endswith('.db'):
            try:
                f.save(tmp_path)
                os.replace(tmp_path, db_path)
                size = os.path.getsize(db_path)
                # Return HTML for form submissions so user sees friendly message
                if request.content_type and 'multipart' in request.content_type:
                    return f'<html><body style="font-family:sans-serif;padding:2rem;"><h3>Upload complete</h3><p>Database updated: {size / 1024 / 1024:.1f} MB</p><p><a href="/">Back to AIDB</a></p></body></html>'
                return jsonify({'status': 'ok', 'database_path': db_path, 'size_bytes': size})
            except Exception as e:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Upload a .db file'}), 400

    # Option 2: Download from URL
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'Provide file= (multipart) or {"url": "https://..."}'}), 400

    def do_download():
        for f in [tmp_path, db_path]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=1200) as resp:
                with open(tmp_path, 'wb') as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            os.replace(tmp_path, db_path)
            print(f'[seed-db] Download complete: {os.path.getsize(db_path)} bytes')
        except Exception as e:
            print(f'[seed-db] Download failed: {e}')
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    if request.args.get('background') == '1':
        # Run download in background to avoid 502 timeout
        thread = threading.Thread(target=do_download)
        thread.daemon = True
        thread.start()
        return jsonify({
            'status': 'started',
            'message': 'Download running in background. Check in 5–10 min. Use GET ?format=json to verify size.'
        })

    for f in [tmp_path, db_path]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=1200) as resp:
            with open(tmp_path, 'wb') as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
        os.replace(tmp_path, db_path)
        size = os.path.getsize(db_path)
        return jsonify({'status': 'ok', 'database_path': db_path, 'size_bytes': size})
    except Exception as e:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return jsonify({'error': str(e)}), 500


# ============================================================
# RUN
# ============================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
