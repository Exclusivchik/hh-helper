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


class StopEnrichmentError(Exception):
    pass


class HHVacancyEnricher:
    FIELDNAMES = [
        "vacancy_id",
        "vacancy_url",
        "salary",
        "region",
        "year_published",
        "vacancy_text",
    ]

    def __init__(self, timeout: float = 30.0, detail_delay: float = 0.15):
        self.timeout = timeout
        self.detail_delay = detail_delay
        self.headers = {
            "HH-User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

    def ensure_output_file(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not output_path.exists():
            with output_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()

    def load_processed_ids(self, output_path: Path) -> Set[str]:
        processed_ids: Set[str] = set()

        if not output_path.exists():
            return processed_ids

        with output_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vacancy_id = str(row.get("vacancy_id", "")).strip()
                if vacancy_id:
                    processed_ids.add(vacancy_id)

        return processed_ids

    def append_row(self, output_path: Path, row: Dict[str, Any]) -> None:
        with output_path.open("a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writerow(row)

    def is_retryable_stop_error(self, response: httpx.Response) -> bool:
        if response.status_code in {403, 429}:
            return True

        text = response.text.lower()
        markers = [
            "captcha",
            "access denied",
            "blocked",
            "too many requests",
            "rate limit",
        ]
        return any(marker in text for marker in markers)

    async def fetch_vacancy_detail(
        self,
        client: httpx.AsyncClient,
        vacancy_id: str,
    ) -> Dict[str, Any]:
        response = await client.get(f"{BASE_URL}/vacancies/{vacancy_id}")

        if response.status_code != 200:
            if self.is_retryable_stop_error(response):
                raise StopEnrichmentError(
                    f"Остановка из-за ограничения/капчи. "
                    f"status={response.status_code}, vacancy_id={vacancy_id}"
                )

            print("DETAIL STATUS:", response.status_code)
            print("DETAIL URL:", response.url)
            print("DETAIL RESPONSE TEXT:", response.text[:3000])
            response.raise_for_status()

        return response.json()

    async def enrich(
        self,
        refs_csv: str = "data/hh_vacancy_refs.csv",
        output_csv: str = "data/hh_vacancies_full.csv",
    ) -> Path:
        refs_path = Path(refs_csv)
        if not refs_path.exists():
            raise FileNotFoundError(f"Файл не найден: {refs_csv}")

        output_path = Path(output_csv)
        self.ensure_output_file(output_path)

        processed_ids = self.load_processed_ids(output_path)
        print(f"Уже обработано вакансий: {len(processed_ids)}")

        refs: List[Dict[str, str]] = []
        seen_ids_in_refs: Set[str] = set()

        with refs_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vacancy_id = str(row.get("vacancy_id", "")).strip()
                if not vacancy_id:
                    continue
                if vacancy_id in seen_ids_in_refs:
                    continue
                if vacancy_id in processed_ids:
                    continue

                seen_ids_in_refs.add(vacancy_id)
                refs.append(row)

        if not refs:
            print("Новых вакансий для обработки нет")
            return output_path

        print(f"Осталось обработать: {len(refs)}")

        saved_now = 0
        errors = 0

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            for i, ref in enumerate(refs, start=1):
                vacancy_id = str(ref["vacancy_id"]).strip()

                try:
                    detail = await self.fetch_vacancy_detail(client, vacancy_id)

                    row = {
                        "vacancy_id": vacancy_id,
                        "vacancy_url": detail.get("alternate_url", ref.get("vacancy_url", "")),
                        "salary": format_salary(detail.get("salary")),
                        "region": extract_region(detail) or ref.get("region", ""),
                        "year_published": extract_year(detail) or ref.get("year_published"),
                        "vacancy_text": build_full_vacancy_text(detail),
                    }

                    self.append_row(output_path, row)
                    processed_ids.add(vacancy_id)
                    saved_now += 1

                except StopEnrichmentError as e:
                    print()
                    print("Скрипт остановлен безопасно.")
                    print(str(e))
                    print(f"Сейчас уже сохранено в файл: {saved_now}")
                    print(f"Всего обработано с учётом прошлых запусков: {len(processed_ids)}")
                    return output_path

                except Exception as e:
                    errors += 1
                    print(f"[{i}/{len(refs)}] vacancy_id={vacancy_id} error={e}")

                if i % 25 == 0:
                    print(
                        f"Прогресс: {i}/{len(refs)} | "
                        f"сохранено в этом запуске: {saved_now} | "
                        f"ошибок: {errors}"
                    )

                await asyncio.sleep(self.detail_delay)
                    

        print()
        print(f"Готово. Сохранено в этом запуске: {saved_now}")
        print(f"Ошибок: {errors}")
        print(f"Итоговый файл: {output_path}")
        return output_path


async def main():
    enricher = HHVacancyEnricher(timeout=30.0, detail_delay=0.15)

    await enricher.enrich(
        refs_csv="../data/hh_vacancy_refs.csv",
        output_csv="../data/hh_vacancies_full.csv",
    )


if __name__ == "__main__":
    asyncio.run(main())