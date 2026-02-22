from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import hashlib
from functools import wraps
from werkzeug.utils import secure_filename

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-me-in-production-please')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['BLOG_TITLE'] = os.environ.get('BLOG_TITLE', 'root@blog')
app.config['BLOG_SUBTITLE'] = os.environ.get('BLOG_SUBTITLE', 'Заметки сисадмина')
app.config['BLOG_DESC'] = os.environ.get('BLOG_DESC', 'DevOps, Linux, инфраструктура и всякое такое')

ADMIN_LOGIN = os.environ.get('ADMIN_LOGIN', 'admin')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', hashlib.sha256('admin123'.encode()).hexdigest())

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

db = SQLAlchemy(app)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(500))
    tags = db.Column(db.String(300), default='')
    published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]


def make_slug(title):
    import re
    from transliterate import translit
    try:
        slug = translit(title, 'ru', reversed=True)
    except:
        slug = title
    slug = re.sub(r'[^\w\s-]', '', slug.lower())
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    # ensure unique
    base = slug
    i = 1
    while Post.query.filter_by(slug=slug).first():
        slug = f"{base}-{i}"
        i += 1
    return slug


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    tag = request.args.get('tag')
    query = Post.query.filter_by(published=True)
    if tag:
        query = query.filter(Post.tags.contains(tag))
    posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('index.html', posts=posts, tag=tag)


@app.route('/post/<slug>')
def post(slug):
    p = Post.query.filter_by(slug=slug, published=True).first_or_404()
    return render_template('post.html', post=p)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('logged_in'):
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        phash = hashlib.sha256(password.encode()).hexdigest()
        if login == ADMIN_LOGIN and phash == ADMIN_PASSWORD_HASH:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Неверный логин или пароль'
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin_dashboard():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin/dashboard.html', posts=posts)


@app.route('/admin/post/new', methods=['GET', 'POST'])
@login_required
def admin_new_post():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '')
        tags = request.form.get('tags', '')
        published = request.form.get('published') == 'on'
        excerpt = request.form.get('excerpt', '').strip()
        
        if not content:
            flash('Напиши текст статьи :)', 'error')
            return render_template('admin/editor.html', post=None)
        

        slug = make_slug(title)
        post = Post(title=title, slug=slug, content=content,
                    tags=tags, published=published, excerpt=excerpt)
        db.session.add(post)
        db.session.commit()
        flash('Пост опубликован!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/editor.html', post=None)


@app.route('/admin/post/<int:post_id>/preview')
@login_required
def admin_preview_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)  # без фильтра published


@app.route('/admin/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form.get('title', '').strip()
        post.content = request.form.get('content', '')
        post.tags = request.form.get('tags', '')
        post.published = request.form.get('published') == 'on'
        post.excerpt = request.form.get('excerpt', '').strip()
        post.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Пост обновлён!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/editor.html', post=post)


@app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Пост удалён', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/upload', methods=['POST'])
@login_required
def admin_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['file']
    if f and allowed_file(f.filename):
        filename = secure_filename(f.filename)
        # make unique
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(datetime.utcnow().timestamp())}{ext}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(save_path)
        url = url_for('static', filename=f'uploads/{filename}')
        return jsonify({'location': url})
    return jsonify({'error': 'File not allowed'}), 400


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=False, host='0.0.0.0', port=5000)
