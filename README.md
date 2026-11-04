# VD — Платформа совместного синхронного просмотра

Смотрите видео, фильмы, YouTube и стримы вместе на расстоянии с идеальной синхронизацией секунда в секунду.

---

## 🚀 Быстрый запуск локально

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите сервер:
```bash
python app.py
```

3. Откройте в браузере: `http://localhost:5050`

---

## ☁️ Развёртывание в облаке за 2 минуты (Render или Koyeb)

### Вариант A: Koyeb (Работает 24/7 без засыпания, бесплатно)
1. Загрузите этот проект в свой новый репозиторий на [GitHub](https://github.com/).
2. Зарегистрируйтесь на [Koyeb.com](https://www.koyeb.com/) и нажмите **Create App**.
3. Выберите **GitHub**, укажите ваш репозиторий.
4. Выберите тариф **Free Eco/Nano** ($0/mo).
5. Нажмите **Deploy** — через 60 секунд сайт получит бесплатный публичный HTTPS-домен.

### Вариант B: Render.com (Без привязки карты, бесплатно)
1. Загрузите этот проект в свой новый репозиторий на [GitHub](https://github.com/).
2. Зарегистрируйтесь на [Render.com](https://render.com/) и нажмите **New +** -> **Web Service**.
3. Подключите репозиторий с GitHub.
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app`
6. Выберите тариф **Free** ($0/mo) и нажмите **Deploy**.

---

## 🛠 Технологии
- **Backend**: Python 3, Flask, Flask-SocketIO, Eventlet
- **Sync Engine**: Высокоточный мульти-городской алгоритм синхронизации дрифта
- **Player**: Custom HTML5 Player, HLS.js, YouTube IFrame API
- **UI**: Vanilla JS, Pure CSS (Dark Minimal Theater Mode)
