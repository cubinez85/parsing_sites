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
import json
from datetime import datetime


def setup_driver():
    """Настройка драйвера для Wildberries"""
    options = Options()

    # Базовые настройки
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')

    # User-agent для Wildberries
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--accept-lang=ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7')

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    # Применяем stealth режим
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
    """Случайная задержка между действиями"""
    time.sleep(random.uniform(min_seconds, max_seconds))


def wait_for_page_load(driver, timeout=10):
    """Ожидание загрузки страницы"""
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script('return document.readyState') == 'complete'
    )


def close_wildberries_popups(driver):
    """Закрытие всплывающих окон на Wildberries"""
    try:
        time.sleep(2)

        # Закрываем куки
        try:
            cookie_btn = driver.find_element(By.CSS_SELECTOR,
                                             '.cookie-notification__button, .cookies__button, [data-wba-header-name*="Cookie"]')
            if cookie_btn.is_displayed():
                cookie_btn.click()
                time.sleep(1)
        except:
            pass

        # Закрываем геолокацию
        try:
            geo_btn = driver.find_element(By.CSS_SELECTOR,
                                          '.geo__close, .location__close, [data-wba-header-name*="Location"]')
            if geo_btn.is_displayed():
                geo_btn.click()
                time.sleep(1)
        except:
            pass

        # Закрываем другие попапы
        close_selectors = [
            'button[aria-label*="Закрыть"]',
            '.popup__close',
            '.j-close',
            '.modal__close'
        ]

        for selector in close_selectors:
            try:
                close_btns = driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in close_btns:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
            except:
                pass

    except Exception as e:
        print(f"Ошибка при закрытии попапов: {e}")


def save_to_temp_file(data, filename='temp_wildberries_gas_stoves.json'):
    """Сохраняет данные во временный файл"""
    try:
        existing_data = []
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        existing_data.extend(data)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        print(f"💾 Сохранено {len(data)} записей во временный файл. Всего: {len(existing_data)}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения во временный файл: {e}")
        return False


def load_from_temp_file(filename='temp_wildberries_gas_stoves.json'):
    """Загружает данные из временного файла"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"❌ Ошибка загрузки из временного файла: {e}")
        return []


def clear_temp_file(filename='temp_wildberries_gas_stoves.json'):
    """Очищает временный файл"""
    try:
        if os.path.exists(filename):
            os.remove(filename)
            print("🗑️ Временный файл очищен")
    except Exception as e:
        print(f"❌ Ошибка очистки временного файла: {e}")


def scroll_wildberries_page(driver, max_scrolls=10):
    """Прокрутка страницы Wildberries с обнаружением товаров"""
    print("📜 Начинаем прокрутку страницы Wildberries...")

    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    no_new_content_count = 0
    max_no_new_content = 3

    all_products_data = []
    temp_filename = 'temp_wildberries_gas_stoves.json'

    while scroll_attempts < max_scrolls and no_new_content_count < max_no_new_content:
        # Прокручиваем вниз
        scroll_height = random.randint(800, 1200)
        driver.execute_script(f"window.scrollBy(0, {scroll_height});")

        human_like_delay(2, 4)
        scroll_attempts += 1

        # Проверяем высоту страницы
        new_height = driver.execute_script("return document.body.scrollHeight")

        # Ищем товары после прокрутки
        current_products = find_wildberries_products(driver)
        current_count = len(current_products)

        print(f"📊 После прокрутки {scroll_attempts}: найдено {current_count} товаров")

        # Собираем данные с новых товаров
        if current_products:
            new_data = extract_wildberries_products_data(driver, current_products, len(all_products_data))
            if new_data:
                all_products_data.extend(new_data)
                # Сохраняем во временный файл
                save_to_temp_file(new_data, temp_filename)
                print(f"💾 Сразу сохранено {len(new_data)} новых товаров")

        # Проверяем появление нового контента
        if new_height == last_height:
            no_new_content_count += 1
            print(f"⚠️ Нет нового контента ({no_new_content_count}/{max_no_new_content})")
        else:
            no_new_content_count = 0
            last_height = new_height

        # Случайная пауза
        human_like_delay(1, 2)

        # Пытаемся найти кнопку "Показать еще"
        try:
            load_more_selectors = [
                "button[class*='show-more']",
                "button[class*='load-more']",
                ".j-show-more",
                ".show-more__btn"
            ]

            for selector in load_more_selectors:
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
    return all_products_data


def find_wildberries_products(driver):
    """Поиск товаров на Wildberries"""
    print("🔍 Ищем товары на странице...")

    # Ждем загрузки товаров
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".product-card, .card, [data-card-index]"))
        )
    except:
        print("⏳ Товары загружаются медленно...")

    # Селекторы для товаров Wildberries
    product_selectors = [
        "article.product-card",
        "div.product-card",
        ".card__link",
        "[data-card-index]",
        ".j-card-item",
        ".product-card__wrapper"
    ]

    products = []

    for selector in product_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"Найдено элементов с селектором {selector}: {len(elements)}")

                # Фильтруем только газовые плиты
                for element in elements:
                    try:
                        text = element.text.lower()
                        if len(text) > 30:  # Минимальная длина текста
                            # Проверяем, что это газовая плита
                            is_gas_stove = (
                                    any(word in text for word in ['плита', 'газов', 'газовая', 'газовой']) and
                                    not any(word in text for word in [
                                        'электрич', 'комбинирован', 'электроплита',
                                        'индукцион', 'газоэлектрич', 'походн', 'туристич'
                                    ])
                            )

                            if is_gas_stove:
                                # Проверяем уникальность элемента
                                element_id = element.get_attribute('data-card-index') or element.id
                                if not any(p.get_attribute('data-card-index') == element_id for p in products):
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


def extract_wildberries_products_data(driver, products, existing_count=0):
    """Извлечение данных из товаров Wildberries"""
    products_data = []

    for i, product in enumerate(products, existing_count + 1):
        try:
            print(f"\n--- Обрабатываем товар {i} ---")

            # Прокручиваем к товару
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", product)
            human_like_delay(1, 2)

            # Извлекаем информацию
            name = extract_wildberries_product_name(product)
            price = extract_wildberries_price(product, driver)
            rating = extract_wildberries_rating(product, driver)
            reviews = extract_wildberries_reviews(product, driver)

            print(f"📝 Название: {name[:100] if name else 'Не найдено'}")
            print(f"💰 Цена: {price if price else 'Не найдена'}")
            print(f"⭐ Рейтинг: {rating if rating else 'Не найден'}")
            print(f"📊 Отзывы: {reviews if reviews else 'Не найдены'}")

            if name and price:
                product_data = {
                    'Категория товара': 'Газовая плита',
                    'Модель': name,
                    'Цена': price,
                    'Рейтинг': rating or 0,
                    'Количество отзывов': reviews or 0,
                    'Источник': 'Wildberries',
                    'Время сбора': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                products_data.append(product_data)
                print(f"✅ Добавлена газовая плита: {name[:80]}... - {price} руб.")
            else:
                print(f"❌ Неполные данные - название или цена отсутствуют")

        except Exception as e:
            print(f"⚠️ Ошибка обработки товара {i}: {e}")
            continue

    return products_data


def extract_wildberries_product_name(element):
    """Извлечение названия товара на Wildberries"""
    try:
        # Селекторы для названия товара
        title_selectors = [
            ".product-card__name",
            ".card__name",
            ".goods-name",
            "[data-link*='text={goodsName}']",
            ".j-card-name",
            "span.good-name"
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

        if lines:
            # Ищем строку с названием (самая длинная информативная строка)
            filtered_lines = []
            for line in lines:
                if (len(line) > 15 and
                        not re.search(r'\d{1,3}[ \ ]?\d{3}[ \ ]?\d{0,3}[ \ ]?₽', line) and
                        not re.search(r'отзыв|в корзину|купить|₽|руб|доставка|рейтинг', line.lower())):
                    filtered_lines.append(line)

            if filtered_lines:
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


def extract_wildberries_price(element, driver):
    """Извлечение цены на Wildberries"""
    try:
        # Селекторы для цены Wildberries
        price_selectors = [
            ".price__lower-price",
            ".price-block__final-price",
            ".final-price",
            ".lower-price",
            ".j-final-price",
            "[class*='price__lower']",
            ".price-block__price"
        ]

        for selector in price_selectors:
            try:
                price_elements = element.find_elements(By.CSS_SELECTOR, selector)
                for price_element in price_elements:
                    price_text = price_element.text.strip()
                    if price_text:
                        print(f"Найден текст цены: {price_text}")
                        # Очистка текста
                        clean_text = re.sub(r'[^\d\s]', '', price_text)
                        clean_text = re.sub(r'\s+', '', clean_text)

                        if clean_text and len(clean_text) >= 3:
                            price = int(clean_text)
                            if 1000 <= price <= 500000:
                                print(f"Цена извлечена: {price}")
                                return price
            except:
                continue

        # Поиск с помощью JavaScript
        js_script = """
        var element = arguments[0];
        var text = element.textContent || element.innerText;
        var priceRegex = /\\d{1,3}[\\s ]?\\d{3}[\\s ]?\\d{0,3}/g;
        var matches = text.match(priceRegex);

        if (matches) {
            for (var i = 0; i < matches.length; i++) {
                var cleanPrice = matches[i].replace(/[^\\d]/g, '');
                if (cleanPrice.length >= 3) {
                    var price = parseInt(cleanPrice);
                    if (price >= 1000 && price <= 500000) {
                        return price;
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

        print("Цена не найдена")
        return None

    except Exception as e:
        print(f"Ошибка извлечения цены: {e}")
        return None


def extract_wildberries_rating(element, driver):
    """Извлечение рейтинга товара"""
    try:
        rating_selectors = [
            ".product-card__rating",
            ".j-rating",
            "[data-rating]",
            ".rating",
            ".stars"
        ]

        for selector in rating_selectors:
            try:
                rating_elements = element.find_elements(By.CSS_SELECTOR, selector)
                for rating_element in rating_elements:
                    rating_text = rating_element.text.strip()
                    if rating_text:
                        # Ищем число с плавающей точкой
                        rating_match = re.search(r'(\d+[.,]\d+|\d+)', rating_text)
                        if rating_match:
                            rating = float(rating_match.group(1).replace(',', '.'))
                            if 0 <= rating <= 5:
                                return rating
            except:
                continue

        return 0
    except:
        return 0


def extract_wildberries_reviews(element, driver):
    """Извлечение количества отзывов"""
    try:
        review_selectors = [
            ".product-card__count",
            ".j-feedback-count",
            "[data-review-count]",
            ".review-count"
        ]

        for selector in review_selectors:
            try:
                review_elements = element.find_elements(By.CSS_SELECTOR, selector)
                for review_element in review_elements:
                    review_text = review_element.text.strip()
                    if review_text:
                        # Ищем число
                        review_match = re.search(r'(\d+)', review_text)
                        if review_match:
                            return int(review_match.group(1))
            except:
                continue

        return 0
    except:
        return 0


def parse_wildberries_gas_stoves():
    """Основная функция парсинга газовых плит с Wildberries"""
    driver = setup_driver()
    temp_filename = 'temp_wildberries_gas_stoves.json'

    # Очищаем временный файл перед началом
    clear_temp_file(temp_filename)

    all_data = []

    try:
        # URL для поиска газовых плит на Wildberries
        url = "https://www.wildberries.ru/catalog/bitovaya-tehnika/kuhnya/plity/plity-gazovye"

        # Альтернативный URL через поиск
        backup_url = "https://www.wildberries.ru/catalog/0/search.aspx?search=газовая+плита"

        print(f"🌐 Открываем Wildberries: {url}")
        driver.get(url)
        wait_for_page_load(driver)
        human_like_delay(5, 8)

        # Закрываем попапы
        close_wildberries_popups(driver)

        # Проверяем, загрузилась ли страница
        page_title = driver.title.lower()
        print(f"Заголовок страницы: {driver.title}")

        if "газов" not in page_title and "плит" not in page_title:
            print("⚠️ Возможно неправильная страница, пробуем альтернативный URL...")
            driver.get(backup_url)
            wait_for_page_load(driver)
            human_like_delay(5, 8)
            close_wildberries_popups(driver)

        # Используем улучшенную прокрутку
        all_data = scroll_wildberries_page(driver, max_scrolls=12)

        print(f"\n📊 Парсинг завершен. Всего собрано: {len(all_data)} газовых плит")

    except Exception as e:
        print(f"🚨 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        driver.save_screenshot('wildberries_error.png')
    finally:
        driver.quit()

    return all_data


def remove_duplicates(df):
    """Удаление дубликатов из DataFrame"""
    if df is None or df.empty:
        return df

    print(f"📊 До удаления дубликатов: {len(df)} записей")

    df_clean = df.copy()

    # Удаляем дубликаты по модели и цене
    df_clean = df_clean.drop_duplicates(subset=['Модель', 'Цена'], keep='first')

    # Дополнительная очистка по нормализованным названиям
    df_clean['Модель_норм'] = df_clean['Модель'].str.lower().str.replace(r'[^\w\s]', '', regex=True)
    df_clean = df_clean.drop_duplicates(subset=['Модель_норм', 'Цена'], keep='first')
    df_clean = df_clean.drop('Модель_норм', axis=1)

    print(f"📊 После удаления дубликатов: {len(df_clean)} записей")
    print(f"🗑️ Удалено дубликатов: {len(df) - len(df_clean)}")

    return df_clean


def save_to_excel(data, filename_base='wildberries_gas_stoves'):
    """Сохраняет данные в Excel файлы"""
    if not data:
        print("📭 Нет данных для сохранения")
        return None

    df = pd.DataFrame(data)

    # Сохраняем ВСЕ данные (с дубликатами)
    all_filename = f'{filename_base}_с_дубликатами.xlsx'
    df_all = df.copy()
    df_all = df_all.sort_values('Цена', ascending=False)
    df_all.reset_index(drop=True, inplace=True)
    df_all.index = df_all.index + 1
    df_all['Цена'] = df_all['Цена'].apply(lambda x: f"{x:,} руб.".replace(',', ' '))
    df_all.to_excel(all_filename, index=True, index_label='№')
    print(f"💾 Сохранены все товары (с дубликатами): {len(df_all)} шт. в файл {all_filename}")

    # Удаляем дубликаты для основного файла
    df_clean = remove_duplicates(df)
    df_clean = df_clean.sort_values('Цена', ascending=False)
    df_clean.reset_index(drop=True, inplace=True)
    df_clean.index = df_clean.index + 1
    df_clean['Цена'] = df_clean['Цена'].apply(lambda x: f"{x:,} руб.".replace(',', ' '))

    # Основной файл без дубликатов
    main_filename = f'{filename_base}_без_дубликатов.xlsx'
    df_clean.to_excel(main_filename, index=True, index_label='№')
    print(f"💾 Сохранено {len(df_clean)} газовых плит (без дубликатов) в файл {main_filename}")

    # Удаляем временный файл
    if os.path.exists('temp_wildberries_gas_stoves.json'):
        os.remove('temp_wildberries_gas_stoves.json')
        print("🗑️ Временный файл удален")

    # Выводим результаты
    print("\n🏆 Собранные газовые плиты с Wildberries (без дубликатов):")
    print("-" * 120)
    for i, row in df_clean.iterrows():
        rating_info = f"⭐ {row['Рейтинг']}" if row['Рейтинг'] > 0 else "⭐ 0"
        reviews_info = f"📊 {row['Количество отзывов']} отз." if row['Количество отзывов'] > 0 else "📊 0 отз."
        print(f"{i:2d}. {row['Модель'][:60]}... - {row['Цена']} | {rating_info} | {reviews_info}")
    print("-" * 120)

    # Статистика
    prices_clean = []
    for price_str in df_clean['Цена']:
        try:
            price_num = int(price_str.replace(' руб.', '').replace(' ', ''))
            prices_clean.append(price_num)
        except:
            continue

    if prices_clean:
        avg_price = sum(prices_clean) // len(prices_clean)
        total_reviews = df_clean['Количество отзывов'].sum()
        avg_rating = df_clean['Рейтинг'].mean()

        print(f"\n📈 Статистика (без дубликатов):")
        print(f"   • Всего уникальных плит: {len(prices_clean)}")
        print(f"   • Минимальная цена: {min(prices_clean):,} руб.")
        print(f"   • Максимальная цена: {max(prices_clean):,} руб.")
        print(f"   • Средняя цена: {avg_price:,} руб.")
        print(f"   • Средний рейтинг: {avg_rating:.1f} ⭐")
        print(f"   • Всего отзывов: {total_reviews:,}")

    return df_clean


if __name__ == "__main__":
    print("🚀 Запускаем парсинг газовых плит с Wildberries...")
    print("⏳ Ищем именно ГАЗОВЫЕ модели (исключаем электрические и комбинированные)...")
    print("=" * 80)

    start_time = time.time()

    gas_stoves_data = parse_wildberries_gas_stoves()

    end_time = time.time()
    execution_time = end_time - start_time

    print(f"\n⏱️ Время выполнения: {execution_time:.2f} секунд")
    print(f"📊 Найдено ГАЗОВЫХ плит: {len(gas_stoves_data)}")

    # Сохраняем результаты
    result_df = save_to_excel(gas_stoves_data)

    if not gas_stoves_data:
        print("\n❌ Газовые плиты не найдены на Wildberries")
        print("\n💡 Рекомендации для решения проблемы:")
        print("1. Проверьте доступность сайта Wildberries")
        print("2. Попробуйте использовать VPN")
        print("3. Обновите селекторы в коде под текущую версию сайта")
        print("4. Увеличьте время ожидания загрузки страницы")
        print("5. Проверьте работу антидетект-функций")