import os
from pathlib import Path

# ===== API КЛЮЧИ =====

# Claude API ключ (Anthropic) - ОБЯЗАТЕЛЬНО установить в переменных окружения!
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# OpenAI API ключ (резервный)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# ===== НАСТРОЙКИ ПРИЛОЖЕНИЯ =====

# Хост и порт
APP_HOST = os.environ.get("HOST", "0.0.0.0")
APP_PORT = int(os.environ.get("PORT", 8000))

# Режим отладки
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# Секретный ключ для сессий (в продакшене должен быть в переменных окружения)
SECRET_KEY = os.environ.get("SECRET_KEY", "qabylda_halyk_hr_secret_key_2024")

# ===== НАСТРОЙКИ БАЗЫ ДАННЫХ =====

# URL базы данных
if DEBUG:
    # Для разработки - локальный PostgreSQL в Docker
    DATABASE_URL = os.environ.get("DATABASE_URL", 
        "postgresql+asyncpg://hr_user:hr_password_2024@localhost:5432/hr_tech_eval")
else:
    # Для продакшена - Render PostgreSQL 
    DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Альтернативная база для тестов
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_hr_tech_eval.db"

# ===== НАСТРОЙКИ ПРОКСИ =====

# Использовать ли прокси для Claude API (для корпоративных сетей)
USE_PROXY = os.environ.get("USE_PROXY", "false").lower() == "true"
PROXY_URL = os.environ.get("PROXY_URL", "http://172.27.170.56:3142/")

# ===== НАСТРОЙКИ БЕЗОПАСНОСТИ =====

# Время жизни тестовых ссылок (в днях)
TEST_LINK_EXPIRE_DAYS = int(os.environ.get("TEST_LINK_EXPIRE_DAYS", 7))

# Максимальное время прохождения теста (в минутах)
TEST_DURATION_MINUTES = int(os.environ.get("TEST_DURATION_MINUTES", 15))

# Максимальное количество попыток входа
MAX_LOGIN_ATTEMPTS = int(os.environ.get("MAX_LOGIN_ATTEMPTS", 5))

# ===== НАСТРОЙКИ EMAIL =====

# SMTP настройки для отправки ссылок кандидатам
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "hr@halykbank.kz")

# ===== НАСТРОЙКИ ФАЙЛОВ =====

# Директория для статических файлов
STATIC_DIR = Path("static")
TEMPLATES_DIR = Path("templates")
UPLOADS_DIR = Path("uploads")

# Максимальный размер загружаемых файлов (в байтах)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ

# ===== НАСТРОЙКИ ЛОГИРОВАНИЯ =====

# Уровень логирования
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Файл логов
LOG_FILE = os.environ.get("LOG_FILE", "logs/hr_tech_eval.log")

# ===== НАСТРОЙКИ ОРГАНИЗАЦИЙ =====

# Конфигурация для разных организаций
ORGANIZATIONS = {
    "halyk": {
        "name": "Халық банкі • Народный банк Казахстана",
        "short_name": "Халык банк",
        "logo": "/static/images/halyk_logo_green.jpg",
        "favicon": "/static/images/halyk_favicon.ico",
        "colors": {
            "primary": "#1DB584",      # Зеленый Халык банка
            "secondary": "#FFD700",    # Золотистый акцент
            "accent": "#2C3E50",       # Темно-синий
            "background": "#F8FAFC",   # Светлый фон
            "text": "#2D3748"          # Основной текст
        },
        "domain": "halyk.qabylda.com",
        "contact_email": "hr@halykbank.kz",
        "phone": "+7 (727) 244-44-44"
    },
    "forte": {
        "name": "Банк Форте",
        "short_name": "Forte Bank",
        "logo": "/static/images/forte_logo.png",
        "colors": {
            "primary": "#E31E24",
            "secondary": "#FFFFFF",
            "accent": "#2C3E50"
        },
        "domain": "forte.qabylda.com"
    }
}

# ===== НАСТРОЙКИ ТЕСТИРОВАНИЯ =====

# Количество основных вопросов в тесте
MAIN_QUESTIONS_COUNT = 3

# Настройки оценки
EVALUATION_SETTINGS = {
    "excellent_threshold": 8,    # Порог для отличной оценки
    "good_threshold": 6,         # Порог для хорошей оценки
    "pass_threshold": 4,         # Минимальный проходной балл
    "max_score": 10             # Максимальная оценка
}

# Должности и их требования
POSITIONS = {
    "backend": {
        "name": "Backend Developer",
        "technologies": ["Python", "Java", "C#", "Node.js", "SQL", "REST API"],
        "levels": ["junior", "middle", "senior"]
    },
    "frontend": {
        "name": "Frontend Developer", 
        "technologies": ["JavaScript", "React", "Vue.js", "HTML/CSS", "TypeScript"],
        "levels": ["junior", "middle", "senior"]
    },
    "mobile_ios": {
        "name": "iOS Developer",
        "technologies": ["Swift", "Objective-C", "iOS SDK", "Xcode"],
        "levels": ["junior", "middle", "senior"]
    },
    "mobile_android": {
        "name": "Android Developer",
        "technologies": ["Java", "Kotlin", "Android SDK", "Android Studio"],
        "levels": ["junior", "middle", "senior"]
    },
    "devops": {
        "name": "DevOps Engineer",
        "technologies": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux"],
        "levels": ["middle", "senior"]
    },
    "data_science": {
        "name": "Data Scientist",
        "technologies": ["Python", "R", "SQL", "Machine Learning", "Statistics"],
        "levels": ["junior", "middle", "senior"]
    }
}

# ===== НАСТРОЙКИ ПРОКТОРИНГА =====

# Настройки веб-камеры и мониторинга
PROCTORING_SETTINGS = {
    "camera_required": True,
    "fullscreen_required": True,
    "tab_switch_monitoring": True,
    "clipboard_protection": True,
    "max_violations": 5,
    "suspicious_video_duration": 3  # минуты подозрительного видео для сохранения
}

# ===== НАСТРОЙКИ РАЗРАБОТКИ =====

# Тестовые пользователи (только для разработки)
if DEBUG:
    TEST_USERS = {
        "admin@qabylda.com": {
            "password": "admin123",
            "name": "Администратор",
            "role": "Super Admin",
            "department": "IT",
            "organization": "halyk"
        }
    }
else:
    TEST_USERS = {}

# ===== СОЗДАНИЕ ДИРЕКТОРИЙ =====

def create_directories():
    """Создает необходимые директории при запуске"""
    directories = [
        STATIC_DIR / "images",
        STATIC_DIR / "css", 
        STATIC_DIR / "js",
        TEMPLATES_DIR,
        UPLOADS_DIR,
        Path("logs")
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# ===== ПРОВЕРКА КОНФИГУРАЦИИ =====

def validate_config():
    """Проверяет корректность конфигурации"""
    errors = []
    
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_anthropic_key_here":
        errors.append("ANTHROPIC_API_KEY не установлен")
    
    if not SECRET_KEY:
        errors.append("SECRET_KEY не установлен")
    
    if errors:
        print("❌ Ошибки конфигурации:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ Конфигурация корректна")
    return True

# Автоматическая проверка при импорте
if __name__ == "__main__":
    create_directories()
    validate_config()