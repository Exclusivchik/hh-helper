// ammap.js - AmCharts 5 Map for Russian Regions

// Глобальные переменные
let chart = null;
let polygonSeries = null;
let root = null;
let zoomEnabled = true;
let regionsData = [];
let isZoomedToRegion = false;
let initialMapState = null;  // Сохраняем начальное состояние карты

/**
 * Инициализация карты AmCharts
 */
function initAmMap(regions) {
    regionsData = regions || [];
    console.log('initAmMap вызван с', regionsData.length, 'регионами');
    
    am5.ready(function() {
        try {
            // Создаем корневой элемент
            root = am5.Root.new("chartdiv", {
                autoResize: true,
                tooltipContainerBounds: { top: 0, bottom: 0, left: 0, right: 0 },
                useSafeResolution: false
            });

            // Отключаем анимации для оптимизации
            root.setThemes([]);

            // Создаем карту с правильными настройками для России (статичная для оптимизации)
            const homeSettings = {
                rotationX: -100,
                zoomLevel: 0.75
            };
            
            // Создаем проекцию с настройкой центра
            const projection = am5map.geoMercator();
            
            chart = root.container.children.push(am5map.MapChart.new(root, {
                panX: "none",
                panY: "none",
                projection: projection,
                rotationX: homeSettings.rotationX,
                maxZoomLevel: 8,        // Разрешаем зум для интерактивности
                minZoomLevel: homeSettings.zoomLevel,
                zoomLevel: homeSettings.zoomLevel,        // Начальный зум
                homeZoomLevel: homeSettings.zoomLevel,
                centerMapOnZoomOut: false,
                wheelY: "none",
                wheelX: "none",
                wheelDuration: 0,
                panDuration: 0,
                zoomDuration: 0,
                pinchZoom: false,
                homeGeoPoint: { latitude: 60, longitude: 100 }  // Центральная точка карты
            }));
            
            // Устанавливаем центр проекции
            projection.center([100, 60]);
            
            // Принудительно центрируем карту
            chart.goHome(); 

            // Создаем серию полигонов
            polygonSeries = chart.series.push(am5map.MapPolygonSeries.new(root, {
                geoJSON: am5geodata_russiaLow,
                valueField: "value",
                calculateAggregates: true
            }));
            
            // Сразу сохраняем начальное состояние (центр России примерно)
            initialMapState = {
                longitude: 100,
                latitude: 65,
                zoomLevel: 0.75
            };
            console.log('Начальное состояние установлено:', initialMapState);

            // Базовая настройка полигонов (без анимаций)
            polygonSeries.mapPolygons.template.setAll({
                tooltipText: "{name}",
                interactive: true,
                cursorOverStyle: "pointer",
                stroke: am5.color(0xffffff),
                strokeWidth: 1,
                strokeOpacity: 0.8,
                fill: am5.color(0x3498db),
                templateField: "polygonSettings",
                tooltipPosition: "pointer"
            });

            // Состояние при наведении (без анимации)
            const hoverState = polygonSeries.mapPolygons.template.states.create("hover", {
                fill: am5.color(0xFFA726),
                strokeWidth: 2
            });
            hoverState.set("stateAnimationDuration", 0);

            // Выводим ВСЕ реальные ID из AmCharts geodata для диагностики
            setTimeout(() => {
                console.log('=== ПОЛНЫЙ СПИСОК ID РЕГИОНОВ В AMCHARTS GEODATA ===');
                const allGeoData = [];
                polygonSeries.mapPolygons.each(function(polygon) {
                    const data = polygon.dataItem.dataContext;
                    if (data && data.id) {
                        allGeoData.push({
                            id: data.id,
                            name: data.name || 'Нет имени'
                        });
                    }
                });
                allGeoData.sort((a, b) => a.name.localeCompare(b.name, 'ru'));
                console.table(allGeoData);
                console.log('Всего регионов в geodata:', allGeoData.length);
            }, 1000);
            
            // Устанавливаем данные
            if (regionsData.length > 0) {
                console.log('Установка данных регионов:', regionsData.length);
                polygonSeries.data.setAll(regionsData);
                console.log('polygonSeries создан:', polygonSeries);
                console.log('Количество полигонов:', polygonSeries.mapPolygons.length);
                
                // Ждем инициализации серии полигонов
                polygonSeries.events.once("inited", function() {
                    console.log('polygonSeries инициализирована, ждем 1.5 сек и позиционируем');
                    setTimeout(() => {
                        console.log('НАЧИНАЕМ ПОЗИЦИОНИРОВАНИЕ КАРТЫ');
                        chart.zoomToGeoPoint(
                            { 
                                longitude: initialMapState.longitude, 
                                latitude: initialMapState.latitude 
                            },
                            initialMapState.zoomLevel,
                            true,
                            600
                        );
                        console.log('Карта возвращена к начальному состоянию');
                    }, 1500);
                });
            } else {
                console.warn('Нет данных о регионах для отображения');
            }

            // Настраиваем цветовую схему
            polygonSeries.set("heatRules", [{
                target: polygonSeries.mapPolygons.template,
                dataField: "value",
                min: am5.color(0x81D4FA),
                max: am5.color(0x1565C0),
                key: "fill"
            }]);

            // Ждем создания всех полигонов и устанавливаем обработчики
            setTimeout(() => {
                console.log('Устанавливаем обработчики клика на все полигоны');
                let clickableCount = 0;
                
                polygonSeries.mapPolygons.each(function(polygon) {
                    // Убеждаемся что полигон интерактивен
                    polygon.set("interactive", true);
                    polygon.set("cursorOverStyle", "pointer");
                    
                    // Устанавливаем обработчик клика напрямую
                    polygon.events.on("click", function(ev) {
                        console.log('!!! КЛИК ЗАРЕГИСТРИРОВАН !!!', ev);
                        try {
                            const data = ev.target.dataItem.dataContext;
                            console.log('Клик по региону:', data);
                            console.log('isZoomedToRegion:', isZoomedToRegion);
                            
                            if (data && !isZoomedToRegion) {
                        console.log('Обрабатываем клик по региону:', data.name);
                        // Показываем информацию о регионе
                        showRegionInfo(data);
                        
                        // Обрабатываем все регионы
                        const selectedPolygon = ev.target;
                        polygonSeries.mapPolygons.each(function(polygon) {
                            if (polygon !== selectedPolygon) {
                                // Затемняем неактивные регионы
                                polygon.set("fillOpacity", 0.3);
                                polygon.set("strokeOpacity", 0.3);
                                polygon.set("interactive", false);
                            } else {
                                // Подкрашиваем выбранный регион и делаем неактивным
                                polygon.setRaw("fill", am5.color(0x27ae60)); // Зеленый цвет
                                polygon.setRaw("fillOpacity", 1);
                                polygon.setRaw("strokeWidth", 3);
                                polygon.setRaw("stroke", am5.color(0xffffff));
                                polygon.set("interactive", false);
                            }
                        });
                        
                        // Получаем центр и размер региона
                        const centroid = selectedPolygon.visualCentroid();
                        
                        if (centroid) {
                            // Разблокируем зум
                            chart.set("maxZoomLevel", 8);
                            chart.set("minZoomLevel", 0.75);
                            
                            // Вычисляем размер региона по координатам границ
                            const geometry = selectedPolygon.dataItem.get("geometry");
                            let zoomLevel = 3.5; // По умолчанию
                            
                            if (geometry && geometry.coordinates && geometry.coordinates[0]) {
                                // Находим минимальные и максимальные координаты
                                let minLon = Infinity, maxLon = -Infinity;
                                let minLat = Infinity, maxLat = -Infinity;
                                
                                geometry.coordinates[0].forEach(coord => {
                                    if (Array.isArray(coord) && coord.length >= 2) {
                                        minLon = Math.min(minLon, coord[0]);
                                        maxLon = Math.max(maxLon, coord[0]);
                                        minLat = Math.min(minLat, coord[1]);
                                        maxLat = Math.max(maxLat, coord[1]);
                                    }
                                });
                                
                                // Вычисляем площадь региона (примерно)
                                const width = maxLon - minLon;
                                const height = maxLat - minLat;
                                const area = width * height;
                                
                                // Определяем зум в зависимости от площади
                                if (area < 1) {
                                    zoomLevel = 6; // Очень маленькие регионы (Москва, СПб)
                                } else if (area < 5) {
                                    zoomLevel = 5;
                                } else if (area < 20) {
                                    zoomLevel = 4;
                                } else if (area < 100) {
                                    zoomLevel = 3;
                                } else {
                                    zoomLevel = 2.5; // Очень большие регионы
                                }
                                
                                console.log(`Регион: ${data.name}, площадь: ${area.toFixed(2)}, зум: ${zoomLevel}`);
                            }
                            
                            // Приближаемся к региону
                            chart.zoomToGeoPoint(
                                { longitude: centroid.longitude, latitude: centroid.latitude },
                                zoomLevel,
                                true,
                                600
                            );
                        }
                        
                        // Устанавливаем флаг и показываем кнопку "Назад"
                        isZoomedToRegion = true;
                        const backButton = document.getElementById('backButton');
                        if (backButton) {
                            backButton.style.display = 'block';
                        }
                        
                        showAmNotification(`Регион: ${data.name}`, 'info');
                    }
                } catch (error) {
                    console.error('Ошибка обработки клика по региону:', error);
                }
                    });
                    
                    clickableCount++;
                });
                
                console.log(`Установлено обработчиков клика: ${clickableCount}`);
            }, 500);

            // Обработчик наведения курсора
            polygonSeries.mapPolygons.template.events.on("pointerover", function(ev) {
                try {
                    ev.target.states.applyAnimate("hover");
                } catch (error) {
                    console.error('Ошибка обработки наведения:', error);
                }
            });

            polygonSeries.mapPolygons.template.events.on("pointerout", function(ev) {
                try {
                    ev.target.states.applyAnimate("default");
                } catch (error) {
                    console.error('Ошибка обработки ухода курсора:', error);
                }
            });

            // Скрываем loading
            const loadingEl = document.querySelector('.loading');
            if (loadingEl) {
                loadingEl.style.display = 'none';
            }

            // Сохраняем для глобального доступа
            window.amChart = chart;
            window.amPolygonSeries = polygonSeries;
            window.amRoot = root;

            console.log("Карта России успешно инициализирована");
            
            showAmNotification('Карта загружена', 'success');
            goBackToMap();
            
            // Инициализируем поиск после загрузки карты
            initRegionSearch();

        } catch (error) {
            console.error("Ошибка инициализации карты:", error);
            const loadingEl = document.querySelector('.loading');
            if (loadingEl) {
                loadingEl.innerHTML = `
                    <div style="color: #e74c3c;">
                        <strong>Ошибка загрузки карты</strong><br>
                        <span style="font-size: 14px;">${error.message}</span><br>
                        <button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px; 
                            background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;">
                            Обновить страницу
                        </button>
                    </div>
                `;
            }
        }
    });
}

/**
 * Функция для центрирования карты России
 */
function centerMap() {
    if (!chart || !polygonSeries || !initialMapState) {
        console.warn('Карта не инициализирована или состояние не сохранено');
        return;
    }
    
    console.log('centerMap вызвана. initialMapState:', initialMapState);
    
    try {
        // Восстанавливаем все полигоны
        polygonSeries.mapPolygons.each(function(polygon) {
            // Удаляем все кастомные настройки
            polygon.remove("fill");
            polygon.remove("stroke");
            polygon.set("fillOpacity", 1);
            polygon.set("strokeOpacity", 0.8);
            polygon.set("strokeWidth", 1);
            polygon.set("interactive", true);
        });
        
        // Разблокируем зум для будущих кликов
        chart.set("maxZoomLevel", 8);
        chart.set("minZoomLevel", 0.75);
        
        // Сбрасываем флаг, чтобы регионы снова стали кликабельны
        isZoomedToRegion = false;
        
        // Небольшая задержка перед возвратом
        setTimeout(() => {
            // Возвращаемся к начальному состоянию
            chart.zoomToGeoPoint(
                { 
                    longitude: initialMapState.longitude, 
                    latitude: initialMapState.latitude 
                },
                initialMapState.zoomLevel,
                true,
                600
            );
            console.log('Карта возвращена к начальному состоянию');
        }, 50);
    } catch (error) {
        console.error('Ошибка центрирования карты:', error);
    }
}

/**
 * Функция для отображения информации о регионе
 */
function showRegionInfo(region) {
    // Панель информации отключена
    return;
}

/**
 * Функция для возврата к виду всей России
 */
function zoomToHome() {
    if (!chart) {
        console.warn('Карта не инициализирована');
        return;
    }
    
    try {
        centerMap();
        const infoPanel = document.getElementById('regionInfo');
        if (infoPanel) {
            infoPanel.style.display = 'none';
        }
        showAmNotification('Показана вся Россия', 'info');
    } catch (error) {
        console.error('Ошибка возврата к начальному виду:', error);
    }
}

/**
 * Функция для приближения к центру России
 */
function zoomToCenter() {
    if (!chart) {
        console.warn('Карта не инициализирована');
        return;
    }
    
    try {
        chart.zoomToGeoPoint({ longitude: 90, latitude: 60 }, 2.5, true);
        showAmNotification('Приближено к центру России', 'info');
    } catch (error) {
        console.error('Ошибка приближения к центру:', error);
    }
}

/**
 * Функция для сброса вида
 */
function resetView() {
    if (!chart || !polygonSeries) {
        console.warn('Карта не инициализирована');
        return;
    }
    
    try {
        centerMap();
        const infoPanel = document.getElementById('regionInfo');
        if (infoPanel) {
            infoPanel.style.display = 'none';
        }

        // Сбрасываем все выделения
        polygonSeries.mapPolygons.each(function(polygon) {
            try {
                polygon.states.applyAnimate("default");
            } catch (e) {
                console.error('Ошибка сброса состояния полигона:', e);
            }
        });
        
        showAmNotification('Вид сброшен', 'success');
    } catch (error) {
        console.error('Ошибка сброса вида:', error);
    }
}

/**
 * Функция для включения/выключения zoom
 */
function toggleZoom() {
    if (!chart) {
        console.warn('Карта не инициализирована');
        return;
    }
    
    try {
        zoomEnabled = !zoomEnabled;
        chart.set("wheelY", zoomEnabled ? "zoom" : "none");
        showAmNotification(
            zoomEnabled ? 'Zoom включен' : 'Zoom выключен',
            zoomEnabled ? 'success' : 'info'
        );
    } catch (error) {
        console.error('Ошибка переключения zoom:', error);
    }
}

/**
 * Функция для возврата к полной карте
 */
function goBackToMap() {
    if (!chart) {
        console.warn('Карта не инициализирована');
        return;
    }
    
    try {
        // Центрируем карту
        centerMap();
        
        // Скрываем кнопку "Назад"
        const backButton = document.getElementById('backButton');
        if (backButton) {
            backButton.style.display = 'none';
        }
        
        // Сбрасываем флаг
        isZoomedToRegion = false;
        
        showAmNotification('Возврат к карте России', 'info');
    } catch (error) {
        console.error('Ошибка возврата к карте:', error);
    }
}

/**
 * Функция для показа уведомлений (отключена)
 */
function showAmNotification(message, type = 'info') {
    // Уведомления отключены
    return;
}

/**
 * Обработчик изменения размера окна
 */
window.addEventListener('resize', function() {
    if (chart) {
        try {
            setTimeout(() => {
                root.resize();
            }, 100);
        } catch (error) {
            console.error('Ошибка изменения размера карты:', error);
        }
    }
});

/**
 * Обработка ошибок AmCharts
 */
if (typeof am5 !== 'undefined') {
    am5.addLicense("AM5C-xxxx-xxxx-xxxx-xxxx");
}

/**
 * Инициализация функционала поиска регионов
 */
function initRegionSearch() {
    const searchInput = document.getElementById('regionSearch');
    const searchResults = document.getElementById('searchResults');
    
    if (!searchInput || !searchResults) {
        console.warn('Элементы поиска не найдены');
        return;
    }
    
    console.log('Поиск инициализирован. Регионов загружено:', regionsData.length);
    
    // Обработчик ввода текста
    searchInput.addEventListener('input', function(e) {
        const query = e.target.value.trim().toLowerCase();
        
        if (query.length === 0) {
            searchResults.classList.remove('active');
            searchResults.innerHTML = '';
            return;
        }
        
        if (!regionsData || regionsData.length === 0) {
            searchResults.innerHTML = '<div class="no-results">Данные регионов не загружены</div>';
            searchResults.classList.add('active');
            return;
        }
        
        // Фильтруем регионы по запросу
        const matches = regionsData.filter(region => {
            return region.name.toLowerCase().includes(query) ||
                   (region.capital && region.capital.toLowerCase().includes(query));
        });
        
        console.log(`Поиск "${query}": найдено ${matches.length} регионов`);
        displaySearchResults(matches, query);
    });
    
    // Закрытие результатов при клике вне поля
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.remove('active');
        }
    });
    
    // Обработка Enter для первого результата
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            const firstResult = searchResults.querySelector('.search-result-item');
            if (firstResult) {
                firstResult.click();
            }
        }
    });
}

/**
 * Отображение результатов поиска
 */
function displaySearchResults(matches, query) {
    const searchResults = document.getElementById('searchResults');
    
    if (matches.length === 0) {
        searchResults.innerHTML = '<div class="no-results">Регион не найден</div>';
        searchResults.classList.add('active');
        return;
    }
    
    // Ограничиваем количество результатов
    const displayMatches = matches.slice(0, 10);
    
    searchResults.innerHTML = displayMatches.map(region => `
        <div class="search-result-item" onclick="selectRegion('${region.id}')">
            <strong>${highlightMatch(region.name, query)}</strong>
            ${region.capital ? `<small>Столица: ${region.capital}</small>` : ''}
        </div>
    `).join('');
    
    searchResults.classList.add('active');
}

/**
 * Подсветка совпадений в тексте
 */
function highlightMatch(text, query) {
    if (!query) return text;
    
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<span style="background: #ffeb3b; color: #000;">$1</span>');
}

/**
 * Выбор региона из результатов поиска
 */
function selectRegion(regionId) {
    const region = regionsData.find(r => r.id === regionId);
    
    if (!region) {
        showAmNotification('Регион не найден', 'error');
        return;
    }
    
    try {
        // Очищаем поиск
        const searchInput = document.getElementById('regionSearch');
        const searchResults = document.getElementById('searchResults');
        if (searchInput) searchInput.value = '';
        if (searchResults) {
            searchResults.classList.remove('active');
            searchResults.innerHTML = '';
        }
        
        // Если уже приближены к другому региону, сначала возвращаемся
        if (isZoomedToRegion) {
            centerMap();
        }
        
        // Небольшая задержка, чтобы анимация возврата завершилась
        setTimeout(() => {
            // Находим полигон региона
            if (polygonSeries) {
                let selectedPolygon = null;
                
                polygonSeries.mapPolygons.each(function(polygon) {
                    const data = polygon.dataItem.dataContext;
                    if (data && data.id === regionId) {
                        selectedPolygon = polygon;
                        // Показываем информацию
                        showRegionInfo(region);
                        
                        // Подкрашиваем выбранный регион зеленым
                        polygon.setRaw("fill", am5.color(0x27ae60)); // Зеленый цвет
                        polygon.setRaw("fillOpacity", 1);
                        polygon.setRaw("strokeWidth", 3);
                        polygon.setRaw("stroke", am5.color(0xffffff));
                        polygon.set("interactive", false);
                        
                        // Получаем центр и размер региона
                        const centroid = polygon.visualCentroid();
                        
                        if (centroid) {
                            // Разблокируем зум
                            chart.set("maxZoomLevel", 8);
                            chart.set("minZoomLevel", 0.75);
                            
                            // Вычисляем размер региона по координатам границ
                            const geometry = polygon.dataItem.get("geometry");
                            let zoomLevel = 3.5; // По умолчанию
                            
                            if (geometry && geometry.coordinates && geometry.coordinates[0]) {
                                // Находим минимальные и максимальные координаты
                                let minLon = Infinity, maxLon = -Infinity;
                                let minLat = Infinity, maxLat = -Infinity;
                                
                                geometry.coordinates[0].forEach(coord => {
                                    if (Array.isArray(coord) && coord.length >= 2) {
                                        minLon = Math.min(minLon, coord[0]);
                                        maxLon = Math.max(maxLon, coord[0]);
                                        minLat = Math.min(minLat, coord[1]);
                                        maxLat = Math.max(maxLat, coord[1]);
                                    }
                                });
                                
                                // Вычисляем площадь региона (примерно)
                                const width = maxLon - minLon;
                                const height = maxLat - minLat;
                                const area = width * height;
                                
                                // Определяем зум в зависимости от площади
                                if (area < 1) {
                                    zoomLevel = 6; // Очень маленькие регионы (Москва, СПб)
                                } else if (area < 5) {
                                    zoomLevel = 5;
                                } else if (area < 20) {
                                    zoomLevel = 4;
                                } else if (area < 100) {
                                    zoomLevel = 3;
                                } else {
                                    zoomLevel = 2.5; // Очень большие регионы
                                }
                                
                                console.log(`Поиск - Регион: ${region.name}, площадь: ${area.toFixed(2)}, зум: ${zoomLevel}`);
                            }
                            
                            // Приближаемся к региону с плавной анимацией
                            chart.zoomToGeoPoint(
                                { longitude: centroid.longitude, latitude: centroid.latitude },
                                zoomLevel,
                                true,
                                600
                            );
                        }
                        
                        // Устанавливаем флаг и показываем кнопку "Назад"
                        isZoomedToRegion = true;
                        const backButton = document.getElementById('backButton');
                        if (backButton) {
                            backButton.style.display = 'block';
                        }
                        
                        showAmNotification(`Регион: ${region.name}`, 'success');
                    } else {
                        // Затемняем все остальные регионы
                        polygon.set("fillOpacity", 0.3);
                        polygon.set("strokeOpacity", 0.3);
                        polygon.set("interactive", false);
                    }
                });
            } else {
                showAmNotification('Карта еще не загружена', 'warning');
            }
        }, isZoomedToRegion ? 700 : 0); // Задержка только если уже приближены
        
    } catch (error) {
        console.error('Ошибка при выборе региона:', error);
        showAmNotification('Ошибка при переходе к региону', 'error');
    }
}

/**
 * Поиск региона по названию (программный)
 */
function searchRegionByName(name) {
    if (!name) return;
    
    const region = regionsData.find(r => 
        r.name.toLowerCase() === name.toLowerCase() ||
        r.name.toLowerCase().includes(name.toLowerCase())
    );
    
    if (region) {
        selectRegion(region.id);
    } else {
        showAmNotification('Регион не найден', 'error');
    }
}

// Экспорт функций для глобального использования
window.initAmMap = initAmMap;
window.showRegionInfo = showRegionInfo;
window.zoomToHome = zoomToHome;
window.zoomToCenter = zoomToCenter;
window.resetView = resetView;
window.toggleZoom = toggleZoom;
window.selectRegion = selectRegion;
window.searchRegionByName = searchRegionByName;