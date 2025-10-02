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


def is_dog_food_by_name(text):
    """Проверяет, является ли текст названием корма для собак, особенно для такс"""
    if not text or len(text) < 10:
        return False

    text_lower = text.lower()

    # Ключевые слова для кормов для собак
    dog_keywords = ['корм', 'питание', 'еда', 'food', 'dog']
    breed_keywords = ['такса', 'таксы', 'dachshund', 'для взрослых собак', 'для щенков', 'для собак']
    type_keywords = ['сухой', 'сухого', 'dry', 'гранулы', 'паучи', 'консервы']

    # Бренды кормов для собак
    brand_keywords = [
        'quattro', 'royal canin', 'purina', 'pro plan', 'hills', 'acana', 'orijen',
        'brit', 'probalance', 'monge', 'farmina', 'grandorf', 'now',
        'taste of the wild', 'go', 'nutram', 'eukanuba', 'advance',
        'belcando', 'bosch', 'trainer', 'arcana', 'optima', 'chappi',
        'pedigree', 'aatu', 'savarra', 'wolf of wilderness', 'barking heads'
    ]

    # Исключения (не корм для собак)
    exclude_keywords = [
        'кош', 'кот', 'cat', 'птиц', 'грызун', 'кролик', 'хомяк',
        'аквариум', 'рыб', 'рептилий', 'наполнитель', 'лоток', 'игрушк',
        'поводок', 'ошейник', 'миска', 'лежанка', 'витамин', 'лакомств',
        'амуниция', 'переноск', 'гигиена', 'груминг'
    ]

    # Должны содержать слова связанные с кормом и собаками
    has_dog_food = any(word in text_lower for word in dog_keywords)
    has_breed = any(word in text_lower for word in breed_keywords)
    has_brand = any(word in text_lower for word in brand_keywords)
    has_exclude = any(word in text_lower for word in exclude_keywords)

    # Дополнительные проверки
    is_food = any(word in text_lower for word in ['корм', 'питание', 'food'])

    # Логика определения
    if has_exclude:
        return False

    # Если есть указание на таксу - это наш товар
    if 'такса' in text_lower or 'dachshund' in text_lower:
        return True

    # Если это корм для собак и сухой корм
    if has_dog_food and (has_breed or has_brand) and 'сух' in text_lower:
        return True

    return False


def is_price_line(text):
    """Проверяет, является ли строка ценой"""
    if not text:
        return False
    price_patterns = [
        r'\d{1,3}[ \ ]?\d{3}[ \ ]?\d{0,3}[ \ ]?₽',
        r'\d+[ \ ]?руб',
        r'цена',
        r'₽',
        r'рубл'
    ]
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in price_patterns)


def is_rating_line(text):
    """Проверяет, является ли строка рейтингом или отзывами"""
    if not text:
        return False
    rating_patterns = [
        r'отзыв',
        r'рейтинг',
        r'⭐',
        r'★',
        r'оценк',
        r'rating'
    ]
    text_lower = text.lower()
    return any(word in text_lower for word in rating_patterns)


def is_button_text(text):
    """Проверяет, является ли строка текстом кнопки"""
    if not text:
        return False
    button_texts = [
        'в корзину',
        'купить',
        'заказать',
        'доставка',
        'в избранное',
        'подробнее',
        'корзин'
    ]
    text_lower = text.lower()
    return any(word in text_lower for word in button_texts)


def extract_brand_from_text(text):
    """Извлекает только название бренда из текста"""
    try:
        if not text:
            return None

        text_lower = text.lower()

        # Словарь брендов для поиска
        brands = {
            'quattro': 'Quattro',
            'royal canin': 'Royal Canin',
            'royal canin': 'Royal Canin',
            'purina': 'Purina',
            'pro plan': 'Pro Plan',
            'hills': 'Hills',
            'acana': 'Acana',
            'orijen': 'Orijen',
            'brit': 'Brit',
            'probalance': 'Probalance',
            'monge': 'Monge',
            'farmina': 'Farmina',
            'grandorf': 'Grandorf',
            'taste of the wild': 'Taste of the Wild',
            'belcando': 'Belcando',
            'bosch': 'Bosch',
            'trainer': 'Trainer'
        }

        for brand_key, brand_name in brands.items():
            if brand_key in text_lower:
                return brand_name

        return None
    except Exception as e:
        print(f"Ошибка извлечения бренда: {e}")
        return None


def clean_product_name(name):
    """Очищает название товара от лишних символов, сохраняя бренд"""
    if not name:
        return "Неизвестный корм для собак"

    # Удаляем лишние пробелы
    name = re.sub(r'\s+', ' ', name).strip()

    # Сохраняем формат с брендом если он есть
    if '/' in name:
        parts = name.split('/')
        if len(parts) == 2:
            brand = parts[0].strip()
            product_name = parts[1].strip()

            # Очищаем только название продукта, бренд оставляем как есть
            product_name = re.sub(r'\d{1,3}[ \ ]?\d{3}[ \ ]?\d{0,3}[ \ ]?₽.*$', '', product_name)

            # Удаляем служебные слова только из названия продукта
            words_to_remove = ['купить', 'цена', 'доставка', 'в корзину', '₽', 'руб']
            for word in words_to_remove:
                product_name = re.sub(f'\\b{word}\\b', '', product_name, flags=re.IGNORECASE)

            product_name = re.sub(r'\s+', ' ', product_name).strip()
            return f"{brand} / {product_name}"

    # Если нет формата с брендом, применяем обычную очистку
    name = re.sub(r'\d{1,3}[ \ ]?\d{3}[ \ ]?\d{0,3}[ \ ]?₽.*$', '', name)

    words_to_remove = ['купить', 'цена', 'доставка', 'в корзину', '₽', 'руб']
    for word in words_to_remove:
        name = re.sub(f'\\b{word}\\b', '', name, flags=re.IGNORECASE)

    name = re.sub(r'^[^a-zA-Zа-яА-Я0-9/]+|[^a-zA-Zа-яА-Я0-9/]+$', '', name)
    name = re.sub(r'\s*/\s*', ' / ', name)

    return name.strip()


def extract_wildberries_full_name(element):
    """Специальная функция для извлечения полного названия в формате Wildberries"""
    try:
        full_text = element.text
        if not full_text:
            return None

        lines = [line.strip() for line in full_text.split('\n') if line.strip()]

        # Ищем паттерн: строка с брендом и названием корма
        for i, line in enumerate(lines):
            if (len(line) > 20 and
                    any(brand in line.lower() for brand in [
                        'quattro', 'royal canin', 'purina', 'pro plan', 'hills', 'acana',
                        'orijen', 'brit', 'probalance', 'monge', 'farmina'
                    ]) and
                    any(word in line.lower() for word in ['корм', 'такса', 'собак', 'dog'])):
                # Это наша целевая строка
                clean_name = clean_product_name(line)
                print(f"✅ Извлечено полное название из текста элемента: {clean_name}")
                return clean_name

        # Дополнительная проверка для формата "Бренд / Название"
        for i, line in enumerate(lines):
            if '/' in line and len(line) > 25:
                parts = line.split('/')
                if len(parts) == 2:
                    brand_part = parts[0].strip()
                    name_part = parts[1].strip()
                    if (len(brand_part) > 2 and len(name_part) > 10 and
                            any(word in name_part.lower() for word in ['корм', 'такса', 'собак'])):
                        clean_name = clean_product_name(line)
                        print(f"✅ Извлечено название в формате 'Бренд/Название': {clean_name}")
                        return clean_name

        return None
    except Exception as e:
        print(f"Ошибка извлечения полного названия: {e}")
        return None


def get_full_product_name(driver, product_element):
    """Получает полное название товара, переходя на страницу товара, включая бренд из хлебных крошек"""
    original_window = driver.current_window_handle

    try:
        print("🔄 Переходим на страницу товара для получения полного названия...")

        # Ищем ссылку на товар
        link_selectors = [
            "a.product-card__link",
            "a.j-card-link",
            "a[href*='/catalog/']",
            "a[data-nm-id]",
            ".product-card__name a",
            ".card__link",
            "a[class*='product-card']"
        ]

        product_link = None
        for selector in link_selectors:
            try:
                link = product_element.find_element(By.CSS_SELECTOR, selector)
                if link.is_displayed():
                    product_url = link.get_attribute('href')
                    if product_url and 'wildberries.ru/catalog/' in product_url:
                        product_link = link
                        break
            except:
                continue

        if not product_link:
            print("❌ Не найдена ссылка на товар")
            return None

        # Получаем URL товара
        product_url = product_link.get_attribute('href')
        print(f"📎 URL товара: {product_url}")

        # Открываем товар в новой вкладке
        driver.execute_script("window.open(arguments[0]);", product_url)
        time.sleep(3)

        # Переключаемся на новую вкладку
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(3)

        # Закрываем попапы на странице товара
        close_wildberries_popups(driver)

        # Ждем загрузки страницы товара
        wait_for_page_load(driver)
        human_like_delay(2, 3)

        # Получаем бренд из хлебных крошек
        brand_name = None
        try:
            # Селекторы для хлебных крошек Wildberries
            breadcrumb_selectors = [
                ".breadcrumbs__item:last-child",
                ".bread-crumbs__item:last-child",
                ".breadcrumb__item:last-child",
                ".breadcrumbs li:last-child",
                "[data-tag='breadcrumbLastItem']",
                ".j-breadcrumb-last"
            ]

            for selector in breadcrumb_selectors:
                try:
                    breadcrumb_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for breadcrumb_element in breadcrumb_elements:
                        brand_candidate = breadcrumb_element.text.strip()
                        if brand_candidate and len(brand_candidate) > 1 and len(brand_candidate) < 50:
                            # Проверяем, что это не служебные слова
                            exclude_words = ['главная', 'каталог', 'поиск', 'отзывы', 'акции', 'скидки', 'новинки']
                            if brand_candidate.lower() not in exclude_words:
                                brand_name = brand_candidate
                                print(f"🏷️ Бренд из хлебных крошек: {brand_name}")
                                break
                    if brand_name:
                        break
                except:
                    continue

        except Exception as e:
            print(f"⚠️ Ошибка при извлечении бренда: {e}")

        # Получаем полное название со страницы товара
        full_name = None

        # Сначала пробуем найти в h1 и основных заголовках
        name_selectors = [
            "h1.product-page__title",
            "h1.same-part-kt__header",
            ".product-page__header h1",
            "h1.product-card__name",
            "h1",
            ".product-name",
            ".product__name",
            "[data-link*='text{:product^goodsName}']",
            ".product-title",
            ".goods-name"
        ]

        for selector in name_selectors:
            try:
                name_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for name_element in name_elements:
                    candidate_name = name_element.text.strip()
                    if candidate_name and len(candidate_name) > 10:
                        full_name = candidate_name
                        print(f"✅ Полное название найдено через селектор {selector}: {full_name[:80]}...")

                        # Если есть бренд и его нет в названии - добавляем бренд в начало
                        if brand_name and brand_name.lower() not in full_name.lower():
                            full_name = f"{brand_name} / {full_name}"
                            print(f"✅ Добавлен бренд к названию: {full_name[:80]}...")
                        break
                if full_name:
                    break
            except:
                continue

        # Если не нашли, пробуем найти в мета-тегах
        if not full_name:
            try:
                # Мета-тег title
                meta_title = driver.execute_script("return document.title;")
                if meta_title and len(meta_title) > 10:
                    # Очищаем title от лишнего
                    clean_title = re.sub(r'\s*[–-]\s*Wildberries.*$', '', meta_title)
                    if len(clean_title) > 10:
                        full_name = clean_title
                        # Добавляем бренд если есть
                        if brand_name and brand_name.lower() not in full_name.lower():
                            full_name = f"{brand_name} / {full_name}"
                        print(f"✅ Название из заголовка страницы: {full_name[:80]}...")

                # Мета-тег og:title
                if not full_name:
                    og_title = driver.find_element(By.CSS_SELECTOR, "meta[property='og:title']").get_attribute(
                        'content')
                    if og_title and len(og_title) > 10:
                        full_name = og_title
                        # Добавляем бренд если есть
                        if brand_name and brand_name.lower() not in full_name.lower():
                            full_name = f"{brand_name} / {full_name}"
                        print(f"✅ Название из og:title: {full_name[:80]}...")
            except:
                pass

        # Если все еще не нашли, пробуем поискать в структуре данных
        if not full_name:
            try:
                # Ищем в JSON-LD структуре
                scripts = driver.find_elements(By.CSS_SELECTOR, "script[type='application/ld+json']")
                for script in scripts:
                    try:
                        json_data = json.loads(script.get_attribute('innerHTML'))
                        if isinstance(json_data, dict) and 'name' in json_data:
                            candidate_name = json_data['name']
                            if candidate_name and len(candidate_name) > 10:
                                full_name = candidate_name
                                # Добавляем бренд если есть
                                if brand_name and brand_name.lower() not in full_name.lower():
                                    full_name = f"{brand_name} / {full_name}"
                                print(f"✅ Название из JSON-LD: {full_name[:80]}...")
                                break
                    except:
                        continue
            except:
                pass

        # Если нашли только бренд, но не нашли полное название
        if not full_name and brand_name:
            # Пробуем найти любое название товара на странице
            try:
                all_text = driver.find_element(By.TAG_NAME, "body").text
                lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                for line in lines:
                    if len(line) > 20 and len(line) < 200 and ('корм' in line.lower() or 'такса' in line.lower()):
                        full_name = f"{brand_name} / {line}"
                        print(f"✅ Составное название из текста страницы: {full_name[:80]}...")
                        break
            except:
                pass

        # Закрываем вкладку и возвращаемся
        driver.close()
        driver.switch_to.window(original_window)
        time.sleep(2)

        return full_name

    except Exception as e:
        print(f"❌ Ошибка при получении полного названия: {e}")
        # В случае ошибки пытаемся вернуться на исходную вкладку
        try:
            if len(driver.window_handles) > 1:
                driver.close()
            driver.switch_to.window(original_window)
        except:
            pass
        return None


def enhance_product_name(name):
    """Улучшает название товара, сохраняя оригинальный формат с брендом"""
    if not name:
        return "Неизвестный корм для собак"

    # Если название уже содержит формат "БРЕНД / Название", оставляем как есть
    if '/' in name and len(name.split('/')) == 2:
        parts = name.split('/')
        brand = parts[0].strip()
        model = parts[1].strip()

        # Проверяем, что это действительно бренд и модель
        if (len(brand) > 1 and len(brand) < 20 and
                len(model) > 5 and any(word in model.lower() for word in ['корм', 'питание', 'food'])):
            return f"{brand} / {model}"

    # Словарь брендов для улучшенного определения
    brands_mapping = {
        'quattro': 'Quattro',
        'royal canin': 'Royal Canin', 'роял канин': 'Royal Canin',
        'purina': 'Purina', 'пурина': 'Purina',
        'pro plan': 'Pro Plan', 'про план': 'Pro Plan',
        'hills': 'Hills', 'хиллс': 'Hills',
        'acana': 'Acana', 'акана': 'Acana',
        'orijen': 'Orijen', 'ориджен': 'Orijen',
        'brit': 'Brit', 'брит': 'Brit',
        'probalance': 'Probalance', 'пробаланс': 'Probalance',
        'monge': 'Monge', 'монж': 'Monge',
        'farmina': 'Farmina', 'фармина': 'Farmina',
        'grandorf': 'Grandorf', 'грандорф': 'Grandorf',
        'taste of the wild': 'Taste of the Wild',
        'belcando': 'Belcando', 'белькандо': 'Belcando',
        'bosch': 'Bosch', 'бош': 'Bosch',
        'trainer': 'Trainer', 'тренер': 'Trainer',
        'arcana': 'Arcana', 'аркана': 'Arcana',
        'optima': 'Optima', 'оптима': 'Optima',
        'chappi': 'Chappi', 'чаппи': 'Chappi',
        'pedigree': 'Pedigree', 'педигри': 'Pedigree'
    }

    # Приводим к нижнему регистру для поиска
    name_lower = name.lower()

    # Проверяем, содержит ли название слово "корм"
    has_food_keyword = any(word in name_lower for word in ['корм', 'питание', 'food'])

    # Проверяем, содержит ли название слово "такса"
    has_dachshund_keyword = any(word in name_lower for word in ['такса', 'dachshund'])

    # Ищем бренд в названии
    found_brand = None
    for brand_key, brand_name in brands_mapping.items():
        if brand_key in name_lower:
            found_brand = brand_name
            break

    # Улучшаем название
    improved_name = name.strip()

    # Если бренд уже есть в названии, но не в начале - переставляем
    if found_brand and found_brand.lower() in name_lower:
        # Если название не начинается с бренда, переставляем
        if not improved_name.startswith(found_brand):
            # Удаляем бренд из середины/конца и ставим в начало
            improved_name = re.sub(f'{found_brand}\\s*', '', improved_name, flags=re.IGNORECASE)
            improved_name = f"{found_brand} / {improved_name}".strip()

    # Если есть бренд в словаре, но его нет в названии - добавляем
    elif found_brand and found_brand.lower() not in name_lower:
        # Проверяем, начинается ли название с "Корм"
        if improved_name.startswith('Корм'):
            # Вставляем бренд после "Корм"
            parts = improved_name.split(' ', 1)
            if len(parts) >= 2:
                improved_name = f"{parts[0]} {found_brand} {parts[1]}"
            else:
                improved_name = f"Корм {found_brand} {improved_name}"
        else:
            # Добавляем бренд в начало
            if not has_food_keyword and has_dachshund_keyword:
                improved_name = f"Корм {found_brand} / {improved_name}"
            else:
                improved_name = f"{found_brand} / {improved_name}"

    # Если нет указания на таксу, но есть указание на корм - проверяем контекст
    elif not has_dachshund_keyword and has_food_keyword:
        # Если это корм для собак, но не указано порода, оставляем как есть
        if 'собак' not in name_lower and 'dog' not in name_lower:
            improved_name = f"Корм для собак {improved_name}"

    # Удаляем возможные дублирования
    improved_name = re.sub(r'Корм для собак Корм для собак', 'Корм для собак', improved_name)
    improved_name = re.sub(r'\s+', ' ', improved_name).strip()

    return improved_name


def debug_element_text(element, element_index):
    """Отладочная функция для анализа текста элемента"""
    try:
        text = element.text
        if not text or len(text) < 10:
            return

        print(f"\n🔍 [Элемент {element_index}] Полный текст:")
        print("-" * 50)
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.strip():
                print(f"{i:2d}. {line.strip()}")
        print("-" * 50)

    except Exception as e:
        print(f"Ошибка отладки элемента: {e}")


def extract_wildberries_product_name(element, driver=None):
    """Извлечение названия товара на Wildberries с сохранением полного названия с брендом"""
    try:
        # Сохраняем оригинальный текст элемента для поиска бренда
        original_text = element.text
        original_brand = None

        # Пытаемся найти бренд в оригинальном тексте
        if original_text:
            lines = [line.strip() for line in original_text.split('\n') if line.strip()]
            for line in lines:
                line_lower = line.lower()
                # Ищем известные бренды в тексте
                brands_found = [
                    'quattro', 'royal canin', 'purina', 'pro plan', 'hills', 'acana',
                    'orijen', 'brit', 'probalance', 'monge', 'farmina', 'grandorf',
                    'taste of the wild', 'belcando', 'bosch', 'trainer', 'arcana',
                    'optima', 'chappi', 'pedigree'
                ]
                for brand in brands_found:
                    if brand in line_lower:
                        # Нашли бренд - извлекаем всю строку
                        original_brand = line
                        print(f"🏷️ Найден бренд в оригинальном тексте: {original_brand}")
                        break
                if original_brand:
                    break

        # Пробуем сначала извлечь полное название в формате Wildberries
        full_name = extract_wildberries_full_name(element)
        if full_name:
            return full_name

        # Если нашли бренд в оригинальном тексте, используем его как основу
        if original_brand and is_dog_food_by_name(original_brand):
            final_name = clean_product_name(original_brand)
            print(f"🎯 Используем название с брендом из оригинального текста: {final_name}")
            return final_name

        # Сначала пробуем получить полное название из текста элемента
        full_text = element.text
        if full_text and len(full_text) > 30:
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]

            # Ищем строку, содержащую и бренд и название корма
            brand_food_line = None
            for line in lines:
                line_lower = line.lower()
                # Проверяем, содержит ли строка бренд и признаки корма для собак
                has_brand = any(brand in line_lower for brand in [
                    'quattro', 'royal canin', 'purina', 'pro plan', 'hills', 'acana',
                    'orijen', 'brit', 'probalance', 'monge', 'farmina'
                ])
                has_food = any(word in line_lower for word in ['корм', 'такса', 'собак', 'dog'])

                if has_brand and has_food and len(line) > 20:
                    brand_food_line = line
                    print(f"✅ Найдена строка с брендом и кормом: {brand_food_line}")
                    break

            # Если нашли строку с брендом и кормом, используем её
            if brand_food_line:
                final_name = clean_product_name(brand_food_line)
                print(f"🎯 Используем полное название из текста элемента: {final_name}")
                return final_name

        # Если не нашли полное название в тексте, используем старую логику
        base_name = None

        # Селекторы для названия товара Wildberries
        title_selectors = [
            ".product-card__name span",
            ".product-card__name",
            ".card__name",
            ".goods-name",
            ".j-card-name",
            ".product-card__brand-name",
            "[data-nm-id] .product-card__name",
            ".product-card__link .product-card__name",
            ".product-card__info .product-card__name",
            ".card-product__name",
            ".product-card__title",
            ".product-card__link"
        ]

        for selector in title_selectors:
            try:
                title_elements = element.find_elements(By.CSS_SELECTOR, selector)
                for title_element in title_elements:
                    title_text = title_element.text.strip()
                    if title_text and len(title_text) > 5:
                        # Проверяем, похоже ли на название корма для собак
                        if is_dog_food_by_name(title_text) or len(title_text) > 15:
                            base_name = clean_product_name(title_text)
                            if len(base_name) > 10:
                                print(f"✅ Базовое название из селектора {selector}: {base_name[:80]}...")
                                break
                if base_name:
                    break
            except:
                continue

        # Если не нашли базовое название, пробуем альтернативные методы
        if not base_name:
            # Пробуем найти в data-атрибутах
            try:
                data_name = element.get_attribute('data-nm-id')
                if data_name:
                    # Пробуем найти название через data-атрибуты
                    name_attr = element.get_attribute('data-product-name')
                    if name_attr and len(name_attr) > 10:
                        base_name = clean_product_name(name_attr)
                        print(f"✅ Название из data-атрибута: {base_name[:80]}...")
            except:
                pass

        # Получаем полное название если доступен драйвер
        full_name = None
        if driver and base_name:
            print("🔄 Пробуем получить полное название со страницы товара...")
            full_name = get_full_product_name(driver, element)

        # Выбираем лучшее название
        final_name = None
        if full_name:
            # Если у нас есть оригинальный бренд, добавляем его к названию
            if original_brand and not any(brand in full_name.lower() for brand in ['quattro', 'royal canin']):
                # Извлекаем только бренд из оригинального текста
                brand_only = extract_brand_from_text(original_brand)
                if brand_only:
                    final_name = f"{brand_only} / {full_name}"
                    print(f"🎯 Добавили оригинальный бренд к названию со страницы: {final_name[:80]}...")
                else:
                    final_name = enhance_product_name(full_name)
            else:
                final_name = enhance_product_name(full_name)
                print(f"🎯 Используем полное название со страницы: {final_name[:80]}...")
        elif base_name:
            # Если есть базовое название, добавляем к нему бренд если нужно
            if original_brand and not any(brand in base_name.lower() for brand in ['quattro', 'royal canin']):
                brand_only = extract_brand_from_text(original_brand)
                if brand_only:
                    final_name = f"{brand_only} / {base_name}"
                    print(f"🎯 Добавили оригинальный бренд к базовому названию: {final_name[:80]}...")
                else:
                    final_name = enhance_product_name(base_name)
            else:
                final_name = enhance_product_name(base_name)
                print(f"🎯 Используем улучшенное базовое название: {final_name[:80]}...")
        else:
            # Альтернативный подход: анализируем весь текст элемента
            if full_text and len(full_text) > 30:
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]

                # Фильтруем строкы для названия
                name_candidates = []
                for line in lines:
                    if (len(line) > 10 and
                            not is_price_line(line) and
                            not is_rating_line(line) and
                            not is_button_text(line) and
                            'скидк' not in line.lower()):
                        name_candidates.append(line)

                if name_candidates:
                    # Выбираем самую длинную строку как название
                    best_name = max(name_candidates, key=len)
                    # Добавляем бренд если нужно
                    if original_brand and not any(brand in best_name.lower() for brand in ['quattro', 'royal canin']):
                        brand_only = extract_brand_from_text(original_brand)
                        if brand_only:
                            final_name = f"{brand_only} / {best_name}"
                        else:
                            final_name = enhance_product_name(clean_product_name(best_name))
                    else:
                        final_name = enhance_product_name(clean_product_name(best_name))
                    print(f"🎯 Используем название из текста элемента: {final_name[:80]}...")

        if not final_name:
            print("❌ Название не найдено или не соответствует критериям корма для такс")
            return "Неизвестный корм для собак"

        return final_name

    except Exception as e:
        print(f"⚠️ Ошибка извлечения названия: {e}")
        return "Неизвестный корм для собак"


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
            ".price-block__price",
            ".price-block__final-price-wrapper",
            ".product-card__price"
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
                            if 100 <= price <= 10000:  # Диапазон цен для кормов
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
                    if (price >= 100 && price <= 10000) {
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
            ".stars",
            ".product-card__rate"
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
            ".review-count",
            ".product-card__feedback"
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


def save_to_temp_file(data, filename='temp_wildberries_dog_food.json'):
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


def load_from_temp_file(filename='temp_wildberries_dog_food.json'):
    """Загружает данные из временного файла"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"❌ Ошибка загрузки из временного файл: {e}")
        return []


def clear_temp_file(filename='temp_wildberries_dog_food.json'):
    """Очищает временный файл"""
    try:
        if os.path.exists(filename):
            os.remove(filename)
            print("🗑️ Временный файл очищен")
    except Exception as e:
        print(f"❌ Ошибка очистки временного файла: {e}")


def find_wildberries_products(driver):
    """Поиск товаров на Wildberries с улучшенной фильтрацией"""
    print("🔍 Ищем товары на странице...")

    # Ждем загрузки товаров
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".product-card, .card, [data-nm-id]"))
        )
    except:
        print("⏳ Товары загружаются медленно...")

    # Селекторы для товаров Wildberries (обновленные)
    product_selectors = [
        "article.product-card",
        "div.product-card",
        ".product-card__wrapper",
        "[data-nm-id]",
        ".j-card-item",
        ".card__link"
    ]

    products = []
    seen_names = set()

    for selector in product_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"Найдено элементов с селектором {selector}: {len(elements)}")

            for element in elements:
                try:
                    # Пробуем извлечь название для проверки
                    name = extract_wildberries_product_name(element)

                    # Проверяем, что это корм для такс и название не повторяется
                    if (name != "Неизвестный корм для собак" and
                            name not in seen_names and
                            len(name) > 10):
                        seen_names.add(name)
                        products.append(element)
                        print(f"✅ Добавлен корм для такс: {name[:80]}...")

                except Exception as e:
                    print(f"⚠️ Ошибка проверки элемента: {e}")
                    continue

        except Exception as e:
            print(f"Ошибка при поиске по селектору {selector}: {e}")
            continue

    print(f"✅ Всего найдено кормов для такс: {len(products)}")
    return products


def extract_wildberries_products_data(driver, products, existing_count=0):
    """Извлечение данных из товаров Wildberries с улучшенным логированием"""
    products_data = []

    for i, product in enumerate(products, existing_count + 1):
        try:
            print(f"\n{'=' * 60}")
            print(f"🛒 Обрабатываем товар {i}/{len(products)}")
            print(f"{'=' * 60}")

            # Прокручиваем к товару
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", product)
            human_like_delay(1, 2)

            # Отладочная информация
            debug_element_text(product, i)

            # Извлекаем информацию (передаем driver для получения полного названия)
            name = extract_wildberries_product_name(product, driver)
            price = extract_wildberries_price(product, driver)

            print(f"📝 Название: {name}")
            print(f"💰 Цена: {price if price else 'Не найдена'}")

            if name and price and name != "Неизвестный корм для собак":
                product_data = {
                    'Название товара': name,
                    'Цена': price,
                    'Источник': 'Wildberries'
                }
                products_data.append(product_data)
                print(f"✅ УСПЕХ: Добавлен корм для такс")
            else:
                print(f"❌ ПРОПУСК: Неполные данные")

        except Exception as e:
            print(f"⚠️ Ошибка обработки товара {i}: {e}")
            continue

    return products_data


def scroll_wildberries_page(driver, max_scrolls=2):
    """Прокрутка страницы Wildberries с обнаружением товаров"""
    print(f"📜 Начинаем прокрутку страницы Wildberries... (максимум {max_scrolls} прокрутки)")

    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    no_new_content_count = 0
    max_no_new_content = 2

    all_products_data = []
    temp_filename = 'temp_wildberries_dog_food.json'

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


def parse_wildberries_dog_food():
    """Основная функция парсинга кормов для такс с Wildberries"""
    driver = setup_driver()
    temp_filename = 'temp_wildberries_dog_food.json'

    # Очищаем временный файл перед началом
    clear_temp_file(temp_filename)

    all_data = []

    try:
        # URL для поиска через поисковую строку Wildberries
        search_url = "https://www.wildberries.ru/catalog/0/search.aspx?search=%D1%81%D1%83%D1%85%D0%BE%D0%B9%20%D0%BA%D0%BE%D1%80%D0%BC%20%D0%B4%D0%BB%D1%8F%20%D1%82%D0%B0%D0%BA%D1%81%D1%8B"

        print(f"🌐 Открываем Wildberries через поиск: {search_url}")
        driver.get(search_url)
        wait_for_page_load(driver)
        human_like_delay(5, 8)

        # Закрываем попапы
        close_wildberries_popups(driver)

        # Проверяем, загрузилась ли страница
        page_title = driver.title.lower()
        print(f"Заголовок страницы: {driver.title}")

        if "корм" not in page_title and "такса" not in page_title:
            print("⚠️ Возможно неправильная страница, проверяем результаты поиска...")

        # Используем улучшенную прокрутку (только 2 прокрутки)
        all_data = scroll_wildberries_page(driver, max_scrolls=2)

        print(f"\n📊 Парсинг завершен. Всего собрано: {len(all_data)} кормов для такс")

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

    # Удаляем дубликаты по названию и цене
    df_clean = df_clean.drop_duplicates(subset=['Название товара', 'Цена'], keep='first')

    # Дополнительная очистка по нормализованным названиям
    df_clean['Название_норм'] = df_clean['Название товара'].str.lower().str.replace(r'[^\w\s]', '', regex=True)
    df_clean = df_clean.drop_duplicates(subset=['Название_норм', 'Цена'], keep='first')
    df_clean = df_clean.drop('Название_норм', axis=1)

    print(f"📊 После удаления дубликатов: {len(df_clean)} записей")
    print(f"🗑️ Удалено дубликатов: {len(df) - len(df_clean)}")

    return df_clean


def save_to_excel(data, filename_base='wildberries_dog_food'):
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
    df_all.to_excel(all_filename, index=True, index_label='№')
    print(f"💾 Сохранены все товары (с дубликатами): {len(df_all)} шт. в файл {all_filename}")

    # Удаляем дубликаты для основного файла
    df_clean = remove_duplicates(df)
    df_clean = df_clean.sort_values('Цена', ascending=False)
    df_clean.reset_index(drop=True, inplace=True)
    df_clean.index = df_clean.index + 1

    # Основной файл без дубликатов
    main_filename = f'{filename_base}_без_дубликатов.xlsx'
    df_clean.to_excel(main_filename, index=True, index_label='№')
    print(f"💾 Сохранено {len(df_clean)} кормов для такс (без дубликатов) в файл {main_filename}")

    # Удаляем временный файл
    if os.path.exists('temp_wildberries_dog_food.json'):
        os.remove('temp_wildberries_dog_food.json')
        print("🗑️ Временный файл удален")

    # Для вывода в консоль используем форматирование
    print("\n🏆 Собранные корма для такс с Wildberries (без дубликатов):")
    print("-" * 120)
    for i, row in df_clean.iterrows():
        # Форматируем только для вывода в консоль
        price_formatted = f"{row['Цена']:,} руб.".replace(',', ' ')
        print(f"{i:2d}. {row['Название товара'][:80]}... - {price_formatted}")
    print("-" * 120)

    # Статистика (используем исходные числовые значения)
    if not df_clean.empty:
        prices_clean = df_clean['Цена'].tolist()
        avg_price = sum(prices_clean) // len(prices_clean)

        print(f"\n📈 Статистика (без дубликатов):")
        print(f"   • Всего уникальных кормов: {len(prices_clean)}")
        print(f"   • Минимальная цена: {min(prices_clean):,} руб.".replace(',', ' '))
        print(f"   • Максимальная цена: {max(prices_clean):,} руб.".replace(',', ' '))
        print(f"   • Средняя цена: {avg_price:,} руб.".replace(',', ' '))

    return df_clean


if __name__ == "__main__":
    print("🚀 Запускаем парсинг кормов для такс с Wildberries...")
    print("⏳ Ищем именно СУХИЕ КОРМА для ТАКС (исключаем другие товары для животных)...")
    print("=" * 80)

    start_time = time.time()

    dog_food_data = parse_wildberries_dog_food()

    end_time = time.time()
    execution_time = end_time - start_time

    print(f"\n⏱️ Время выполнения: {execution_time:.2f} секунд")
    print(f"📊 Найдено кормов для такс: {len(dog_food_data)}")

    # Сохраняем результаты
    result_df = save_to_excel(dog_food_data)

    if not dog_food_data:
        print("\n❌ Корма для такс не найдены на Wildberries")
        print("\n💡 Рекомендации для решения проблемы:")
        print("1. Проверьте доступность сайта Wildberries")
        print("2. Попробуйте использовать VPN")
        print("3. Обновите селекторы в коде под текущую версию сайта")
        print("4. Увеличьте время ожидания загрузки страницы")
        print("5. Проверьте работу антидетект-функций")