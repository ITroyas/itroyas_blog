# 🖥️ Sysadmin Blog

Блог сисадмина/DevOps на Flask + SQLite + TinyMCE. Тёмная тема, редактор с WYSIWYG, загрузка картинок.

## Быстрый старт на VPS

### 1. Установка зависимостей

```bash
cd /opt
git clone <твой-репо> blog  # или загрузи файлы через scp/rsync
cd blog

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройка (создай файл .env или экспортируй переменные)

```bash
export SECRET_KEY="замени-на-длинную-случайную-строку"
export BLOG_TITLE="root@server"
export BLOG_SUBTITLE="Заметки DevOps инженера"
export BLOG_DESC="Linux, Docker, Kubernetes и всё такое"

# Логин и пароль для админки
export ADMIN_LOGIN="admin"

# Хэш пароля — генерируй так:
# python3 -c "import hashlib; print(hashlib.sha256('твой_пароль'.encode()).hexdigest())"
export ADMIN_PASSWORD_HASH="8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"
# ↑ это хэш слова "admin" — ОБЯЗАТЕЛЬНО ЗАМЕНИ!
```

### 3. Инициализация БД

```bash
source venv/bin/activate
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
mkdir -p static/uploads
```

### 4. Запуск через systemd

```bash
sudo nano /etc/systemd/system/blog.service
```

```ini
[Unit]
Description=Sysadmin Blog
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/blog
Environment="SECRET_KEY=замени-меня"
Environment="ADMIN_LOGIN=admin"
Environment="ADMIN_PASSWORD_HASH=твой-хэш"
Environment="BLOG_TITLE=root@server"
Environment="BLOG_SUBTITLE=Заметки DevOps"
Environment="BLOG_DESC=Linux, Docker и всё такое"
ExecStart=/opt/blog/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable blog
sudo systemctl start blog
```

### 5. Nginx как реверс-прокси

```bash
sudo nano /etc/nginx/sites-available/blog
```

```nginx
server {
    listen 80;
    server_name твой-домен.com;

    client_max_body_size 20M;

    location /static/ {
        alias /opt/blog/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/blog /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. HTTPS (бесплатно через Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d твой-домен.com
```

## Смена пароля

```bash
python3 -c "import hashlib; print(hashlib.sha256('новый_пароль'.encode()).hexdigest())"
```
Вставь результат в ADMIN_PASSWORD_HASH и перезапусти сервис.

## Структура

```
blog/
├── app.py              # Flask приложение
├── requirements.txt
├── templates/
│   ├── index.html      # Главная страница
│   ├── post.html       # Страница поста
│   └── admin/
│       ├── login.html  # Вход в админку
│       ├── dashboard.html
│       └── editor.html # Редактор (TinyMCE)
├── static/
│   ├── css/style.css
│   └── uploads/        # Загруженные картинки
└── blog.db             # SQLite база (создаётся автоматически)
```

## Возможности

- ✅ Тёмная тема (как у настоящего сисадмина)
- ✅ WYSIWYG редактор TinyMCE (бесплатный, без API ключа)
- ✅ Загрузка изображений прямо в редакторе
- ✅ Подсветка синтаксиса кода (bash, python, yaml, docker...)
- ✅ Авторизация через логин/пароль (хэшированный)
- ✅ Теги и фильтрация по тегам
- ✅ Черновики (published/draft)
- ✅ Краткое описание для главной
- ✅ Ctrl+S в редакторе для сохранения
- ✅ Пагинация
- ✅ SEO-friendly URL slugs (транслитерация с русского)
