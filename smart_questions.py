import random
import hashlib
import json
from typing import List, Dict, Set
from datetime import datetime

class SmartQuestionGenerator:
    """
    Умная система генерации вопросов с рандомизацией и персонализацией
    """
    
    def __init__(self):
        # База знаний для каждой профессии
        self.knowledge_base = {
            "HR Specialist": {
                "Recruiter": {
                    "core_areas": [
                        "Методы подбора",
                        "Интервьюирование", 
                        "Sourcing",
                        "Boolean search",
                        "ATS системы",
                        "HR-брендинг"
                    ],
                    "theoretical": [
                        "Психология подбора",
                        "Трудовое право РК",
                        "HR процессы",
                        "Мотивация кандидатов",
                        "Этика рекрутинга"
                    ],
                    "practical": [
                        "LinkedIn/HH.ru работа",
                        "Telegram для рекрутинга",
                        "Проведение интервью",
                        "Оценка кандидатов",
                        "Закрытие вакансий"
                    ],
                    "bonus_skills": [
                        "Executive search",
                        "IT рекрутинг",
                        "Международный подбор",
                        "Employer branding",
                        "Analytics в HR"
                    ]
                },
                "L&D Specialist": {
                    "core_areas": [
                        "Обучение взрослых",
                        "Методы обучения",
                        "LMS системы",
                        "Оценка эффективности",
                        "Instructional Design"
                    ],
                    "theoretical": [
                        "Теории обучения",
                        "Андрагогика",
                        "Психология обучения",
                        "Модели компетенций",
                        "Performance management"
                    ],
                    "practical": [
                        "Создание курсов",
                        "Проведение тренингов",
                        "Работа с LMS",
                        "Оценка ROI обучения",
                        "Gamification"
                    ]
                }
            },
            "Data Scientist": {
                "Computer Vision": {
                    "core_areas": [
                        "Компьютерное зрение",
                        "OpenCV",
                        "PyTorch/TensorFlow",
                        "Обработка изображений",
                        "Deep Learning"
                    ],
                    "theoretical": [
                        "Математика CV",
                        "Алгоритмы обработки",
                        "Нейронные сети",
                        "Архитектуры CNN",
                        "Transfer Learning"
                    ],
                    "practical": [
                        "Детекция объектов",
                        "Сегментация изображений",
                        "OCR системы",
                        "Видеоаналитика",
                        "Production ML"
                    ]
                }
            }
        }
        
        # Шаблоны вопросов для разных типов
        self.question_templates = {
            "definition": [
                "Объясните разницу между {concept1} и {concept2}",
                "Что такое {concept} и когда это используется?",
                "Дайте определение {concept} простыми словами"
            ],
            "practical": [
                "Как бы вы решали задачу {scenario}?",
                "Опишите ваш подход к {task}",
                "Какие инструменты используете для {process}?"
            ],
            "experience": [
                "Расскажите о вашем опыте с {technology}",
                "Приведите пример использования {method}",
                "Какие проблемы возникали при работе с {tool}?"
            ],
            "analysis": [
                "Проанализируйте ситуацию: {scenario}",
                "Какие метрики важны для {process}?",
                "Как оценить эффективность {activity}?"
            ]
        }

    def generate_unique_questions(self, 
                                position: str, 
                                specialization: str, 
                                level: str,
                                candidate_name: str,
                                stage: int,
                                count: int = 5) -> List[Dict]:
        """
        Генерирует уникальные вопросы для кандидата
        """
        
        # 1. Создаем персональный seed для кандидата
        personal_seed = self._create_personal_seed(candidate_name, position, specialization)
        
        # 2. Получаем область знаний
        knowledge_areas = self._get_knowledge_areas(position, specialization)
        
        # 3. Выбираем случайные области для тестирования
        selected_areas = self._select_random_areas(knowledge_areas, count, personal_seed)
        
        # 4. Генерируем вопросы с рандомизацией
        questions = []
        for i, area in enumerate(selected_areas):
            question = self._generate_question_for_area(
                area, position, specialization, level, 
                personal_seed + i, stage
            )
            questions.append(question)
        
        return questions

    def _create_personal_seed(self, candidate_name: str, position: str, specialization: str) -> int:
        """
        Создает персональный seed на основе данных кандидата
        """
        # Комбинируем имя, позицию и текущую дату для уникальности
        seed_string = f"{candidate_name.lower()}{position}{specialization}{datetime.now().strftime('%Y%m%d')}"
        # Создаем хеш для получения числового seed
        hash_object = hashlib.md5(seed_string.encode())
        return int(hash_object.hexdigest()[:8], 16)

    def _get_knowledge_areas(self, position: str, specialization: str) -> Dict:
        """
        Получает области знаний для позиции
        """
        if position in self.knowledge_base and specialization in self.knowledge_base[position]:
            return self.knowledge_base[position][specialization]
        return {"core_areas": [], "theoretical": [], "practical": [], "bonus_skills": []}

    def _select_random_areas(self, knowledge_areas: Dict, count: int, seed: int) -> List[Dict]:
        """
        Выбирает случайные области для тестирования
        """
        random.seed(seed)
        
        # Создаем пул всех областей с типами
        all_areas = []
        
        # Добавляем обязательные области (core_areas)
        for area in knowledge_areas.get("core_areas", []):
            all_areas.append({"area": area, "type": "core", "weight": 3})
        
        # Добавляем теоретические области  
        for area in knowledge_areas.get("theoretical", []):
            all_areas.append({"area": area, "type": "theoretical", "weight": 2})
            
        # Добавляем практические области
        for area in knowledge_areas.get("practical", []):
            all_areas.append({"area": area, "type": "practical", "weight": 2})
            
        # Добавляем бонусные области (с меньшим весом)
        for area in knowledge_areas.get("bonus_skills", []):
            all_areas.append({"area": area, "type": "bonus", "weight": 1})
        
        # Взвешенный случайный выбор
        selected = []
        
        # Обязательно берем минимум 2 core области
        core_areas = [a for a in all_areas if a["type"] == "core"]
        if len(core_areas) >= 2:
            selected.extend(random.sample(core_areas, min(2, len(core_areas))))
        
        # Остальные области выбираем случайно
        remaining_count = count - len(selected)
        remaining_areas = [a for a in all_areas if a not in selected]
        
        if remaining_areas and remaining_count > 0:
            # Взвешенный выбор
            weights = [area["weight"] for area in remaining_areas]
            selected_remaining = random.choices(
                remaining_areas, 
                weights=weights, 
                k=min(remaining_count, len(remaining_areas))
            )
            selected.extend(selected_remaining)
        
        return selected

    def _generate_question_for_area(self, 
                                  area_info: Dict, 
                                  position: str, 
                                  specialization: str,
                                  level: str,
                                  seed: int,
                                  stage: int) -> Dict:
        """
        Генерирует конкретный вопрос для области знаний
        """
        random.seed(seed)
        
        area = area_info["area"]
        area_type = area_info["type"]
        
        # Выбираем тип вопроса в зависимости от этапа и типа области
        if stage == 1:  # Скрининг - простые вопросы
            question_types = ["definition", "practical"]
        elif stage == 2:  # Углубленное - сложные вопросы  
            question_types = ["practical", "experience", "analysis"]
        else:  # Бонусные - специализированные
            question_types = ["experience", "analysis"]
        
        # Добавляем вариативность в зависимости от типа области
        if area_type == "theoretical":
            question_types.extend(["definition"])
        elif area_type == "practical":
            question_types.extend(["practical", "experience"])
        
        question_type = random.choice(question_types)
        
        # Генерируем вопрос
        if area_type == "core" and area == "Методы подбора":
            variations = [
                "Какие методы подбора персонала вы знаете и когда какой использовать?",
                "Опишите процесс активного поиска кандидатов",
                "Как вы работаете с различными источниками кандидатов?",
                "Расскажите о методах оценки кандидатов на первичном этапе"
            ]
        elif area_type == "practical" and area == "LinkedIn/HH.ru работа":
            variations = [
                "Как эффективно искать кандидатов в LinkedIn?",
                "Какие фильтры и операторы поиска вы используете в HH.ru?",
                "Как составить привлекательное сообщение кандидату?",
                "Какие метрики отслеживаете при работе с job-порталами?"
            ]
        elif area_type == "theoretical" and area == "Трудовое право РК":
            variations = [
                "Какие особенности трудового законодательства РК важны для HR?",
                "Как правильно оформить увольнение сотрудника?",
                "Какие документы обязательны при приеме на работу в Казахстане?",
                "Расскажите о правах и обязанностях работодателя по ТК РК"
            ]
        else:
            # Генерируем вопрос на основе шаблонов
            template = random.choice(self.question_templates[question_type])
            variations = [template.format(concept=area, technology=area, method=area, tool=area)]
        
        # Выбираем случайную вариацию
        question_text = random.choice(variations)
        
        return {
            "id": f"q_{hashlib.md5(f'{area}{seed}'.encode()).hexdigest()[:8]}",
            "text": question_text,
            "area": area,
            "type": area_type,
            "question_type": question_type,
            "level": level,
            "stage": stage
        }

# Пример использования
def example_usage():
    """
    Пример того, как использовать систему
    """
    generator = SmartQuestionGenerator()
    
    # Генерируем вопросы для двух разных кандидатов на одну позицию
    questions1 = generator.generate_unique_questions(
        position="HR Specialist",
        specialization="Recruiter", 
        level="middle",
        candidate_name="Айгүл Қасымова",
        stage=1,
        count=5
    )
    
    questions2 = generator.generate_unique_questions(
        position="HR Specialist",
        specialization="Recruiter",
        level="middle", 
        candidate_name="Дамир Алибеков",
        stage=1,
        count=5
    )
    
    print("=== КАНДИДАТ 1: Айгүл Қасымова ===")
    for i, q in enumerate(questions1, 1):
        print(f"{i}. {q['text']} ({q['area']} - {q['type']})")
    
    print("\n=== КАНДИДАТ 2: Дамир Алибеков ===")
    for i, q in enumerate(questions2, 1):
        print(f"{i}. {q['text']} ({q['area']} - {q['type']})")
    
    # Проверяем уникальность
    texts1 = {q['text'] for q in questions1}
    texts2 = {q['text'] for q in questions2}
    overlap = len(texts1.intersection(texts2))
    
    print(f"\n=== АНАЛИЗ УНИКАЛЬНОСТИ ===")
    print(f"Совпадающих вопросов: {overlap}/5")
    print(f"Уникальность: {(5-overlap)/5*100:.1f}%")

if __name__ == "__main__":
    example_usage()