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
        current_products = find_dachshund_dry_food(driver)
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


def extract_product_url(element, driver):
    """Извлечение ссылки на товар"""
    try:
        # Селекторы для ссылок на товары в Ozon
        link_selectors = [
            "a[href*='/product/']",
            "a[href*='/product']",
            "a[class*='tile-link']",
            "a[class*='card-link']",
            "a[class*='title-link']",
            "a[class*='name-link']",
            "a[href*='/r/']",
            "a[class*='link']"
        ]

        for selector in link_selectors:
            try:
                links = element.find_elements(By.CSS_SELECTOR, selector)
                for link in links:
                    href = link.get_attribute('href')
                    if href and ('/product/' in href or '/r/' in href):
                        # Преобразуем относительную ссылку в абсолютную
                        if href.startswith('/'):
                            href = f"https://www.ozon.ru{href}"
                        print(f"🔗 Найдена ссылка: {href}")
                        return href
            except:
                continue

        # Альтернативный способ: поиск через родительские элементы
        try:
            parent_link = element.find_element(By.XPATH, "./ancestor::a[1]")
            href = parent_link.get_attribute('href')
            if href and ('/product/' in href or '/r/' in href):
                if href.startswith('/'):
                    href = f"https://www.ozon.ru{href}"
                print(f"🔗 Найдена ссылка через родителя: {href}")
                return href
        except:
            pass

        # JavaScript поиск ссылок
        js_script = """
        var element = arguments[0];
        var links = element.querySelectorAll('a[href*="/product/"], a[href*="/r/"]');
        if (links.length > 0) {
            var href = links[0].href;
            if (href.startsWith('/')) {
                return 'https://www.ozon.ru' + href;
            }
            return href;
        }
        return null;
        """

        href = driver.execute_script(js_script, element)
        if href:
            print(f"🔗 Найдена ссылка через JS: {href}")
            return href

        print("❌ Ссылка на товар не найдена")
        return None

    except Exception as e:
        print(f"⚠️ Ошибка извлечения ссылки: {e}")
        return None


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
            url = extract_product_url(product, driver)

            print(f"📝 Название: {name[:100] if name else 'Не найдено'}")
            print(f"💰 Цена: {price if price else 'Не найдена'}")
            print(f"🔗 Ссылка: {url if url else 'Не найдена'}")

            if name and price:
                # Проверка что это сухой корм для собак (не строгая фильтрация по породе)
                name_lower = name.lower()
                is_dog_food = (
                        any(word in name_lower for word in ['корм', 'food', 'питание']) and
                        any(word in name_lower for word in ['собак', 'dog', 'для взрослых собак', 'для щенков']) and
                        not any(word in name_lower for word in ['консерв', 'влажн', 'паштет', 'желе', 'пауч'])
                )

                if is_dog_food:
                    product_data = {
                        'Название товара': name,
                        'Цена': price,
                        'Ссылка на товар': url if url else 'Не найдена',
                        'Источник': 'Ozon'
                    }
                    products_data.append(product_data)
                    print(f"✅ Добавлен корм для собак: {name[:80]}... - {price} руб.")
                else:
                    print(f"❌ Пропущено (не сухой корм для собак): {name[:60]}...")
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


def find_dachshund_dry_food(driver):
    """Поиск сухого корма для собак с улучшенной логикой"""
    print("🔍 Ищем сухой корм для собак...")

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
                    if len(text) > 20:  # Минимальная длина текста
                        # Признаки корма для собак
                        is_dog_food = (
                                any(word in text for word in ['корм', 'собак', 'dog', 'для собак']) and
                                not any(word in text for word in [
                                    'консерв', 'влажн', 'паштет', 'желе', 'пауч', 'кошк', 'cat', 'кот'
                                ])
                        )

                        if is_dog_food:
                            # Проверяем, нет ли уже этого элемента
                            element_id = element.id
                            if not any(p.id == element_id for p in products):
                                products.append(element)
                                print(f"Найден корм для собак: {text[:100]}...")
                except:
                    continue

            if products:
                print(f"✅ Найдено кормов для собак: {len(products)}")
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

                        if clean_text and len(clean_text) >= 2:
                            price = int(clean_text)
                            if 100 <= price <= 100000:  # Диапазон цен для кормов
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
                    if (cleanPrice.length >= 2) {
                        var price = parseInt(cleanPrice);
                        if (price >= 100 && price <= 100000) {
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
                    if 100 <= price <= 100000:
                        print(f"Цена из текста: {price}")
                        return price

        # Стратегия 4: Поиск в атрибутах data-*
        try:
            data_attributes = element.get_attribute('outerHTML')
            if data_attributes:
                data_price_matches = re.findall(r'data-price="(\d+)"', data_attributes)
                for match in data_price_matches:
                    price = int(match)
                    if 100 <= price <= 100000:
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
                    if title_text and len(title_text) > 5:
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
                if (len(line) > 10 and
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
                if len(line) > 15:
                    print(f"Название из длинной строки: {line[:80]}...")
                    return line

            name = lines[0] if lines else "Неизвестный товар"
            print(f"Название из первой строки: {name[:80]}...")
            return name

        print("Название не найдено")
        return "Неизвестный товар"

    except Exception as e:
        print(f"Ошибка извлечения названия: {e}")
        return "Неизвестный товар"


def apply_category_filters(driver):
    """Применение фильтров на странице категории"""
    try:
        # Ждем загрузки фильтров
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='filter'], aside[class*='filter']"))
        )

        # Фильтр по типу корма - пытаемся найти и выбрать "Сухой"
        filter_selectors = [
            "label:contains('Сухой')",
            "span:contains('Сухой')",
            "div:contains('Сухой')",
            "a[href*='dry']",
            "input[value*='сух']"
        ]

        for selector in filter_selectors:
            try:
                # Используем XPath для поиска по тексту
                filter_element = driver.find_element(By.XPATH, f"//*[contains(text(), 'Сухой')]")
                if filter_element.is_displayed():
                    driver.execute_script("arguments[0].click();", filter_element)
                    print("✅ Применен фильтр 'Сухой'")
                    human_like_delay(3, 5)
                    break
            except:
                continue

    except Exception as e:
        print(f"⚠️ Фильтры не применены: {e}")


def parse_ozon_dachshund_dry_food():
    """Парсинг сухого корма для такс"""
    driver = setup_driver()
    all_data = []

    try:
        # URL категории сухих кормов для собак с поиском для такс
        url = "https://www.ozon.ru/category/suhie-korma-dlya-sobak-12303/?category_was_predicted=true&deny_category_prediction=true&from_global=true&text=%D1%81%D1%83%D1%85%D0%BE%D0%B9+%D0%BA%D0%BE%D1%80%D0%BC+%D0%B4%D0%BB%D1%8F+%D1%82%D0%B0%D0%BA%D1%81%D1%8B"

        print(f"\n🌐 Используем URL категории сухих кормов для собак: {url}")
        driver.get(url)
        wait_for_page_load(driver)
        human_like_delay(5, 8)

        # Пытаемся применить фильтры
        apply_category_filters(driver)

        # Используем улучшенную функцию полной прокрутки
        all_data = scroll_all(driver, max_scrolls=15, scroll_delay_min=2, scroll_delay_max=4)

        print(f"\n📊 Полная прокрутка завершена. Всего собрано: {len(all_data)} кормов для собак")

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

    # Удаляем дубликаты по названию и цене (основные критерии)
    df_clean = df_clean.drop_duplicates(subset=['Название товара', 'Цена'], keep='first')

    # Дополнительная очистка: удаляем очень похожие названия
    # Нормализуем названия для лучшего сравнения
    df_clean['Название_норм'] = df_clean['Название товара'].str.lower().str.replace(r'[^\w\s]', '', regex=True)

    # Удаляем дубликаты по нормализованным названиям и цене
    df_clean = df_clean.drop_duplicates(subset=['Название_норм', 'Цена'], keep='first')

    # Удаляем временный столбец
    df_clean = df_clean.drop('Название_норм', axis=1)

    print(f"📊 После удаления дубликатов: {len(df_clean)} записей")
    print(f"🗑️ Удалено дубликатов: {len(df) - len(df_clean)}")

    return df_clean


def save_to_excel(data, filename='ozon_dachshund_dry_food_with_link_on_product.xlsx'):
    """Сохраняет данные в Excel с удалением дубликатов"""
    if data:
        df = pd.DataFrame(data)

        # УДАЛЯЕМ ДУБЛИКАТЫ
        df_clean = remove_duplicates(df)

        # Сортируем по цене
        df_clean = df_clean.sort_values('Цена', ascending=True)
        df_clean.reset_index(drop=True, inplace=True)

        # Сохраняем очищенные данные в основной файл
        columns_order = ['Название товара', 'Цена', 'Ссылка на товар', 'Источник']
        df_clean = df_clean.reindex(columns=[col for col in columns_order if col in df_clean.columns])
        df_clean.to_excel(filename, index=False)
        print(f"💾 Сохранено {len(df_clean)} кормов для собак (без дубликатов) в файл {filename}")

        # Удаляем временный файл если он существует
        if os.path.exists('temp_ozon_data.xlsx'):
            os.remove('temp_ozon_data.xlsx')
            print("🗑️ Временный файл удален")

        # Выводим результаты (только очищенные данные)
        print("\n🏆 Собранные сухие корма для собак с Ozon:")
        print("-" * 120)
        for i, row in df_clean.iterrows():
            link_info = f" - {row['Ссылка на товар']}" if row[
                                                              'Ссылка на товар'] != 'Не найдена' else " - Ссылка не найдена"
            print(f"{i + 1:2d}. {row['Название товара'][:60]}... - {row['Цена']} руб.{link_info}")
        print("-" * 120)

        # Статистика по очищенным данным
        prices_clean = df_clean['Цена'].tolist()
        if prices_clean:
            avg_price = sum(prices_clean) // len(prices_clean)
            print(f"\n📈 Статистика (без дубликатов):")
            print(f"   • Всего уникальных кормов: {len(prices_clean)}")
            print(f"   • Минимальная цена: {min(prices_clean):,} руб.")
            print(f"   • Максимальная цена: {max(prices_clean):,} руб.")
            print(f"   • Средняя цена: {avg_price:,} руб.")

            # Статистика по ссылкам
            links_count = df_clean['Ссылка на товар'].apply(lambda x: x != 'Не найдена').sum()
            print(f"   • Товаров со ссылками: {links_count}/{len(df_clean)}")

        return df_clean
    else:
        print("📭 Нет данных для сохранения")
        return None


if __name__ == "__main__":
    print("🚀 Запускаем парсинг сухого корма для такс с Ozon...")
    print("⏳ Используем категорию сухих кормов для собак...")
    print("=" * 80)

    start_time = time.time()

    dog_food_data = parse_ozon_dachshund_dry_food()

    end_time = time.time()
    execution_time = end_time - start_time

    print(f"\n⏱️ Время выполнения: {execution_time:.2f} секунд")
    print(f"📊 Найдено кормов для собак: {len(dog_food_data)}")

    # Сохраняем результаты
    result_df = save_to_excel(dog_food_data)

    if not dog_food_data:
        print("\n❌ Корма для собак не найдены")
        print("\n💡 Рекомендации для решения проблемы:")
        print("1. Проверьте доступность сайта Ozon")
        print("2. Попробуйте использовать VPN")
        print("3. Обновите селекторы в коде под текущую версию сайта")
        print("4. Увеличьте время ожидания загрузки страницы")
        print("5. Проверьте работу антидетект-функций")