from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import anthropic
import httpx
import uuid
import datetime
import json
import os
from pathlib import Path

# Импортируем настройки
from config import ANTHROPIC_API_KEY, APP_HOST, APP_PORT, DEBUG

# После существующих импортов добавь:
# from database.database import create_tables, get_db
# from database.models import User, Test, TestQuestion
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


# Добавь эти функции после существующих импортов:

async def get_db_connection():
    """Получить подключение к БД"""
    import asyncpg
    from config import DATABASE_URL
    clean_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(clean_url)

async def create_user_if_not_exists(email: str, password: str, name: str, role: str, department: str):
    """Создать пользователя если не существует"""
    conn = await get_db_connection()
    try:
        # Проверяем существует ли пользователь
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
        if not existing:
            await conn.execute(
                "INSERT INTO users (email, password_hash, name, role, department) VALUES ($1, $2, $3, $4, $5)",
                email, password, name, role, department
            )
            print(f"✅ Создан пользователь: {email}")
    finally:
        await conn.close()

async def verify_user_db(email: str, password: str):
    """Проверить пользователя в БД"""
    conn = await get_db_connection()
    try:
        user = await conn.fetchrow(
            "SELECT email, name, role, department FROM users WHERE email = $1 AND password_hash = $2",
            email.lower(), password
        )
        return dict(user) if user else None
    finally:
        await conn.close()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_user_if_not_exists(
        "janaydar@halykbank.kz", 
        "123456", 
        "Жанайдар", 
        "HR Manager", 
        "IT"
    )
    await create_user_if_not_exists(
        "janaydarK@halykbank.kz", 
        "123456", 
        "Жанайдар К.", 
        "Senior HR Manager", 
        "IT"
    )
    print("✅ Тестовые пользователи созданы/проверены")
    
    yield
    
    # Shutdown
    print("🔄 Завершение работы")
    
app = FastAPI(
    title="Qabylda HR Tech Eval", 
    description="Система оценки IT-специалистов для Халык банка",
    lifespan=lifespan
)


# Настраиваем шаблоны и статические файлы
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настраиваем прокси для anthropic (если нужен)
if os.getenv("USE_PROXY"):
    proxy_url = "http://172.27.170.56:3142/"
    httpx_client = httpx.Client(proxy=proxy_url)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, http_client=httpx_client)
else:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Временное хранилище (потом заменим на PostgreSQL)
users_db = {
    "janaydar@halykbank.kz": {
        "password": "123456",
        "name": "Жанайдар",
        "role": "HR Manager",
        "department": "IT",
        "organization": "halyk"
    },
    "janaydarK@halykbank.kz": {
        "password": "123456", 
        "name": "Жанайдар К.",
        "role": "Senior HR Manager",
        "department": "IT",
        "organization": "halyk"
    }
}

test_sessions = {}
organizations = {
    "halyk": {
        "name": "Халык банк",
        "logo": "/static/images/halyk_logo_green.jpg",
        "colors": {
            "primary": "#1DB584",
            "secondary": "#FFD700", 
            "accent": "#2C3E50"
        }
    }
}

# Модели данных
class LoginRequest(BaseModel):
    email: str
    password: str

class TestRequest(BaseModel):
    candidate_name: str
    candidate_email: str
    position: str
    specialization: str = "Общий"
    level: str
    custom_requirements: str = ""
    optional_technologies: list = []

class AnswerRequest(BaseModel):
    question: str
    answer: str
    session_id: str = ""

# Утилиты для аутентификации

def get_organization_from_subdomain(request: Request):
    host = request.headers.get("host", "")
    if "halyk." in host or host.startswith("halyk"):
        return "halyk"
    return "halyk"  # По умолчанию



# ===== ГЛАВНЫЕ СТРАНИЦЫ =====

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница - показывает логин для HR или тест для кандидата"""
    path = request.url.path
    organization = get_organization_from_subdomain(request)
    org_data = organizations[organization]
    
    # Проверяем, есть ли код теста в URL
    if len(path) > 1 and path != "/":
        test_code = path[1:]  # Убираем первый слеш
        # Проверяем, существует ли тест
        if test_code in test_sessions:
            test_data = test_sessions[test_code]
            return templates.TemplateResponse("test_page.html", {
                "request": request,
                "test_code": test_code,
                "test_data": test_data,
                "organization": org_data
            })
        else:
            raise HTTPException(status_code=404, detail="Тест не найден")
    
    # Главная страница - показываем кнопку входа HR
    return templates.TemplateResponse("index.html", {
        "request": request,
        "organization": org_data
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа для HR"""
    organization = get_organization_from_subdomain(request)
    org_data = organizations[organization]
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "organization": org_data
    })

@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    """Обработка входа HR"""
    user = await verify_user_db(email, password)  # ← Новая функция с БД
    if not user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    
    return {
        "status": "success",
        "user": {
            "email": email,
            "name": user["name"],
            "role": user["role"],
            "department": user["department"]
        },
        "redirect": "/dashboard"
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard для HR"""
    organization = get_organization_from_subdomain(request)
    org_data = organizations[organization]
    
    # В реальном проекте здесь будет проверка авторизации
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "organization": org_data
    })

# ===== API ДЛЯ РАБОТЫ С ТЕСТАМИ =====


@app.post("/api/create-test")
async def create_test(test_request: TestRequest):
    """Создание нового теста с сохранением в БД"""
    try:
        # Генерируем уникальный код теста
        test_code = str(uuid.uuid4())[:8].upper()
        
        # Сохраняем в БД
        conn = await get_db_connection()
        try:
            await conn.execute("""
                INSERT INTO tests (test_code, candidate_name, candidate_email, position, level, 
                                 creator_email, custom_requirements, status, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, 'created', $8)
            """, 
                test_code,
                test_request.candidate_name,
                test_request.candidate_email, 
                f"{test_request.position} - {test_request.specialization}",
                test_request.level,
                "hr@halykbank.kz",  # Потом заменим на текущего пользователя
                test_request.custom_requirements,
                datetime.datetime.now() + datetime.timedelta(days=7)
            )
        finally:
            await conn.close()
        
        return {
            "status": "success",
            "test_code": test_code,
            "test_url": f"/{test_code}",
            "message": f"Тест создан для {test_request.candidate_name}"
        }
        
    except Exception as e:
        print(f"Ошибка создания теста: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tests")
async def get_tests(creator_email: Optional[str] = None):
    """Получение списка тестов"""
    tests = []
    
    for test_code, test_data in test_sessions.items():
        # Фильтруем по создателю если указан
        if creator_email and test_data.get("creator_email") != creator_email:
            continue
            
        tests.append({
            "test_code": test_code,
            "candidate_name": f"{test_data['candidate_data'].get('name', '')} {test_data['candidate_data'].get('surname', '')}",
            "position": test_data["position"],
            "level": test_data["level"],
            "status": test_data["status"],
            "created_at": test_data["created_at"].isoformat(),
            "expires_at": test_data["expires_at"].isoformat()
        })
    
    return {
        "status": "success",
        "tests": tests,
        "total": len(tests)
    }
    

# Добавь этот роут после существующих страниц:

@app.get("/create-test", response_class=HTMLResponse)
async def create_test_page(request: Request):
    """Страница создания теста"""
    organization = get_organization_from_subdomain(request)
    org_data = organizations[organization]
    
    return templates.TemplateResponse("create_test.html", {
        "request": request,
        "organization": org_data
    })


@app.get("/test-db") 
async def test_database():
    try:
        import asyncpg
        from config import DATABASE_URL
        
        # Убираем +asyncpg для asyncpg
        clean_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        
        conn = await asyncpg.connect(clean_url)
        
        # Создаем таблицы для HR системы
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                role VARCHAR(100) NOT NULL,
                department VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tests (
                id SERIAL PRIMARY KEY,
                test_code VARCHAR(50) UNIQUE NOT NULL,
                candidate_name VARCHAR(255) NOT NULL,
                candidate_email VARCHAR(255),
                position VARCHAR(100) NOT NULL,
                level VARCHAR(50) NOT NULL,
                creator_email VARCHAR(255) NOT NULL,
                custom_requirements TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                expires_at TIMESTAMP,
                total_score FLOAT DEFAULT 0.0,
                final_evaluation TEXT,
                status VARCHAR(50) DEFAULT 'created',
                duration_minutes INTEGER,
                violations_count INTEGER DEFAULT 0,
                proctoring_data TEXT
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS test_questions (
                id SERIAL PRIMARY KEY,
                test_id INTEGER REFERENCES tests(id) ON DELETE CASCADE,
                question_number INTEGER NOT NULL,
                question_type VARCHAR(50) NOT NULL,
                question_text TEXT NOT NULL,
                answer_text TEXT,
                ai_score FLOAT,
                ai_evaluation TEXT,
                typing_speed FLOAT,
                time_spent_seconds INTEGER,
                answered_at TIMESTAMP
            )
        ''')
        
        # Проверяем созданные таблицы
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        table_names = [row['tablename'] for row in tables]
        
        await conn.close()
        
        return {
            "status": "success", 
            "message": "All tables created successfully!",
            "tables": table_names
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

    
@app.get("/{test_code}", response_class=HTMLResponse)
async def test_page(request: Request, test_code: str):
    """Страница прохождения теста"""
    try:
        # Проверяем существует ли тест
        conn = await get_db_connection()
        test = await conn.fetchrow("SELECT * FROM tests WHERE test_code = $1", test_code)
        await conn.close()
        
        if not test:
            raise HTTPException(status_code=404, detail="Тест не найден")
        
        organization = get_organization_from_subdomain(request)
        org_data = organizations[organization]
        
        return templates.TemplateResponse("test_interface.html", {
            "request": request,
            "test_code": test_code,
            "test": dict(test),
            "organization": org_data
        })
    except Exception as e:
        raise HTTPException(status_code=404, detail="Тест не найден")

# ===== ФУНКЦИИ РАБОТЫ С CLAUDE =====

async def generate_main_question(position: str, level: str, question_number: int, custom_requirements: str = ""):
    """Генерирует основной вопрос"""
    custom_part = f"\n\nДополнительные требования: {custom_requirements}" if custom_requirements else ""
    
    prompt = f"""
    Создай технический вопрос №{question_number} для собеседования на позицию {position} уровня {level} в Халык банке.
    
    Требования:
    - На русском языке
    - Подходящий для уровня {level}
    - Требует развернутого ответа (2-3 предложения минимум)
    - Длина вопроса: максимум 2 предложения
    - Проверяет практические знания для банковской сферы
    - Справедливый и объективный{custom_part}
    
    Верни только сам вопрос, кратко и ясно.
    """
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text.strip()

async def generate_extension_question(position: str, level: str, main_question: str, main_answer: str):
    """Генерирует расширенный вопрос"""
    prompt = f"""
    На основе основного вопроса и ответа создай короткий расширенный вопрос для {position} {level} в банке.

    Основной вопрос: {main_question}
    Ответ: {main_answer}

    Создай один расширенный вопрос который поможет кандидату дополнить ответ.
    Максимум 1 предложение. Конкретный и по делу.

    Верни только вопрос.
    """
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text.strip()

async def evaluate_answer(position: str, level: str, question: str, answer: str):
    """Оценивает ответ кандидата"""
    prompt = f"""
    Оцени ответ кандидата на позицию {position} уровня {level} в банке.

    Вопрос: {question}
    Ответ: {answer}

    Критерии оценки (справедливо оценивай, это реальный человек):
    - Правильность фактов
    - Понимание темы
    - Структура ответа
    - Соответствие уровню {level}
    - Применимость в банковской сфере

    Важно: 
    - 10 баллов возможны для отличных ответов
    - 8-9 баллов для хороших ответов  
    - 6-7 для средних
    - 4-5 для слабых
    - 0-3 для неправильных

    Дай только число от 0 до 10.
    """
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}]
    )
    
    evaluation_text = message.content[0].text.strip()
    
    # Извлекаем числовую оценку
    score = 5  # по умолчанию
    try:
        import re
        match = re.search(r'(\d+)', evaluation_text)
        if match:
            score = int(match.group(1))
            score = min(10, max(0, score))  # Ограничиваем 0-10
    except:
        pass
    
    return score

    



# ===== ОБРАБОТКА ОШИБОК =====

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

# ===== ЗАПУСК ПРИЛОЖЕНИЯ =====

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Запуск Qabylda HR Tech Eval")
    print(f"🌐 Будет доступно на: http://{APP_HOST}:{APP_PORT}")
    print(f"🏛️ Халык банк: http://halyk.localhost:{APP_PORT}")
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, reload=DEBUG)