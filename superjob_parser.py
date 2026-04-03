import asyncio
import csv
import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx

BASE_URL = "https://api.superjob.ru/2.0"
SUPERJOB_API_KEY = "v3.r.139734359.24c4e098765e68dafc79a71f1ac4745aef973265.80d9f30bfa1ffef871afe6502aa034bc5e64d61a"

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
    regions = []

    town_obj = item.get("town")
    if isinstance(town_obj, dict) and town_obj.get("title"):
        regions.append(str(town_obj["title"]))

    t_list = item.get("t") or []
    if isinstance(t_list, list):
        for t in t_list:
            if isinstance(t, dict) and t.get("title"):
                regions.append(str(t["title"]))

    # убираем дубли, сохраняя порядок
    unique_regions = list(dict.fromkeys(regions))
    return "; ".join(unique_regions)


def extract_year(date_published_ts: Any) -> Optional[int]:
    if not date_published_ts:
        return None
    try:
        return datetime.utcfromtimestamp(int(date_published_ts)).year
    except Exception:
        return None


def format_salary(
    salary_from: Any,
    salary_to: Any,
    currency: Optional[str],
    agreement: Any,
) -> str:
    salary_from = salary_from or 0
    salary_to = salary_to or 0
    currency = currency or ""

    if agreement:
        return "по договорённости"

    if salary_from and salary_to:
        return f"от {salary_from} до {salary_to} {currency}".strip()
    if salary_from:
        return f"от {salary_from} {currency}".strip()
    if salary_to:
        return f"до {salary_to} {currency}".strip()

    return ""


def build_vacancy_text(item: Dict[str, Any]) -> str:
    profession = clean_html(item.get("profession"))
    work = clean_html(item.get("work"))
    candidat = clean_html(item.get("candidat"))
    compensation = clean_html(item.get("compensation"))

    parts = [profession, work, candidat, compensation]
    return re.sub(r"\s+", " ", " ".join(part for part in parts if part)).strip()


def normalize_vacancy(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "vacancy_url": item.get("link", ""),
        "salary": format_salary(
            item.get("payment_from"),
            item.get("payment_to"),
            item.get("currency"),
            item.get("agreement"),
        ),
        "region": extract_region(item),
        "year_published": extract_year(item.get("date_published")),
        "vacancy_text": build_vacancy_text(item),
    }


class SuperJobVacancyCSVExporter:
    def __init__(self, api_key: str, timeout: float = 30.0):
        if not api_key:
            raise ValueError(
                "Не найден SUPERJOB_API_KEY. "
                "Укажи его в коде или перед запуском выполни:\n"
                "export SUPERJOB_API_KEY='твой_ключ'"
            )

        self.timeout = timeout
        self.headers = {
            "X-Api-App-Id": api_key,
            "Accept": "application/json",
            "User-Agent": "python-httpx-superjob-client/1.0",
        }

    async def fetch_search_page(
        self,
        client: httpx.AsyncClient,
        keyword: str,
        page: int,
        count: int,
        town: Optional[str] = None,
        period: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "keyword": keyword,
            "page": page,
            "count": count,
        }

        if town:
            params["town"] = town
        if period is not None:
            params["period"] = period

        response = await client.get(f"{BASE_URL}/vacancies/", params=params)

        if response.status_code != 200:
            print("STATUS:", response.status_code)
            print("URL:", response.url)
            print("RESPONSE TEXT:", response.text[:2000])
            response.raise_for_status()

        return response.json()

    async def export(
        self,
        queries: List[str],
        output_csv: str = "data/superjob_ai_vacancies.csv",
        town: Optional[str] = None,
        count: int = 100,
        period: Optional[int] = 30,
        delay_between_pages: float = 0.5,
        max_pages_per_query: int = 50,
    ) -> Path:
        if count < 1 or count > 100:
            raise ValueError("count должен быть от 1 до 100")

        rows: List[Dict[str, Any]] = []
        seen_ids: Set[int] = set()

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            for query in queries:
                print(f"\n=== SEARCH: {query} ===")

                for page in range(max_pages_per_query):
                    search_data = await self.fetch_search_page(
                        client=client,
                        keyword=query,
                        page=page,
                        count=count,
                        town=town,
                        period=period,
                    )

                    items = search_data.get("objects", [])
                    print(
                        f"[query={query}] [page={page}] "
                        f"api_items={len(items)} more={search_data.get('more')} total={search_data.get('total')}"
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
                        rows.append(normalize_vacancy(item))
                        added_on_page += 1

                    print(
                        f"[query={query}] [page={page}] "
                        f"added={added_on_page}, dup={duplicates}, total_saved={len(rows)}"
                    )

                    if not search_data.get("more", False):
                        break

                    await asyncio.sleep(delay_between_pages)

        print(f"\nИтог: rows={len(rows)}, unique_ids={len(seen_ids)}")

        if not rows:
            raise RuntimeError("Не удалось собрать ни одной вакансии")

        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
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

        print(f"Сохранено {len(rows)} вакансий в {output_path}")
        return output_path


async def main():
    api_key = SUPERJOB_API_KEY
    # Альтернатива:
    # import os
    # api_key = os.getenv("SUPERJOB_API_KEY", "")

    exporter = SuperJobVacancyCSVExporter(api_key=api_key)

    await exporter.export(
        queries=SEARCH_QUERIES,
        output_csv="data/superjob_ai_vacancies.csv",
        town=None,          # например "Москва" или id города строкой
        count=100,
        period=30,          # вакансии за последние 30 дней
        delay_between_pages=0.5,
        max_pages_per_query=50,   # увеличь при необходимости
    )


if __name__ == "__main__":
    asyncio.run(main())