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
        
        # СОЗДАЕМ ТАБЛИЦЫ (как было раньше)
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
        
        # ПРОВЕРЯЕМ СОЗДАННЫЕ ТАБЛИЦЫ
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        table_names = [row['tablename'] for row in tables]
        
        # СМОТРИМ ДАННЫЕ В ТАБЛИЦАХ
        data = {}
        
        # Пользователи
        users = await conn.fetch("SELECT email, name, role, created_at FROM users LIMIT 5")
        data['users'] = [dict(row) for row in users]
        
        # Тесты
        tests = await conn.fetch("SELECT test_code, candidate_name, position, level, status, created_at FROM tests LIMIT 5")
        data['tests'] = [dict(row) for row in tests]
        
        # Вопросы тестов
        questions = await conn.fetch("SELECT test_id, question_number, question_type, answered_at FROM test_questions LIMIT 5")
        data['test_questions'] = [dict(row) for row in questions]
        
        await conn.close()
        
        return {
            "status": "success", 
            "message": "Tables created successfully + data shown!",
            "tables": table_names,
            "data": data
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
    
@app.get("/admin-db", response_class=HTMLResponse)
async def admin_database_view(request: Request):
    """Красивый просмотр данных БД"""
    try:
        import asyncpg
        from config import DATABASE_URL
        
        clean_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(clean_url)
        
        # Получаем данные
        users = await conn.fetch("SELECT * FROM users ORDER BY created_at DESC")
        tests = await conn.fetch("SELECT * FROM tests ORDER BY created_at DESC")
        questions = await conn.fetch("SELECT * FROM test_questions ORDER BY id DESC LIMIT 10")
        
        await conn.close()
        
        return templates.TemplateResponse("admin_db.html", {
            "request": request,
            "users": [dict(row) for row in users],
            "tests": [dict(row) for row in tests],
            "questions": [dict(row) for row in questions]
        })
    except Exception as e:
        return f"<h1>Ошибка: {e}</h1>"

    
@app.get("/{test_code}/stage/{stage}", response_class=HTMLResponse)
async def test_stage(request: Request, test_code: str, stage: str):
    """Этапы прохождения теста"""
    try:
        stage = int(stage)  # Конвертируем внутри функции
        print(f"🔍 test_stage called: {test_code}, stage: {stage}")
        
        print("🔍 Connecting to DB...")
        # Проверяем тест
        conn = await get_db_connection()
        test = await conn.fetchrow("SELECT * FROM tests WHERE test_code = $1", test_code)
        print(f"🔍 Test found: {test is not None}")
        
        if not test:
            await conn.close()
            print("❌ Test not found in DB")
            raise HTTPException(status_code=404, detail="Тест не найден")
        
        print("🔍 Checking stage validity...")
        # Проверяем валидность этапа
        if stage not in [1, 2, 3]:
            await conn.close()
            print(f"❌ Invalid stage: {stage}")
            raise HTTPException(status_code=404, detail="Неверный этап")
        
        print("🔍 Updating test status...")
        # Обновляем статус если нужно
        if stage == 1 and test['status'] == 'created':
            await conn.execute(
                "UPDATE tests SET status = 'stage_1', started_at = NOW() WHERE test_code = $1",
                test_code
            )
        
        await conn.close()
        print("🔍 Getting organization...")
        
        organization = get_organization_from_subdomain(request)
        org_data = organizations[organization]
        
        print("🔍 Loading template...")
        return templates.TemplateResponse("test_stage.html", {
            "request": request,
            "test_code": test_code,
            "stage": stage,
            "test": dict(test),
            "organization": org_data
        })
    except HTTPException:
        # Перебрасываем HTTPException как есть
        raise
    except Exception as e:
        print(f"❌ Unexpected error in test_stage: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {e}") 

    
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

    
# Добавь эти endpoints после существующих:

@app.post("/api/stage/{stage}/questions")
async def generate_stage_questions(stage: int, request_data: dict):
    """Генерация вопросов для этапа"""
    try:
        test_code = request_data.get('test_code')
        position = request_data.get('position') 
        level = request_data.get('level')
        
        if stage == 1:
            # Генерируем вопросы скрининга
            questions = await generate_screening_questions(position, level)
        elif stage == 2:
            # Генерируем глубокие вопросы
            questions = await generate_deep_questions(position, level, test_code)
        elif stage == 3:
            # Генерируем вопросы по доп.навыкам
            questions = await generate_bonus_questions(position, level, test_code)
        else:
            raise HTTPException(status_code=400, detail="Неверный этап")
        
        # Сохраняем вопросы в БД
        conn = await get_db_connection()
        try:
            test_id = await conn.fetchval("SELECT id FROM tests WHERE test_code = $1", test_code)
            
            for i, question in enumerate(questions):
                await conn.execute("""
                    INSERT INTO test_questions (test_id, question_number, question_type, question_text)
                    VALUES ($1, $2, $3, $4)
                """, test_id, i + 1, f"stage_{stage}", question['text'])
        finally:
            await conn.close()
        
        return {
            "status": "success",
            "questions": questions
        }
        
    except Exception as e:
        print(f"Ошибка генерации вопросов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stage/{stage}/complete")
async def complete_stage(stage: int, completion_data: dict):
    """Завершение этапа и оценка ответов"""
    try:
        test_code = completion_data.get('test_code')
        answers = completion_data.get('answers', [])
        
        conn = await get_db_connection()
        try:
            # Обновляем ответы в БД
            test_id = await conn.fetchval("SELECT id FROM tests WHERE test_code = $1", test_code)
            
            total_score = 0
            for answer in answers:
                question_id = answer.get('question_id')
                answer_text = answer.get('answer')
                
                # Здесь будет оценка ответа через Claude API
                score = await evaluate_answer_simple(answer_text)
                total_score += score
                
                await conn.execute("""
                    UPDATE test_questions 
                    SET answer_text = $1, ai_score = $2, answered_at = NOW()
                    WHERE id = $3
                """, answer_text, score, question_id)
            
            # Обновляем статус теста
            avg_score = total_score / len(answers) if answers else 0
            
            if stage == 1:
                new_status = 'stage_1_completed'
                await conn.execute("""
                    UPDATE tests 
                    SET status = $1, total_score = $2
                    WHERE test_code = $3
                """, new_status, avg_score, test_code)
            elif stage == 2:
                new_status = 'stage_2_completed'
                await conn.execute("""
                    UPDATE tests 
                    SET status = $1, total_score = $2
                    WHERE test_code = $3
                """, new_status, avg_score, test_code)
            elif stage == 3:
                new_status = 'completed'
                await conn.execute("""
                    UPDATE tests 
                    SET status = $1, completed_at = NOW(), total_score = $2
                    WHERE test_code = $3
                """, new_status, avg_score, test_code)
        
        finally:
            await conn.close()
        
        # Определяем следующий этап
        next_stage = None
        if stage == 1 and avg_score >= 6:  # Проходной балл для скрининга
            next_stage = {
                "title": "Углубленное интервью",
                "description": "3 больших вопроса с ИИ-диалогом (15 минут)"
            }
        elif stage == 2:
            next_stage = {
                "title": "Дополнительные навыки", 
                "description": "Бонусные технологии (опционально)"
            }
        
        return {
            "status": "success",
            "score": f"{avg_score:.1f}/10",
            "next_stage": next_stage,
            "message": "Этап завершен успешно!"
        }
        
    except Exception as e:
        print(f"Ошибка завершения этапа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_screening_questions(position: str, level: str, specialization: str = "Общий"):
    try:
        print(f"🤖 Генерируем вопросы для {position} - {specialization} ({level})")
        
        # Определяем required_skills (твой существующий код)
        required_skills = []
        if position == "Data Scientist":
            if specialization == "Computer Vision":
                required_skills = ["Python", "Машинное обучение", "Компьютерное зрение", "OpenCV", "PyTorch"]
            # ... остальные специализации
        elif position == "HR Specialist":
            if specialization == "Recruiter":
                required_skills = ["Методы подбора", "Интервьюирование", "LinkedIn/HH.ru", "Sourcing", "Boolean search"]
            # ... остальные
        
        # ПРАВИЛЬНЫЙ импорт для версии 1.x
        from openai import OpenAI
        from config import OPENAI_API_KEY
        
        client_openai = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""
        Создай 5 вопросов для СКРИНИНГА кандидата на позицию {position} - {specialization} уровня {level}.
        
        ЦЕЛЬ СКРИНИНГА: Отсеять 30-40% неподходящих кандидатов на раннем этапе.
        
        ОБЯЗАТЕЛЬНЫЕ ОБЛАСТИ для проверки: {', '.join(required_skills)}
        
        ТРЕБОВАНИЯ К ВОПРОСАМ:
        - На русском языке
        - ПОВЕРХНОСТНАЯ проверка базовых знаний
        - Хороший {level} специалист должен легко ответить
        
        Верни JSON массив: [{{"text": "Вопрос 1", "skill_area": "Python"}}, ...]
        """
        
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        
        import json
        questions = json.loads(response.choices[0].message.content)
        
        for i, question in enumerate(questions):
            question['id'] = f"q{i+1}"
        
        print(f"✅ Сгенерировано {len(questions)} скрининг-вопросов")
        return questions
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: ИИ не смог сгенерировать вопросы!")
        print(f"❌ Причина: {e}")
        raise HTTPException(status_code=503, detail=f"Ошибка ИИ: {str(e)}")

async def generate_deep_questions(position: str, level: str, test_code: str):
    """Генерация глубоких вопросов для этапа 2"""
    # Пока заглушка
    return [
        {"id": "deep1", "text": "Расскажите о своем самом сложном проекте в области данных"},
        {"id": "deep2", "text": "Как бы вы решали задачу прогнозирования для банка?"},
        {"id": "deep3", "text": "Объясните архитектуру ML pipeline в production"}
    ]

async def generate_bonus_questions(position: str, level: str, test_code: str):
    """Генерация вопросов по дополнительным навыкам"""
    # Пока заглушка
    return [
        {"id": "bonus1", "text": "Опыт работы с Docker контейнерами"},
        {"id": "bonus2", "text": "Знание облачных платформ AWS/GCP"}
    ]

async def evaluate_answer_simple(answer_text: str):
    """Простая оценка ответа (потом улучшим)"""
    # Пока простая оценка по длине
    if len(answer_text) < 50:
        return 3
    elif len(answer_text) < 150:
        return 6
    else:
        return 8


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