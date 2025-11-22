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


hh_api_client = HHAPIClient()