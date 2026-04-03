import asyncio
import csv
import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx

BASE_URL = "https://api.hh.ru"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"

CORE_QUERIES = [
    "machine learning engineer",
    "ml engineer",
    "deep learning engineer",
    "research engineer",
    "инженер машинного обучения",
    "разработчик машинного обучения",
    "ml разработчик",
    "инженер по глубокому обучению",
]

LLM_NLP_QUERIES = [
    "llm engineer",
    "rag engineer",
    "nlp engineer",
    "large language models",
    "retrieval augmented generation",
    "transformers",
    "huggingface",
    "инженер llm",
    "инженер nlp",
    "языковые модели",
    "большие языковые модели",
    "обработка естественного языка",
    "дообучение моделей",
]

CV_QUERIES = [
    "computer vision engineer",
    "cv engineer",
    "computer vision",
    "инженер компьютерного зрения",
    "компьютерное зрение",
]

DS_QUERIES = [
    "data scientist",
    "senior data scientist",
    "lead data scientist",
    "applied scientist",
    "research scientist",
    "predictive modeling",
    "statistical learning",
    "дата саентист",
    "дата сайентист",
    "специалист по машинному обучению",
    "исследователь данных",
    "статистическое моделирование",
]

SEARCH_QUERIES = CORE_QUERIES + LLM_NLP_QUERIES + CV_QUERIES + DS_QUERIES


def clean_html(text: Optional[str]) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_region(item: Dict[str, Any]) -> str:
    area = item.get("area") or {}
    return clean_html(area.get("name"))


def extract_year(item: Dict[str, Any]) -> Optional[int]:
    published_at = item.get("published_at")
    if not published_at:
        return None

    try:
        return datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%S%z").year
    except Exception:
        try:
            return datetime.fromisoformat(str(published_at).replace("Z", "+00:00")).year
        except Exception:
            return None


def format_salary(salary: Optional[Dict[str, Any]]) -> str:
    salary = salary or {}
    salary_from = salary.get("from")
    salary_to = salary.get("to")
    currency = salary.get("currency") or ""
    gross = salary.get("gross")

    gross_text = ""
    if gross is True:
        gross_text = " gross"
    elif gross is False:
        gross_text = " net"

    if salary_from and salary_to:
        return f"от {salary_from} до {salary_to} {currency}{gross_text}".strip()
    if salary_from:
        return f"от {salary_from} {currency}{gross_text}".strip()
    if salary_to:
        return f"до {salary_to} {currency}{gross_text}".strip()

    return ""


def build_full_vacancy_text(item: Dict[str, Any]) -> str:
    name = clean_html(item.get("name"))

    employer = item.get("employer") or {}
    employer_name = clean_html(employer.get("name"))

    description = clean_html(item.get("description"))

    snippet = item.get("snippet") or {}
    requirement = clean_html(snippet.get("requirement"))
    responsibility = clean_html(snippet.get("responsibility"))

    key_skills = item.get("key_skills") or []
    skill_names: List[str] = []
    if isinstance(key_skills, list):
        for skill in key_skills:
            if isinstance(skill, dict) and skill.get("name"):
                skill_names.append(clean_html(skill.get("name")))

    specializations = item.get("specializations") or []
    specialization_names: List[str] = []
    if isinstance(specializations, list):
        for spec in specializations:
            if isinstance(spec, dict) and spec.get("name"):
                specialization_names.append(clean_html(spec.get("name")))

    parts = [
        name,
        employer_name,
        description,
        requirement,
        responsibility,
        " ".join(skill_names),
        " ".join(specialization_names),
    ]

    return re.sub(r"\s+", " ", " ".join(part for part in parts if part)).strip()


def normalize_full_vacancy(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "vacancy_id": item.get("id", ""),
        "vacancy_url": item.get("alternate_url", ""),
        "salary": format_salary(item.get("salary")),
        "region": extract_region(item),
        "year_published": extract_year(item),
        "vacancy_text": build_full_vacancy_text(item),
    }


class HHVacancyCSVExporter:
    def __init__(self, timeout: float = 30.0, detail_delay: float = 0.15):
        self.timeout = timeout
        self.detail_delay = detail_delay
        self.headers = {
            "HH-User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

    async def fetch_search_page(
        self,
        client: httpx.AsyncClient,
        text: str,
        page: int,
        per_page: int,
        area: Optional[str] = None,
        only_with_salary: bool = False,
        period: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "text": text,
            "page": page,
            "per_page": per_page,
        }

        if area:
            params["area"] = str(area)

        if only_with_salary:
            params["only_with_salary"] = True

        if period is not None:
            params["period"] = period

        response = await client.get(f"{BASE_URL}/vacancies", params=params)

        if response.status_code != 200:
            print("SEARCH STATUS:", response.status_code)
            print("SEARCH URL:", response.url)
            print("SEARCH RESPONSE TEXT:", response.text[:3000])
            response.raise_for_status()

        return response.json()

    async def fetch_vacancy_detail(
        self,
        client: httpx.AsyncClient,
        vacancy_id: str,
    ) -> Dict[str, Any]:
        response = await client.get(f"{BASE_URL}/vacancies/{vacancy_id}")

        if response.status_code != 200:
            print("DETAIL STATUS:", response.status_code)
            print("DETAIL URL:", response.url)
            print("DETAIL RESPONSE TEXT:", response.text[:3000])
            response.raise_for_status()

        return response.json()

    async def export(
        self,
        queries: List[str],
        output_csv: str = "data/hh_ai_vacancies_full.csv",
        area: Optional[str] = None,
        per_page: int = 100,
        only_with_salary: bool = False,
        delay_between_pages: float = 1.0,
        max_pages_per_query: int = 20,
        period: Optional[int] = None,
    ) -> Path:
        if per_page < 1 or per_page > 100:
            raise ValueError("per_page должен быть от 1 до 100")

        rows: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        detail_errors = 0

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            for query in queries:
                print(f"\n=== SEARCH: {query} ===")

                for page in range(max_pages_per_query):
                    if page * per_page >= 2000:
                        print(f"[query={query}] достигнут лимит HH API: максимум 2000 результатов на запрос")
                        break

                    search_data = await self.fetch_search_page(
                        client=client,
                        text=query,
                        page=page,
                        per_page=per_page,
                        area=area,
                        only_with_salary=only_with_salary,
                        period=period,
                    )

                    items = search_data.get("items", [])
                    total_pages = search_data.get("pages", 0)
                    found = search_data.get("found", 0)

                    print(
                        f"[query={query}] [page={page}] "
                        f"api_items={len(items)} pages={total_pages} found={found}"
                    )

                    if not items:
                        break

                    added_on_page = 0
                    duplicates = 0

                    for item in items:
                        vacancy_id = item.get("id")
                        if not vacancy_id:
                            continue

                        if vacancy_id in seen_ids:
                            duplicates += 1
                            continue

                        seen_ids.add(vacancy_id)

                        try:
                            detail = await self.fetch_vacancy_detail(client, str(vacancy_id))
                            rows.append(normalize_full_vacancy(detail))
                            added_on_page += 1
                        except Exception as e:
                            detail_errors += 1
                            print(f"[vacancy_id={vacancy_id}] ошибка при загрузке деталей: {e}")
                            continue

                        await asyncio.sleep(self.detail_delay)

                    print(
                        f"[query={query}] [page={page}] "
                        f"added={added_on_page}, dup={duplicates}, total_saved={len(rows)}, detail_errors={detail_errors}"
                    )

                    if page + 1 >= total_pages:
                        break

                    await asyncio.sleep(delay_between_pages)

        if not rows:
            raise RuntimeError("Не удалось собрать ни одной вакансии")

        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "vacancy_id",
            "vacancy_url",
            "salary",
            "region",
            "year_published",
            "vacancy_text",
        ]

        with output_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"\nСохранено {len(rows)} вакансий в {output_path}")
        print(f"Ошибок при загрузке деталей: {detail_errors}")
        return output_path


async def main():
    exporter = HHVacancyCSVExporter(timeout=30.0, detail_delay=0.15)

    await exporter.export(
        queries=SEARCH_QUERIES,
        output_csv="data/hh_ai_vacancies_full.csv",
        area=None,              # например "1" для Москвы
        per_page=100,
        only_with_salary=False,
        delay_between_pages=1.0,
        max_pages_per_query=20, # 20 * 100 = 2000 результатов на запрос
        period=None,            # например 30, если нужны только свежие
    )


if __name__ == "__main__":
    asyncio.run(main())