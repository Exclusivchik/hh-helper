// region.js - Логика загрузки и отображения вакансий для страницы региона

/**
 * Поисковый запрос для ML/AI вакансий
 */
const AI_ML_SEARCH_QUERY = '"внедрение ИИ" OR "AI integration" OR "AI внедрение" OR "AI engineer" OR "AI разработчик" OR "инженер по ИИ" OR "LLM" OR "GPT" OR "языковые модели" OR "RAG" OR "retrieval augmented generation" OR "нейросети" OR "интеграция нейросетей" OR "машинное обучение" OR "ML" OR "ML разработчик" OR "автоматизация ИИ" OR "AI автоматизация" OR "AI solutions" OR "AI решения" OR "AI consultant" OR "консультант по ИИ"';

/**
 * Массив ID профессиональных ролей для ML/AI вакансий
 */
const AI_ML_PROFESSIONAL_ROLES = [156, 160, 10, 12, 150, 25, 165, 34, 36, 73, 155, 96, 164, 104, 157, 107, 112, 113, 148, 114, 116, 121, 124, 125, 126];

/**
 * Загрузка вакансий через API
 * @param {string} areaId - ID региона в HH.ru
 */
async function loadVacancies(areaId) {
    const searchQuery = encodeURIComponent(AI_ML_SEARCH_QUERY);
    // Временно отключаем professional_role - нужно добавить поддержку на бэкенде
    // const professionalRolesParams = AI_ML_PROFESSIONAL_ROLES.map(id => `professional_role=${id}`).join('&');
    const url = `/vacancies?area=${areaId}&per_page=20&text=${searchQuery}`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        const container = document.getElementById('vacancies-list');
        
        if (data.items && data.items.length > 0) {
            const salaryStats = calculateSalaryStats(data.items);
            container.innerHTML = renderSalaryStats(salaryStats) + renderVacancies(data);
        } else {
            container.innerHTML = '<p style="text-align: center; color: #7f8c8d;">Вакансии не найдены</p>';
        }
    } catch (error) {
        document.getElementById('vacancies-list').innerHTML = 
            '<div class="error">Ошибка загрузки вакансий. Попробуйте позже.</div>';
    }
}

/**
 * Расчет статистики по зарплатам
 * @param {Array} vacancies - Массив вакансий
 * @returns {Object} Объект со статистикой
 */
function calculateSalaryStats(vacancies) {
    const salaries = [];
    
    vacancies.forEach(vacancy => {
        if (vacancy.salary) {
            // Берем среднее между from и to, или то что есть
            if (vacancy.salary.from && vacancy.salary.to) {
                salaries.push((vacancy.salary.from + vacancy.salary.to) / 2);
            } else if (vacancy.salary.from) {
                salaries.push(vacancy.salary.from);
            } else if (vacancy.salary.to) {
                salaries.push(vacancy.salary.to);
            }
        }
    });
    
    if (salaries.length === 0) {
        return null;
    }
    
    const min = Math.min(...salaries);
    const max = Math.max(...salaries);
    const avg = salaries.reduce((sum, val) => sum + val, 0) / salaries.length;
    
    return {
        min: Math.round(min),
        max: Math.round(max),
        avg: Math.round(avg),
        count: salaries.length,
        total: vacancies.length
    };
}

/**
 * Рендеринг статистики по зарплатам
 * @param {Object} stats - Статистика по зарплатам
 * @returns {string} HTML строка со статистикой
 */
function renderSalaryStats(stats) {
    if (!stats) {
        return '<div class="salary-stats"><p>Нет данных о зарплатах</p></div>';
    }
    
    return `
        <div class="salary-stats">
            <h3>Статистика по зарплатам</h3>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Минимальная</div>
                    <div class="stat-value">${stats.min.toLocaleString('ru-RU')} ₽</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Средняя</div>
                    <div class="stat-value">${stats.avg.toLocaleString('ru-RU')} ₽</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Максимальная</div>
                    <div class="stat-value">${stats.max.toLocaleString('ru-RU')} ₽</div>
                </div>
            </div>
            <p class="stats-info">На основе ${stats.count} из ${stats.total} вакансий с указанной зарплатой</p>
        </div>
    `;
}

/**
 * Рендеринг списка вакансий
 * @param {Object} data - Данные с вакансиями от API
 * @returns {string} HTML строка с вакансиями
 */
function renderVacancies(data) {
    const countText = `
        <p class="vacancy-count">
            Найдено вакансий: ${data.found.toLocaleString('ru-RU')}
        </p>
    `;
    
    const vacanciesHTML = data.items.map(vacancy => renderVacancyCard(vacancy)).join('');
    
    return countText + vacanciesHTML;
}

/**
 * Рендеринг карточки одной вакансии
 * @param {Object} vacancy - Данные вакансии
 * @returns {string} HTML строка карточки вакансии
 */
function renderVacancyCard(vacancy) {
    const salaryHTML = vacancy.salary ? renderSalary(vacancy.salary) : 
        '<div class="vacancy-salary">Зарплата не указана</div>';
    
    const requirementHTML = vacancy.snippet.requirement || '';
    const responsibilityHTML = vacancy.snippet.responsibility ? 
        '<br><br>' + vacancy.snippet.responsibility : '';
    
    return `
        <div class="vacancy-card">
            <div class="vacancy-title">
                <a href="${vacancy.alternate_url}" target="_blank">${vacancy.name}</a>
            </div>
            <div class="vacancy-company">${vacancy.employer.name}</div>
            ${salaryHTML}
            <div class="vacancy-details">
                ${requirementHTML}
                ${responsibilityHTML}
            </div>
        </div>
    `;
}

/**
 * Рендеринг информации о зарплате
 * @param {Object} salary - Объект с данными о зарплате
 * @returns {string} HTML строка с зарплатой
 */
function renderSalary(salary) {
    const fromText = salary.from ? salary.from.toLocaleString('ru-RU') : '';
    const separator = salary.from && salary.to ? ' - ' : '';
    const toText = salary.to ? salary.to.toLocaleString('ru-RU') : '';
    const currency = salary.currency || 'RUB';
    
    return `
        <div class="vacancy-salary">
            ${fromText}${separator}${toText} ${currency}
        </div>
    `;
}
