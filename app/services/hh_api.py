# app/services/hh_api.py
import httpx
import logging
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class HHAPIClient:
    def __init__(self):
        self.base_url = "https://api.hh.ru"
        self.timeout = 30.0

    async def get_areas(self) -> List[Dict[str, Any]]:
        """
        Получение списка всех регионов из HH.ru API
        """
        url = f"{self.base_url}/areas"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error getting areas from HH API: {str(e)}")
            return []
    
    async def get_professional_roles(self) -> List[Dict[str, Any]]:
        """
        Получение списка профессиональных ролей из HH.ru API
        """
        url = f"{self.base_url}/professional_roles"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Получено {len(data.get('categories', []))} категорий профессиональных ролей")
                return data
        except Exception as e:
            logger.error(f"Error getting professional roles from HH API: {str(e)}")
            return {"categories": []}
    
    async def search_vacancies(self, params: Dict[str, Any], user_agent: str) -> Dict[str, Any]:
        """
        Поиск вакансий через API HH.ru
        """
        url = f"{self.base_url}/vacancies"

        headers = {
            "HH-User-Agent": user_agent,
            "User-Agent": user_agent,
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from HH API: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"HH API returned error: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            logger.error(f"Request error to HH API: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable"
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    def build_hh_params(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Преобразование параметров нашего API в параметры HH API
        """
        hh_params = {}

        # Маппинг параметров
        mapping = {
            'page': 'page',
            'per_page': 'per_page',
            'text': 'text',
            'search_field': 'search_field',
            'experience': 'experience',
            'employment': 'employment',
            'schedule': 'schedule',
            'area': 'area',
            'metro': 'metro',
            'professional_role': 'professional_role',
            'industry': 'industry',
            'employer_id': 'employer_id',
            'currency': 'currency',
            'salary': 'salary',
            'label': 'label',
            'only_with_salary': 'only_with_salary',
            'period': 'period',
            'date_from': 'date_from',
            'date_to': 'date_to',
            'order_by': 'order_by',
            'clusters': 'clusters',
            'describe_arguments': 'describe_arguments',
            'no_magic': 'no_magic',
            'premium': 'premium',
            'responses_count_enabled': 'responses_count_enabled',
            'part_time': 'part_time',
            'accept_temporary': 'accept_temporary',
            'employment_form': 'employment_form',
            'work_schedule_by_days': 'work_schedule_by_days',
            'working_hours': 'working_hours',
            'work_format': 'work_format',
            'excluded_text': 'excluded_text',
            'education': 'education',
            'locale': 'locale'
        }

        # Преобразование параметров
        for our_param, hh_param in mapping.items():
            if our_param in query_params and query_params[our_param] is not None:
                hh_params[hh_param] = query_params[our_param]

        # Особые обработки параметров
        if 'top_lat' in query_params and query_params['top_lat'] is not None:
            hh_params['top_lat'] = query_params['top_lat']
            hh_params['bottom_lat'] = query_params['bottom_lat']
            hh_params['left_lng'] = query_params['left_lng']
            hh_params['right_lng'] = query_params['right_lng']

        if 'sort_point_lat' in query_params and query_params['sort_point_lat'] is not None:
            hh_params['sort_point_lat'] = query_params['sort_point_lat']
            hh_params['sort_point_lng'] = query_params['sort_point_lng']

        return hh_params


def build_region_mapping(areas: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Создает маппинг между названиями регионов и их HH.ru ID
    """
    mapping = {}
    
    def process_area(area: Dict[str, Any]):
        name = area.get('name', '')
        area_id = area.get('id', '')
        if name and area_id:
            mapping[name] = area_id
            # Также добавляем короткие варианты названий
            mapping[name.lower()] = area_id
        
        # Рекурсивно обрабатываем дочерние регионы
        for child in area.get('areas', []):
            process_area(child)
    
    for area in areas:
        process_area(area)
    
    return mapping


def find_area_id_by_name(mapping: Dict[str, str], search_name: str) -> Optional[str]:
    """
    Ищет ID региона по названию с поддержкой частичного совпадения
    """
    search_lower = search_name.lower()
    
    # Точное совпадение
    if search_name in mapping:
        return mapping[search_name]
    
    if search_lower in mapping:
        return mapping[search_lower]
    
    # Частичное совпадение - ищем регион, который содержит искомое слово
    for name, area_id in mapping.items():
        if search_lower in name.lower():
            logger.info(f"Found partial match: '{search_name}' -> '{name}' (ID: {area_id})")
            return area_id
    
    # Ищем наоборот - искомое слово содержит название региона
    for name, area_id in mapping.items():
        if name.lower() in search_lower:
            logger.info(f"Found reverse match: '{search_name}' -> '{name}' (ID: {area_id})")
            return area_id
    
    return None


def get_amcharts_to_hh_mapping() -> Dict[str, str]:
    """
    Маппинг между AmCharts region ID (RU-XXX) и названиями регионов для поиска в HH.ru
    """
    return {
        "RU-AD": "Адыгея",
        "RU-AL": "Республика Алтай",
        "RU-ALT": "Алтайский край",
        "RU-AMU": "Амурская область",
        "RU-ARK": "Архангельская область",
        "RU-AST": "Астраханская область",
        "RU-BA": "Башкортостан",
        "RU-BEL": "Белгородская область",
        "RU-BRY": "Брянская область",
        "RU-BU": "Бурятия",
        "RU-CE": "Чеченская Республика",
        "RU-CHE": "Челябинская область",
        "RU-CHU": "Чукотский автономный округ",
        "RU-CU": "Чувашская Республика",
        "RU-DA": "Дагестан",
        "RU-IN": "Ингушетия",
        "RU-IRK": "Иркутская область",
        "RU-IVA": "Ивановская область",
        "RU-KB": "Кабардино-Балкария",
        "RU-KGD": "Калининградская область",
        "RU-KL": "Калмыкия",
        "RU-KLU": "Калужская область",
        "RU-KAM": "Камчатский край",
        "RU-KC": "Карачаево-Черкесия",
        "RU-KR": "Карелия",
        "RU-KEM": "Кемеровская область",
        "RU-KHA": "Хабаровский край",
        "RU-KK": "Хакасия",
        "RU-KHM": "Ханты-Мансийский АО",
        "RU-KIR": "Кировская область",
        "RU-KO": "Республика Коми",
        "RU-KOS": "Костромская область",
        "RU-KDA": "Краснодарский край",
        "RU-KYA": "Красноярский край",
        "RU-KGN": "Курганская область",
        "RU-KRS": "Курская область",
        "RU-LEN": "Ленинградская область",
        "RU-LIP": "Липецкая область",
        "RU-MAG": "Магаданская область",
        "RU-ME": "Марий Эл",
        "RU-MO": "Мордовия",
        "RU-MOW": "Москва",
        "RU-MOS": "Московская область",
        "RU-MUR": "Мурманская область",
        "RU-NEN": "Ненецкий АО",
        "RU-NIZ": "Нижегородская область",
        "RU-SE": "Северная Осетия",
        "RU-NGR": "Новгородская область",
        "RU-NVS": "Новосибирская область",
        "RU-OMS": "Омская область",
        "RU-ORE": "Оренбургская область",
        "RU-ORL": "Орловская область",
        "RU-PNZ": "Пензенская область",
        "RU-PER": "Пермский край",
        "RU-PRI": "Приморский край",
        "RU-PSK": "Псковская область",
        "RU-ROS": "Ростовская область",
        "RU-RYA": "Рязанская область",
        "RU-SA": "Саха",  # Республика Саха (Якутия) в HH.ru
        "RU-SAK": "Сахалинская область",
        "RU-SAM": "Самарская область",
        "RU-SAR": "Саратовская область",
        "RU-SMO": "Смоленская область",
        "RU-SPE": "Санкт-Петербург",
        "RU-STA": "Ставропольский край",
        "RU-SVE": "Свердловская область",
        "RU-TAM": "Тамбовская область",
        "RU-TA": "Татарстан",
        "RU-TOM": "Томская область",
        "RU-TUL": "Тульская область",
        "RU-TY": "Тыва",
        "RU-TVE": "Тверская область",
        "RU-TYU": "Тюменская область",
        "RU-UD": "Удмуртия",
        "RU-ULY": "Ульяновская область",
        "RU-VLA": "Владимирская область",
        "RU-VGG": "Волгоградская область",
        "RU-VLG": "Вологодская область",
        "RU-VOR": "Воронежская область",
        "RU-YAN": "Ямало-Ненецкий АО",
        "RU-YAR": "Ярославская область",
        "RU-YEV": "Еврейская АО",
        "RU-ZAB": "Забайкальский край"
    }


hh_api_client = HHAPIClient()