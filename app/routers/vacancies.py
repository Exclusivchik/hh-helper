# app/routers/vacancies.py
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

from app.services.hh_api import hh_api_client

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


class HostEnum(str, Enum):
    HH_RU = "hh.ru"
    RABOTA_BY = "rabota.by"
    HH1_AZ = "hh1.az"
    HH_UZ = "hh.uz"
    HH_KZ = "hh.kz"
    HEADHUNTER_GE = "headhunter.ge"
    HEADHUNTER_KG = "headhunter.kg"


class Salary(BaseModel):
    from_: Optional[float] = Field(None, alias='from')
    to: Optional[float] = None
    currency: Optional[str] = None
    gross: Optional[bool] = None


class Employer(BaseModel):
    id: Optional[str] = None  # Может отсутствовать для анонимных работодателей
    name: str
    url: Optional[str] = None
    alternate_url: Optional[str] = None
    logo_urls: Optional[dict] = None
    vacancies_url: Optional[str] = None
    trusted: Optional[bool] = None


class Snippet(BaseModel):
    requirement: Optional[str] = None
    responsibility: Optional[str] = None


class VacancyResponse(BaseModel):
    id: str
    name: str
    salary: Optional[Salary] = None
    employer: Employer
    snippet: Snippet
    area: Optional[dict] = None
    url: Optional[str] = None
    alternate_url: Optional[str] = None
    published_at: str
    created_at: str
    archived: bool
    schedule: Optional[dict] = None
    experience: Optional[dict] = None
    employment: Optional[dict] = None


class VacanciesResponse(BaseModel):
    items: List[VacancyResponse]
    found: int
    pages: int
    page: int
    per_page: int
    clusters: Optional[dict] = None
    arguments: Optional[dict] = None


@router.get("", response_model=VacanciesResponse)
async def search_vacancies(
        page: int = Query(0, ge=0, description="Номер страницы"),
        per_page: int = Query(10, le=100, description="Количество элементов"),
        text: Optional[str] = Query(None, description="Текст для поиска"),
        search_field: Optional[List[str]] = Query(None, description="Область поиска"),
        experience: Optional[List[str]] = Query(None, description="Опыт работы"),
        employment: Optional[List[str]] = Query(None, description="Тип занятости (deprecated)"),
        schedule: Optional[List[str]] = Query(None, description="График работы (deprecated)"),
        area: Optional[List[str]] = Query(None, description="Регион"),
        metro: Optional[List[str]] = Query(None, description="Метро"),
        professional_role: Optional[str] = Query(None, description="Профессиональная область"),
        industry: Optional[List[str]] = Query(None, description="Индустрия компании"),
        employer_id: Optional[List[str]] = Query(None, description="Идентификатор работодателя"),
        currency: Optional[str] = Query(None, description="Код валюты"),
        salary: Optional[float] = Query(None, ge=0, description="Размер заработной платы"),
        label: Optional[List[str]] = Query(None, description="Фильтр по меткам вакансий"),
        only_with_salary: bool = Query(False, description="Только с указанием зарплаты"),
        period: Optional[int] = Query(None, ge=1, description="Количество дней для поиска"),
        date_from: Optional[str] = Query(None, description="Дата начала публикации"),
        date_to: Optional[str] = Query(None, description="Дата окончания публикации"),
        top_lat: Optional[float] = Query(None, description="Верхняя граница широты"),
        bottom_lat: Optional[float] = Query(None, description="Нижняя граница широты"),
        left_lng: Optional[float] = Query(None, description="Левая граница долготы"),
        right_lng: Optional[float] = Query(None, description="Правая граница долготы"),
        order_by: Optional[str] = Query(None, description="Сортировка"),
        sort_point_lat: Optional[float] = Query(None, description="Широта для сортировки по расстоянию"),
        sort_point_lng: Optional[float] = Query(None, description="Долгота для сортировки по расстоянию"),
        clusters: bool = Query(False, description="Возвращать ли кластеры"),
        describe_arguments: bool = Query(False, description="Возвращать ли описание параметров"),
        no_magic: bool = Query(False, description="Отключить автоматическое преобразование"),
        premium: bool = Query(False, description="Учитывать премиум-вакансии"),
        responses_count_enabled: bool = Query(False, description="Включить счетчик откликов"),
        part_time: Optional[List[str]] = Query(None, description="Вакансии для подработки (deprecated)"),
        accept_temporary: bool = Query(False, description="Только временная работа"),
        employment_form: Optional[List[str]] = Query(None, description="Тип занятости"),
        work_schedule_by_days: Optional[List[str]] = Query(None, description="График работы"),
        working_hours: Optional[List[str]] = Query(None, description="Рабочие часы в день"),
        work_format: Optional[List[str]] = Query(None, description="Формат работы"),
        excluded_text: Optional[str] = Query(None, description="Исключить слова"),
        education: Optional[List[str]] = Query(None, description="Образование"),
        locale: str = Query("RU", description="Идентификатор локали"),
        host: HostEnum = Query(HostEnum.HH_RU, description="Доменное имя сайта"),

        hh_user_agent: str = Header("HHHelper/1.0 (damir.exclusivchik@example.com)", alias="User-Agent", description="Название приложения и контактная почта"),
        authorization: Optional[str] = Header(None, alias="Authorization", description="OAuth токен")
):
    """
    Поиск по вакансиям через HH.ru API
    """

    # Проверка ограничения глубины результатов (2000)
    if page * per_page >= 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Глубина возвращаемых результатов не может быть больше 2000"
        )

    # Проверка гео-координат
    geo_params = [top_lat, bottom_lat, left_lng, right_lng]
    if any(geo_params) and not all(geo_params):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Все четыре параметра гео-координат должны быть указаны одновременно"
        )

    # Проверка параметров сортировки по расстоянию
    if order_by == "distance" and (sort_point_lat is None or sort_point_lng is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для сортировки по расстоянию необходимо указать sort_point_lat и sort_point_lng"
        )

    # Проверка конфликтующих параметров дат
    if period and (date_from or date_to):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Параметр period нельзя передавать вместе с date_from или date_to"
        )

    # Собираем все параметры запроса
    query_params = {k: v for k, v in locals().items() if
                    k not in ['router', 'hh_api_client', 'hh_user_agent', 'authorization']}

    try:
        # Преобразуем параметры для HH API
        hh_params = hh_api_client.build_hh_params(query_params)

        # Выполняем запрос к HH API
        result = await hh_api_client.search_vacancies(hh_params, hh_user_agent)

        # Обрабатываем ответ
        vacancies_data = {
            "items": result.get("items", []),
            "found": result.get("found", 0),
            "pages": result.get("pages", 0),
            "page": result.get("page", page),
            "per_page": result.get("per_page", per_page)
        }

        # Добавляем опциональные поля
        if clusters and "clusters" in result:
            vacancies_data["clusters"] = result["clusters"]

        if describe_arguments and "arguments" in result:
            vacancies_data["arguments"] = result["arguments"]

        return vacancies_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )