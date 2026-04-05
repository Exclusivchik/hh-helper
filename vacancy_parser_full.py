import asyncio
import csv
import html
import re
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


def join_names(items: Any) -> str:
    if not isinstance(items, list):
        return ""

    result: List[str] = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name")
            if name:
                result.append(clean_html(str(name)))
        elif isinstance(item, str):
            result.append(clean_html(item))

    return " | ".join(x for x in result if x)


class StopEnrichmentError(Exception):
    pass


class VacancyNotFoundError(Exception):
    pass


class HHVacancyEnricher:
    FIELDNAMES = [
        "vacancy_id",
        "vacancy_url",
        "name",
        "description_clean",
        "snippet_requirement",
        "snippet_responsibility",
        "key_skills",
        "professional_roles",
        "area_name",
        "experience_name",
        "schedule_name",
        "employment_name",
        "work_format",
        "internship",
        "salary_from",
        "salary_to",
        "salary_currency",
        "salary_gross",
        "employer_name",
        "published_at",
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

        if response.status_code == 404:
            raise VacancyNotFoundError(f"Вакансия не найдена: vacancy_id={vacancy_id}")

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

    def build_row(self, detail: Dict[str, Any], ref: Dict[str, Any]) -> Dict[str, Any]:
        snippet = detail.get("snippet") or {}
        salary = detail.get("salary") or {}
        area = detail.get("area") or {}
        employer = detail.get("employer") or {}
        experience = detail.get("experience") or {}
        schedule = detail.get("schedule") or {}
        employment = detail.get("employment") or {}

        work_format = detail.get("work_format")
        if not work_format:
            work_format = []

        return {
            "vacancy_id": str(detail.get("id") or ref.get("vacancy_id", "")).strip(),
            "vacancy_url": detail.get("alternate_url") or ref.get("vacancy_url", ""),
            "name": clean_html(detail.get("name")),
            "description_clean": clean_html(detail.get("description")),
            "snippet_requirement": clean_html(snippet.get("requirement")),
            "snippet_responsibility": clean_html(snippet.get("responsibility")),
            "key_skills": join_names(detail.get("key_skills") or []),
            "professional_roles": join_names(detail.get("professional_roles") or []),
            "area_name": clean_html(area.get("name")),
            "experience_name": clean_html(experience.get("name")),
            "schedule_name": clean_html(schedule.get("name")),
            "employment_name": clean_html(employment.get("name")),
            "work_format": join_names(work_format),
            "internship": bool(detail.get("internship", False)),
            "salary_from": salary.get("from"),
            "salary_to": salary.get("to"),
            "salary_currency": salary.get("currency"),
            "salary_gross": salary.get("gross"),
            "employer_name": clean_html(employer.get("name")),
            "published_at": detail.get("published_at"),
        }

    async def enrich(
        self,
        refs_csv: str = "data/hh_vacancy_refs.csv",
        output_csv: str = "data/hh_vacancies_train.csv",
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
        skipped_404 = 0
        errors = 0

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            for i, ref in enumerate(refs, start=1):
                vacancy_id = str(ref["vacancy_id"]).strip()

                try:
                    detail = await self.fetch_vacancy_detail(client, vacancy_id)
                    row = self.build_row(detail, ref)

                    self.append_row(output_path, row)
                    processed_ids.add(vacancy_id)
                    saved_now += 1

                except VacancyNotFoundError:
                    skipped_404 += 1
                    print(f"[{i}/{len(refs)}] vacancy_id={vacancy_id} skipped (404)")

                except StopEnrichmentError as e:
                    print()
                    print("Скрипт остановлен безопасно.")
                    print(str(e))
                    print(f"Сейчас уже сохранено в файл: {saved_now}")
                    print(f"Пропущено 404: {skipped_404}")
                    print(f"Всего обработано с учётом прошлых запусков: {len(processed_ids)}")
                    return output_path

                except Exception as e:
                    errors += 1
                    print(f"[{i}/{len(refs)}] vacancy_id={vacancy_id} error={e}")

                if i % 25 == 0:
                    print(
                        f"Прогресс: {i}/{len(refs)} | "
                        f"сохранено в этом запуске: {saved_now} | "
                        f"пропущено 404: {skipped_404} | "
                        f"ошибок: {errors}"
                    )

                await asyncio.sleep(self.detail_delay)

        print()
        print(f"Готово. Сохранено в этом запуске: {saved_now}")
        print(f"Пропущено 404: {skipped_404}")
        print(f"Ошибок: {errors}")
        print(f"Итоговый файл: {output_path}")
        return output_path


async def main():
    enricher = HHVacancyEnricher(timeout=30.0, detail_delay=0.15)

    await enricher.enrich(
        refs_csv="id_ml_dl.csv",
        output_csv="full_data.csv",
    )


if __name__ == "__main__":
    asyncio.run(main())
