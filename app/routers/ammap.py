# app/routers/ammap.py
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/ammap", tags=["ammap"])

# Настройка путей
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))
data_dir = os.path.join(base_dir, "static", "data")

# Данные регионов России (ID соответствуют AmCharts geodata)
russia_regions = [
    {"id": "RU-AD", "name": "Адыгея", "value": 1000},
    {"id": "RU-AL", "name": "Республика Алтай", "value": 1000},
    {"id": "RU-ALT", "name": "Алтайский край", "value": 1000},
    {"id": "RU-AMU", "name": "Амурская область", "value": 1000},
    {"id": "RU-ARK", "name": "Архангельская область", "value": 1000},
    {"id": "RU-AST", "name": "Астраханская область", "value": 1000},
    {"id": "RU-BA", "name": "Башкортостан", "value": 1000},
    {"id": "RU-BEL", "name": "Белгородская область", "value": 1000},
    {"id": "RU-BRY", "name": "Брянская область", "value": 1000},
    {"id": "RU-BU", "name": "Бурятия", "value": 1000},
    {"id": "RU-CE", "name": "Чеченская Республика", "value": 1000},
    {"id": "RU-CHE", "name": "Челябинская область", "value": 1000},
    {"id": "RU-CHU", "name": "Чукотский автономный округ", "value": 1000},
    {"id": "RU-CU", "name": "Чувашская Республика", "value": 1000},
    {"id": "RU-DA", "name": "Дагестан", "value": 1000},
    {"id": "RU-IN", "name": "Ингушетия", "value": 1000},
    {"id": "RU-IRK", "name": "Иркутская область", "value": 1000},
    {"id": "RU-IVA", "name": "Ивановская область", "value": 1000},
    {"id": "RU-KB", "name": "Кабардино-Балкария", "value": 1000},
    {"id": "RU-KGD", "name": "Калининградская область", "value": 1000},
    {"id": "RU-KL", "name": "Калмыкия", "value": 1000},
    {"id": "RU-KLU", "name": "Калужская область", "value": 1000},
    {"id": "RU-KAM", "name": "Камчатский край", "value": 1000},
    {"id": "RU-KC", "name": "Карачаево-Черкесия", "value": 1000},
    {"id": "RU-KR", "name": "Карелия", "value": 1000},
    {"id": "RU-KEM", "name": "Кемеровская область", "value": 1000},
    {"id": "RU-KHA", "name": "Хабаровский край", "value": 1000},
    {"id": "RU-KK", "name": "Хакасия", "value": 1000},
    {"id": "RU-KHM", "name": "Ханты-Мансийский АО", "value": 1000},
    {"id": "RU-KIR", "name": "Кировская область", "value": 1000},
    {"id": "RU-KO", "name": "Республика Коми", "value": 1000},
    {"id": "RU-KOS", "name": "Костромская область", "value": 1000},
    {"id": "RU-KDA", "name": "Краснодарский край", "value": 1000},
    {"id": "RU-KYA", "name": "Красноярский край", "value": 1000},
    {"id": "RU-KGN", "name": "Курганская область", "value": 1000},
    {"id": "RU-KRS", "name": "Курская область", "value": 1000},
    {"id": "RU-LEN", "name": "Ленинградская область", "value": 1000},
    {"id": "RU-LIP", "name": "Липецкая область", "value": 1000},
    {"id": "RU-MAG", "name": "Магаданская область", "value": 1000},
    {"id": "RU-ME", "name": "Марий Эл", "value": 1000},
    {"id": "RU-MO", "name": "Мордовия", "value": 1000},
    {"id": "RU-MOW", "name": "Москва", "value": 1000},
    {"id": "RU-MOS", "name": "Московская область", "value": 1000},
    {"id": "RU-MUR", "name": "Мурманская область", "value": 1000},
    {"id": "RU-NEN", "name": "Ненецкий АО", "value": 1000},
    {"id": "RU-NIZ", "name": "Нижегородская область", "value": 1000},
    {"id": "RU-SE", "name": "Северная Осетия", "value": 1000},
    {"id": "RU-NGR", "name": "Новгородская область", "value": 1000},
    {"id": "RU-NVS", "name": "Новосибирская область", "value": 1000},
    {"id": "RU-OMS", "name": "Омская область", "value": 1000},
    {"id": "RU-ORE", "name": "Оренбургская область", "value": 1000},
    {"id": "RU-ORL", "name": "Орловская область", "value": 1000},
    {"id": "RU-PNZ", "name": "Пензенская область", "value": 1000},
    {"id": "RU-PER", "name": "Пермский край", "value": 1000},
    {"id": "RU-PRI", "name": "Приморский край", "value": 1000},
    {"id": "RU-PSK", "name": "Псковская область", "value": 1000},
    {"id": "RU-ROS", "name": "Ростовская область", "value": 1000},
    {"id": "RU-RYA", "name": "Рязанская область", "value": 1000},
    {"id": "RU-SA", "name": "Якутия", "value": 1000},
    {"id": "RU-SAK", "name": "Сахалинская область", "value": 1000},
    {"id": "RU-SAM", "name": "Самарская область", "value": 1000},
    {"id": "RU-SAR", "name": "Саратовская область", "value": 1000},
    {"id": "RU-SMO", "name": "Смоленская область", "value": 1000},
    {"id": "RU-SPE", "name": "Санкт-Петербург", "value": 1000},
    {"id": "RU-STA", "name": "Ставропольский край", "value": 1000},
    {"id": "RU-SVE", "name": "Свердловская область", "value": 1000},
    {"id": "RU-TAM", "name": "Тамбовская область", "value": 1000},
    {"id": "RU-TA", "name": "Татарстан", "value": 1000},
    {"id": "RU-TOM", "name": "Томская область", "value": 1000},
    {"id": "RU-TUL", "name": "Тульская область", "value": 1000},
    {"id": "RU-TY", "name": "Тыва", "value": 1000},
    {"id": "RU-TVE", "name": "Тверская область", "value": 1000},
    {"id": "RU-TYU", "name": "Тюменская область", "value": 1000},
    {"id": "RU-UD", "name": "Удмуртия", "value": 1000},
    {"id": "RU-ULY", "name": "Ульяновская область", "value": 1000},
    {"id": "RU-VLA", "name": "Владимирская область", "value": 1000},
    {"id": "RU-VGG", "name": "Волгоградская область", "value": 1000},
    {"id": "RU-VLG", "name": "Вологодская область", "value": 1000},
    {"id": "RU-VOR", "name": "Воронежская область", "value": 1000},
    {"id": "RU-YAN", "name": "Ямало-Ненецкий АО", "value": 1000},
    {"id": "RU-YAR", "name": "Ярославская область", "value": 1000},
    {"id": "RU-YEV", "name": "Еврейская АО", "value": 1000},
    {"id": "RU-ZAB", "name": "Забайкальский край", "value": 1000}
]

@router.get("/", response_class=HTMLResponse)
async def show_am_map(request: Request):
    """
    Отображение интерактивной карты России с регионами using AmCharts
    """
    return templates.TemplateResponse(
        "ammap.html",
        {
            "request": request,
            "regions": russia_regions
        }
    )


@router.get("/regions")
async def get_regions_data():
    """
    API endpoint для получения данных регионов
    """
    return {"regions": russia_regions}


@router.get("/region/{region_id}")
async def get_region_info(region_id: str):
    """
    API endpoint для получения информации о конкретном регионе
    """
    region = next((r for r in russia_regions if r["id"] == region_id), None)
    if not region:
        return {"error": "Регион не найден"}

    # Дополнительная информация о регионе
    region_info = {
        **region,
        "description": f"Регион {region['name']} с населением {region['value']:,} человек",
        "vacancies_count": 1500,  # Примерное количество вакансий
        "average_salary": 65000,  # Примерная средняя зарплата
        "major_industries": ["IT", "Промышленность", "Строительство"]
    }

    return {"region": region_info}


@router.get("/vacancies/{region_id}")
async def get_region_vacancies(region_id: str):
    """
    API endpoint для получения вакансий по региону
    """
    region = next((r for r in russia_regions if r["id"] == region_id), None)
    if not region:
        return {"error": "Регион не найден"}

    # Заглушка для вакансий
    vacancies = [
        {
            "id": 1,
            "title": "Разработчик Python",
            "company": "Технологии Будущего",
            "salary": "120000-150000 руб.",
            "experience": "3+ года",
            "url": "/vacancies/1"
        },
        {
            "id": 2,
            "title": "Data Scientist",
            "company": "Аналитика Про",
            "salary": "140000-180000 руб.",
            "experience": "2+ года",
            "url": "/vacancies/2"
        }
    ]

    return {
        "region": region["name"],
        "vacancies": vacancies,
        "total_count": len(vacancies)
    }