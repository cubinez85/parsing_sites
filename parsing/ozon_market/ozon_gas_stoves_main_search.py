from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
import pandas as pd
import time
import re
import random
import os


def setup_driver():
    """Настройка драйвера"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--start-maximized')
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    stealth(driver,
            languages=["ru-RU", "ru"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: function() {return undefined;}})")

    return driver


def human_like_delay(min_seconds=1, max_seconds=3):
    time.sleep(random.uniform(min_seconds, max_seconds))


def wait_for_page_load(driver, timeout=10):
    """Ожидание загрузки страницы"""
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script('return document.readyState') == 'complete'
    )


def scroll_all(driver, max_scrolls=20, scroll_delay_min=2, scroll_delay_max=4):
    """
    Полная прокрутка страницы до конца с обнаружением новых товаров
    """
    print("📜 Начинаем полную прокрутку страницы...")

    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    no_new_content_count = 0
    max_no_new_content = 3  # Максимум попыток без нового контента

    all_products_count = 0
    products_data = []

    while scroll_attempts < max_scrolls and no_new_content_count < max_no_new_content:
        # Прокручиваем вниз
        scroll_height = random.randint(800, 1200)
        driver.execute_script(f"window.scrollBy(0, {scroll_height});")

        human_like_delay(scroll_delay_min, scroll_delay_max)
        scroll_attempts += 1

        # Проверяем высоту страницы
        new_height = driver.execute_script("return document.body.scrollHeight")

        # Ищем товары после каждой прокрутки
        current_products = find_kitchen_gas_stoves(driver)
        current_count = len(current_products)

        print(f"📊 После прокрутки {scroll_attempts}: найдено {current_count} товаров")

        # Собираем данные с новых товаров
        if current_products:
            new_data = extract_products_data(driver, current_products, all_products_count)
            if new_data:
                products_data.extend(new_data)
                # Немедленное сохранение во временный файл
                save_temp_data(products_data, 'temp_ozon_data.xlsx')
                print(f"💾 Сразу сохранено {len(new_data)} новых товаров")

        # Проверяем, появился ли новый контент
        if new_height == last_height:
            no_new_content_count += 1
            print(f"⚠️ Нет нового контента ({no_new_content_count}/{max_no_new_content})")
        else:
            no_new_content_count = 0
            last_height = new_height

        # Случайная пауза между прокрутками
        human_like_delay(1, 2)

        # Пытаемся найти кнопку "Показать еще" или пагинацию
        try:
            load_more_buttons = [
                "button[class*='load-more']",
                "button[class*='more']",
                "div[class*='load-more']",
                "a[class*='next']",
                "button:contains('Показать еще')",
                "button:contains('Загрузить еще')"
            ]

            for selector in load_more_buttons:
                try:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                    if button.is_displayed():
                        driver.execute_script("arguments[0].click();", button)
                        print("🔘 Нажата кнопка 'Показать еще'")
                        human_like_delay(3, 5)
                        break
                except:
                    continue
        except:
            pass

    print(f"✅ Прокрутка завершена. Всего прокруток: {scroll_attempts}")
    return products_data


def extract_products_data(driver, products, existing_count=0):
    """Извлечение данных из списка товаров"""
    products_data = []

    for i, product in enumerate(products, existing_count + 1):
        try:
            print(f"\n--- Обрабатываем товар {i} ---")

            # Прокручиваем к товару
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", product)
            human_like_delay(1, 2)

            # Извлекаем информацию
            name = extract_product_name(product)
            price = extract_accurate_price(product, driver)

            print(f"📝 Название: {name[:100] if name else 'Не найдено'}")
            print(f"💰 Цена: {price if price else 'Не найдена'}")

            if name and price:
                # СТРОГАЯ проверка что это именно ГАЗОВАЯ кухонная плита
                name_lower = name.lower()
                is_gas_kitchen_stove = (
                        any(word in name_lower for word in ['газов', 'газовая', 'газовой']) and
                        any(word in name_lower for word in ['плита', 'варочная', 'духовка']) and
                        not any(word in name_lower for word in [
                            'электрич', 'комбинирован', 'электроплита',
                            'индукцион', 'газоэлектрич', 'походн', 'туристич'
                        ])
                )

                if is_gas_kitchen_stove:
                    product_data = {
                        'Категория товара': 'Кухонная газовая плита',
                        'Модель': name,
                        'Цена': price,
                        'Источник': 'Ozon',
                        'Время сбора': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    products_data.append(product_data)
                    print(f"✅ Добавлена ГАЗОВАЯ плита: {name[:80]}... - {price} руб.")
                else:
                    print(f"❌ Пропущена (не газовая): {name[:60]}...")
            else:
                print(f"❌ Неполные данные - название или цена отсутствуют")

        except Exception as e:
            print(f"⚠️ Ошибка обработки товара {i}: {e}")
            continue

    return products_data


def save_temp_data(data, filename):
    """Сохранение временных данных"""
    if data:
        try:
            df = pd.DataFrame(data)
            # Сохраняем все данные без удаления дубликатов
            df.to_excel(filename, index=False)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения временных данных: {e}")


def find_kitchen_gas_stoves(driver):
    """Поиск именно кухонных газовых плит с улучшенной логикой"""
    print("🔍 Ищем кухонные газовые плиты...")

    # Ждем загрузки товаров
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[class*='tile'], article[class*='tile'], div[class*='card']"))
        )
    except:
        print("⏳ Товары загружаются медленно...")

    # Более специфичные селекторы для Ozon
    selectors = [
        "div[class*='tile-root']",
        "article[class*='tile-root']",
        "div[class*='widget-search-result'] div[class*='tile']",
        "div[class*='search-result'] div[class*='tile']",
        "div[class*='tile']",
        "article[class*='tile']",
        "div[class*='card']",
        "div[class*='item']"
    ]

    products = []

    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"Найдено элементов с селектором {selector}: {len(elements)}")

            for element in elements:
                try:
                    text = element.text.lower()
                    if len(text) > 30:  # Минимальная длина текста
                        # Более точные признаки кухонной ГАЗОВОЙ плиты
                        is_gas_stove = (
                                any(word in text for word in ['плита', 'газов', 'газовая', 'газовой']) and
                                not any(word in text for word in [
                                    'походн', 'туристич', 'кемпинг', 'кейс', 'переносн', 'портатив',
                                    'электрич', 'комбинирован', 'электроплита', 'индукцион', 'газоэлектрич'
                                ])
                        )

                        if is_gas_stove:
                            # Проверяем, нет ли уже этого элемента
                            element_id = element.id
                            if not any(p.id == element_id for p in products):
                                products.append(element)
                                print(f"Найдена газовая плита: {text[:100]}...")
                except:
                    continue

            if products:
                print(f"✅ Найдено газовых плит: {len(products)}")
                break

        except Exception as e:
            print(f"Ошибка при поиске по селектору {selector}: {e}")
            continue

    return products


def extract_accurate_price(element, driver):
    """Точное извлечение цены с улучшенными селекторами для Ozon"""
    try:
        # Стратегия 1: Ищем цену в дочерних элементах с приоритетом классов Ozon
        price_selectors = [
            "span[class*='price']",
            "div[class*='price']",
            "span[class*='cost']",
            "div[class*='cost']",
            "[class*='currency']",
            "span[class*='rub']",
            "div[class*='rub']",
            "b[class*='price']",
            "strong[class*='price']",
            # Специфичные классы Ozon
            ".c311-a1", ".a0c1", ".a1v9", ".a1v7", ".ui-q", ".q5",
            ".tsHeadline500Large", ".tsBodyControl400Large",
            "[data-widget*='price']",
            "[data-testid*='price']",
            "[class*='tile-price']",
            # Новые селекторы для современных версий Ozon
            "span[class*='tsHeadline']",
            "div[class*='tsHeadline']",
            "span[class*='tsBodyControl400Large']",
            "div[class*='tsBodyControl400Large']"
        ]

        for selector in price_selectors:
            try:
                price_elements = element.find_elements(By.CSS_SELECTOR, selector)
                for price_element in price_elements:
                    price_text = price_element.text.strip()
                    if price_text:
                        print(f"Найден текст цены: {price_text}")
                        # Улучшенная очистка текста
                        clean_text = re.sub(r'[^\d\s]', '', price_text)
                        clean_text = re.sub(r'\s+', '', clean_text)

                        if clean_text and len(clean_text) >= 3:
                            price = int(clean_text)
                            if 1000 <= price <= 500000:  # Расширенный диапазон
                                print(f"Цена извлечена: {price}")
                                return price
            except:
                continue

        # Стратегия 2: Поиск по текстовым узлам с помощью JavaScript
        js_script = """
        var element = arguments[0];
        var walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
        var textNodes = [];
        while (walker.nextNode()) {
            textNodes.push(walker.currentNode.textContent);
        }

        var priceRegex = /\\d{1,3}[\\s ]?\\d{3}[\\s ]?\\d{0,3}/g;
        for (var i = 0; i < textNodes.length; i++) {
            var matches = textNodes[i].match(priceRegex);
            if (matches) {
                for (var j = 0; j < matches.length; j++) {
                    var cleanPrice = matches[j].replace(/[^\\d]/g, '');
                    if (cleanPrice.length >= 3) {
                        var price = parseInt(cleanPrice);
                        if (price >= 1000 && price <= 500000) {
                            return price;
                        }
                    }
                }
            }
        }
        return null;
        """

        price = driver.execute_script(js_script, element)
        if price:
            print(f"Цена из JavaScript: {price}")
            return price

        # Стратегия 3: Поиск в основном тексте элемента
        element_text = element.text
        # Улучшенное регулярное выражение для русских цен
        price_patterns = [
            r'(\d{1,3}[ \ ]?\d{3}[ \ ]?\d{0,3})[ \ ]?₽?',
            r'₽[ \ ]*(\d{1,3}[ \ ]?\d{3}[ \ ]?\d{0,3})',
            r'руб[^\\d]*(\d{1,3}[ \ ]?\d{3}[ \ ]?\d{0,3})'
        ]

        for pattern in price_patterns:
            price_matches = re.findall(pattern, element_text)
            for match in price_matches:
                clean_price = re.sub(r'[^\d]', '', str(match))
                if clean_price:
                    price = int(clean_price)
                    if 1000 <= price <= 500000:
                        print(f"Цена из текста: {price}")
                        return price

        # Стратегия 4: Поиск в атрибутах data-*
        try:
            data_attributes = element.get_attribute('outerHTML')
            if data_attributes:
                data_price_matches = re.findall(r'data-price="(\d+)"', data_attributes)
                for match in data_price_matches:
                    price = int(match)
                    if 1000 <= price <= 500000:
                        print(f"Цена из data-атрибута: {price}")
                        return price
        except:
            pass

        print("Цена не найдена")
        return None

    except Exception as e:
        print(f"Ошибка извлечения цены: {e}")
        return None


def extract_product_name(element):
    """Извлечение названия товара с улучшенной логикой"""
    try:
        # Попробуем найти заголовок или название товара
        title_selectors = [
            "a[class*='title']",
            "span[class*='title']",
            "div[class*='title']",
            "h3", "h4", "h5",
            "a[class*='name']",
            "span[class*='name']",
            "div[class*='name']",
            "[class*='tile-title']",
            "[class*='card-title']",
            ".tsBody500Medium", ".a5-a"
        ]

        for selector in title_selectors:
            try:
                title_elements = element.find_elements(By.CSS_SELECTOR, selector)
                for title_element in title_elements:
                    title_text = title_element.text.strip()
                    if title_text and len(title_text) > 10:
                        print(f"Название из селектора {selector}: {title_text[:80]}...")
                        return title_text
            except:
                continue

        # Если не нашли по селекторам, используем общий текст
        text = element.text
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Ищем строку с названием (самая длинная информативная строка)
        if lines:
            # Фильтруем строки с ценами и техническими данными
            filtered_lines = []
            for line in lines:
                if (len(line) > 15 and
                        not re.search(r'\d{1,3}[ \ ]?\d{3}[ \ ]?\d{0,3}[ \ ]?₽', line) and
                        not re.search(r'отзыв|в корзину|купить|₽|руб|доставка', line.lower())):
                    filtered_lines.append(line)

            if filtered_lines:
                # Возвращаем самую длинную строку
                name = max(filtered_lines, key=len)
                print(f"Название из фильтрованных строк: {name[:80]}...")
                return name

            # Если не нашли отфильтрованных, возвращаем первую длинную строку
            for line in lines:
                if len(line) > 20:
                    print(f"Название из длинной строки: {line[:80]}...")
                    return line

            name = lines[0] if lines else "Неизвестная модель"
            print(f"Название из первой строки: {name[:80]}...")
            return name

        print("Название не найдено")
        return "Неизвестная модель"

    except Exception as e:
        print(f"Ошибка извлечения названия: {e}")
        return "Неизвестная модель"


def parse_ozon_kitchen_gas_stoves():
    """Парсинг именно кухонных газовых плит"""
    driver = setup_driver()
    all_data = []

    try:
        # ОДИН наиболее релевантный URL для газовых плит
        url = "https://www.ozon.ru/search/?text=газовая+плита+кухонная&from_global=true"

        print(f"\n🌐 Используем основной URL: {url}")
        driver.get(url)
        wait_for_page_load(driver)
        human_like_delay(5, 8)

        # Используем улучшенную функцию полной прокрутки
        all_data = scroll_all(driver, max_scrolls=15, scroll_delay_min=2, scroll_delay_max=4)

        print(f"\n📊 Полная прокрутка завершена. Всего собрано: {len(all_data)} ГАЗОВЫХ плит")

    except Exception as e:
        print(f"🚨 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        driver.save_screenshot('ozon_error.png')
    finally:
        driver.quit()

    return all_data


def remove_duplicates(df):
    """Удаление дубликатов из DataFrame"""
    if df is None or df.empty:
        return df

    print(f"📊 До удаления дубликатов: {len(df)} записей")

    # Создаем копию DataFrame для работы
    df_clean = df.copy()

    # Удаляем дубликаты по модели и цене (основные критерии)
    df_clean = df_clean.drop_duplicates(subset=['Модель', 'Цена'], keep='first')

    # Дополнительная очистка: удаляем очень похожие модели
    # Нормализуем названия для лучшего сравнения
    df_clean['Модель_норм'] = df_clean['Модель'].str.lower().str.replace(r'[^\w\s]', '', regex=True)

    # Удаляем дубликаты по нормализованным названиям и цене
    df_clean = df_clean.drop_duplicates(subset=['Модель_норм', 'Цена'], keep='first')

    # Удаляем временный столбец
    df_clean = df_clean.drop('Модель_норм', axis=1)

    print(f"📊 После удаления дубликатов: {len(df_clean)} записей")
    print(f"🗑️ Удалено дубликатов: {len(df) - len(df_clean)}")

    return df_clean


def save_to_excel(data, filename='ozon_kitchen_gas_stoves_with_del_dublicates.xlsx'):
    """Сохраняет данные в Excel с удалением дубликатов"""
    if data:
        df = pd.DataFrame(data)

        # Сохраняем ВСЕ найденные товары в отдельный файл (с дубликатами)
        all_filename = 'ozon_kitchen_gas_stoves_with_duplicates.xlsx'
        df_all = df.copy()
        df_all = df_all.sort_values('Цена', ascending=True)
        df_all.reset_index(drop=True, inplace=True)
        df_all.index = df_all.index + 1
        df_all['Цена'] = df_all['Цена'].apply(lambda x: f"{x:,} руб.".replace(',', ' '))
        df_all.to_excel(all_filename, index=True, index_label='№')
        print(f"💾 Сохранены все товары (с дубликатами): {len(df_all)} шт. в файл {all_filename}")

        # УДАЛЯЕМ ДУБЛИКАТЫ для основного файла
        df_clean = remove_duplicates(df)

        # Сортируем по цене
        df_clean = df_clean.sort_values('Цена', ascending=True)
        df_clean.reset_index(drop=True, inplace=True)
        df_clean.index = df_clean.index + 1

        # Форматируем цену для читаемости
        df_clean['Цена'] = df_clean['Цена'].apply(lambda x: f"{x:,} руб.".replace(',', ' '))

        # Сохраняем очищенные данные в основной файл
        df_clean.to_excel(filename, index=True, index_label='№')
        print(f"💾 Сохранено {len(df_clean)} кухонных плит (без дубликатов) в файл {filename}")

        # Удаляем временный файл если он существует
        if os.path.exists('temp_ozon_data.xlsx'):
            os.remove('temp_ozon_data.xlsx')
            print("🗑️ Временный файл удален")

        # Выводим результаты (только очищенные данные)
        print("\n🏆 Собранные кухонные газовые плиты с Ozon (без дубликатов):")
        print("-" * 100)
        for i, row in df_clean.iterrows():
            print(f"{i:2d}. {row['Модель'][:70]}... - {row['Цена']}")
        print("-" * 100)

        # Статистика по очищенным данным
        prices_clean = []
        for price_str in df_clean['Цена']:
            try:
                price_num = int(price_str.replace(' руб.', '').replace(' ', ''))
                prices_clean.append(price_num)
            except:
                continue

        if prices_clean:
            avg_price = sum(prices_clean) // len(prices_clean)
            print(f"\n📈 Статистика (без дубликатов):")
            print(f"   • Всего уникальных плит: {len(prices_clean)}")
            print(f"   • Минимальная цена: {min(prices_clean):,} руб.")
            print(f"   • Максимальная цена: {max(prices_clean):,} руб.")
            print(f"   • Средняя цена: {avg_price:,} руб.")

        return df_clean
    else:
        print("📭 Нет данных для сохранения")
        return None


if __name__ == "__main__":
    print("🚀 Запускаем парсинг кухонных ГАЗОВЫХ плит с Ozon...")
    print("⏳ Ищем именно ГАЗОВЫЕ модели (исключаем электрические и комбинированные)...")
    print("=" * 80)

    start_time = time.time()

    kitchen_stoves_data = parse_ozon_kitchen_gas_stoves()

    end_time = time.time()
    execution_time = end_time - start_time

    print(f"\n⏱️ Время выполнения: {execution_time:.2f} секунд")
    print(f"📊 Найдено ГАЗОВЫХ плит: {len(kitchen_stoves_data)}")

    # Сохраняем результаты (теперь с удалением дубликатов)
    result_df = save_to_excel(kitchen_stoves_data)

    if not kitchen_stoves_data:
        print("\n❌ Газовые плиты не найдены")
        print("\n💡 Рекомендации для решения проблемы:")
        print("1. Проверьте доступность сайта Ozon")
        print("2. Попробуйте использовать VPN")
        print("3. Обновите селекторы в коде под текущую версию сайта")
        print("4. Увеличьте время ожидания загрузки страницы")
        print("5. Проверьте работу антидетект-функций")