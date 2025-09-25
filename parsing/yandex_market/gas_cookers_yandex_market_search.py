from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
import pandas as pd
import time
import re
import json
import os
from datetime import datetime


def setup_driver():
    """Настройка драйвера с stealth режимом"""
    options = Options()

    # Базовые настройки
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-infobars')

    # User-agent
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--accept-lang=ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7')

    # Экспериментальные настройки
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

    return driver


def close_popups(driver):
    """Закрытие всплывающих окон и попапов"""
    try:
        time.sleep(2)
        # Закрываем куки
        try:
            cookie_btn = driver.find_element(By.CSS_SELECTOR,
                                             'button[data-grab-id*="cookie"], [data-id*="cookie"], [data-auto*="cookie"]')
            cookie_btn.click()
            time.sleep(1)
        except:
            pass

        # Закрываем другие попапы
        close_buttons = driver.find_elements(By.CSS_SELECTOR,
                                             'button[aria-label*="Закрыть"], ._popup-close, .close-button, [data-zone-name*="close"]')
        for button in close_buttons:
            try:
                if button.is_displayed():
                    button.click()
                    time.sleep(0.5)
            except:
                pass

    except Exception as e:
        print(f"Ошибка при закрытии попапов: {e}")


def save_to_temp_file(data, filename='temp_gas_stoves.json'):
    """Сохраняет данные во временный файл"""
    try:
        # Читаем существующие данные
        existing_data = []
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        # Добавляем новые данные
        existing_data.extend(data)

        # Сохраняем обратно
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        print(f"💾 Сохранено {len(data)} записей во временный файл. Всего записей: {len(existing_data)}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения во временный файл: {e}")
        return False


def load_from_temp_file(filename='temp_gas_stoves.json'):
    """Загружает данные из временного файла"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"❌ Ошибка загрузки из временного файла: {e}")
        return []


def clear_temp_file(filename='temp_gas_stoves.json'):
    """Очищает временный файл"""
    try:
        if os.path.exists(filename):
            os.remove(filename)
            print("🗑️ Временный файл очищен")
    except Exception as e:
        print(f"❌ Ошибка очистки временного файла: {e}")


def parse_gas_stoves():
    """Парсинг газовых плит через поиск с сохранением во временный файл"""
    driver = setup_driver()
    temp_filename = 'temp_gas_stoves.json'

    # Очищаем временный файл перед началом нового парсинга
    clear_temp_file(temp_filename)

    try:
        # URL поиска газовых плит
        url = "https://market.yandex.ru/search?text=газовые%20плиты&hid=16147374&onstock=1"

        print("Открываем страницу поиска газовых плит...")
        driver.get(url)
        time.sleep(5)

        # Закрываем попапы
        close_popups(driver)
        time.sleep(2)

        # Проверяем заголовок страницы
        page_title = driver.title.lower()
        print(f"Заголовок страницы: {driver.title}")

        all_products_data = []

        # Прокручиваем страницу для загрузки товаров и сохраняем данные после каждой прокрутки
        print("Прокручиваем страницу для загрузки товаров...")
        for scroll_iteration in range(5):  # Увеличим количество прокруток
            print(f"\n--- Прокрутка {scroll_iteration + 1} ---")

            # Прокручиваем страницу
            driver.execute_script(f"window.scrollTo(0, {2000 * (scroll_iteration + 1)});")
            time.sleep(3)

            # Даем время для загрузки контента
            time.sleep(2)

            print("Ищем товары на текущей позиции...")

            # Селекторы для товаров
            product_selectors = [
                'article',
                '[data-zone-name="snippet"]',
                '[data-autotest-id="product-snippet"]',
                '._2U08a',
                '.n-snippet-cell',
                '[data-zone-data*="snippet"]'
            ]

            products = []
            for selector in product_selectors:
                try:
                    found_products = driver.find_elements(By.CSS_SELECTOR, selector)
                    if found_products:
                        print(f"Найдено товаров с селектором '{selector}': {len(found_products)}")
                        products = found_products
                        break
                except:
                    continue

            if not products:
                # Пробуем найти любые товары на странице
                print("Пробуем альтернативный поиск товаров...")
                all_elements = driver.find_elements(By.CSS_SELECTOR, 'div, article, section')
                products = [p for p in all_elements if p.get_attribute('data-zone-name') == 'snippet']
                if not products:
                    print("❌ Не удалось найти товары на этой прокрутке. Продолжаем...")
                    continue

            print(f"✅ Найдено {len(products)} товаров для обработки на прокрутке {scroll_iteration + 1}")

            current_scroll_data = []
            processed_models = set()  # Для отслеживания дубликатов в текущей прокрутке

            for i, product in enumerate(products, 1):
                try:
                    # Прокручиваем к товару
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                          product)
                    time.sleep(0.5)

                    # Получаем весь текст элемента
                    product_text = product.text
                    if not product_text or len(product_text) < 50:
                        continue  # Пропускаем пустые или слишком короткие элементы

                    # Поиск названия
                    name = None
                    name_selectors = [
                        'h3',
                        'a[href*="/product/"]',
                        '[data-zone-name="title"]',
                        '.n-snippet-card2__title',
                        '._3EX9a',
                        '.N9L7oc'
                    ]

                    for selector in name_selectors:
                        try:
                            name_elem = product.find_element(By.CSS_SELECTOR, selector)
                            candidate_name = name_elem.text.strip()
                            if candidate_name and len(candidate_name) > 10:
                                name = candidate_name
                                break
                        except:
                            continue

                    # Если не нашли по селекторам, ищем в тексте
                    if not name and product_text:
                        lines = [line.strip() for line in product_text.split('\n') if line.strip()]
                        for line in lines:
                            if len(line) > 20 and any(word in line.lower() for word in
                                                      ['плита', 'газов', 'gorenje', 'bosch', 'electrolux', 'indesit',
                                                       'darina', 'гефест', 'аристон', 'hotpoint']):
                                name = line
                                break

                    # Если все еще не нашли, берем первую длинную строку
                    if not name and product_text:
                        lines = [line.strip() for line in product_text.split('\n') if len(line.strip()) > 20]
                        if lines:
                            name = lines[0]

                    if not name:
                        continue  # Пропускаем если не нашли название

                    # Поиск цены
                    price = None
                    try:
                        # Ищем цену регулярным выражением
                        price_pattern = r'(\d{1,3}(?:\s?\d{3})*(?:\s?\d{3})*)\s*[₽рруб]'
                        matches = re.findall(price_pattern, product_text, re.IGNORECASE)
                        if matches:
                            price = matches[0].replace(' ', '').replace(' ', '').replace(' ', '')
                        else:
                            # Пробуем селекторы цены
                            price_selectors = [
                                '[data-zone-name="price"]',
                                '.price',
                                '._1u3jP',
                                '.n-snippet-card2__price',
                                '.N9L7oc+div'
                            ]
                            for selector in price_selectors:
                                try:
                                    price_elem = product.find_element(By.CSS_SELECTOR, selector)
                                    price_text = price_elem.text
                                    price_match = re.search(price_pattern, price_text, re.IGNORECASE)
                                    if price_match:
                                        price = price_match.group(1).replace(' ', '').replace(' ', '').replace(' ', '')
                                        break
                                except:
                                    continue

                    except Exception as e:
                        print(f"Ошибка поиска цены: {e}")

                    # Сохраняем данные
                    if name and price:
                        try:
                            # Преобразуем цену в число
                            price_num = int(price) if price.isdigit() else 0

                            # Создаем уникальный идентификатор для проверки дубликатов
                            product_id = f"{name[:100]}_{price_num}"

                            if product_id not in processed_models:
                                product_data = {
                                    'Категория товара': 'Газовая плита',
                                    'Модель': name,
                                    'Цена': price_num,
                                    'Время сбора': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'Прокрутка': scroll_iteration + 1
                                }

                                current_scroll_data.append(product_data)
                                processed_models.add(product_id)

                                print(f"✅ Обработан: {name[:50]}... - {price_num} руб.")

                        except Exception as e:
                            print(f"❌ Ошибка преобразования цены: {e}")

                except Exception as e:
                    print(f"⚠️ Ошибка обработки товара {i}: {e}")
                    continue

            # Сохраняем данные текущей прокрутки во временный файл
            if current_scroll_data:
                save_to_temp_file(current_scroll_data, temp_filename)
                all_products_data.extend(current_scroll_data)
                print(f"💾 Добавлено {len(current_scroll_data)} записей из прокрутки {scroll_iteration + 1}")

        # Загружаем все данные из временного файла для итоговой обработки
        final_data = load_from_temp_file(temp_filename)
        return final_data

    except Exception as e:
        print(f"🚨 Критическая ошибка: {e}")
        driver.save_screenshot('error.png')
        # Возвращаем данные, которые успели сохранить
        return load_from_temp_file(temp_filename)

    finally:
        driver.quit()


def save_to_excel(data, filename_base='yandex_market_gas_stoves'):
    """Сохраняет данные в Excel файлы с дубликатами и без"""
    if not data:
        print("📭 Нет данных для сохранения")
        return

    # Создаем DataFrame
    df = pd.DataFrame(data)

    # Добавляем столбец с уникальным идентификатором для поиска дубликатов
    df['Уникальный_ID'] = df['Модель'].str[:100] + '_' + df['Цена'].astype(str)

    # Файл БЕЗ дубликатов
    df_no_duplicates = df.drop_duplicates(subset=['Уникальный_ID'], keep='first')
    df_no_duplicates = df_no_duplicates.drop(columns=['Уникальный_ID'])

    # Сортируем по цене
    df_no_duplicates = df_no_duplicates.sort_values('Цена', ascending=False)

    # Файл С дубликатами
    df_with_duplicates = df.drop(columns=['Уникальный_ID'])
    df_with_duplicates = df_with_duplicates.sort_values(['Цена', 'Время сбора'], ascending=[False, True])

    # Генерируем имя файла с timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_no_duplicates = f'{filename_base}_без_дубликатов_{timestamp}.xlsx'
    filename_with_duplicates = f'{filename_base}_с_дубликатами_{timestamp}.xlsx'

    # Сохраняем в Excel
    df_no_duplicates.to_excel(filename_no_duplicates, index=False)
    df_with_duplicates.to_excel(filename_with_duplicates, index=False)

    print(f"\n💾 Сохранено результатов:")
    print(f"   • Без дубликатов: {len(df_no_duplicates)} записей -> {filename_no_duplicates}")
    print(f"   • С дубликатами: {len(df_with_duplicates)} записей -> {filename_with_duplicates}")

    # Выводим статистику
    print(f"\n📊 Статистика:")
    print(f"   • Всего собрано записей: {len(df)}")
    print(f"   • Уникальных записей: {len(df_no_duplicates)}")
    print(f"   • Дубликатов: {len(df) - len(df_no_duplicates)}")

    # Выводим топ-5 плит
    print("\n🏆 Топ-5 самых дорогих плит:")
    for i, (_, row) in enumerate(df_no_duplicates.head().iterrows(), 1):
        print(f"{i}. {row['Модель'][:70]}... - {row['Цена']:,.0f} руб.")

    # Сохраняем также в CSV для проверки
    df_no_duplicates.to_csv(f'{filename_base}_без_дубликатов_{timestamp}.csv', index=False, encoding='utf-8')
    print(f"💾 Также сохранено в CSV формате")


if __name__ == "__main__":
    print("🚀 Начинаем парсинг газовых плит...")
    print("📝 Данные будут сохраняться во временный файл при каждой прокрутке")

    gas_stoves_data = parse_gas_stoves()

    print(f"\n📊 Итоговое количество собранных записей: {len(gas_stoves_data)}")

    save_to_excel(gas_stoves_data)

    if gas_stoves_data:
        unique_count = len(pd.DataFrame(gas_stoves_data).drop_duplicates(subset=['Модель', 'Цена']))
        print(f"\n🎉 Успешно! Найдено {unique_count} уникальных газовых плит")
    else:
        print("\n❌ Не удалось получить данные")