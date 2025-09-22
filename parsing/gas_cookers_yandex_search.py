from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
import pandas as pd
import time
import re


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


def parse_gas_stoves():
    """Парсинг газовых плит через поиск"""
    driver = setup_driver()
    data = []

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

        # Прокручиваем страницу для загрузки товаров
        print("Прокручиваем страницу для загрузки товаров...")
        for i in range(3):
            driver.execute_script(f"window.scrollTo(0, {1500 * (i + 1)});")
            time.sleep(3)

        print("Ищем товары...")

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
                    products = found_products[:30]
                    break
            except:
                continue

        if not products:
            # Пробуем найти любые товары на странице
            print("Пробуем альтернативный поиск товаров...")
            products = driver.find_elements(By.CSS_SELECTOR, 'div, article, section')
            products = [p for p in products if p.get_attribute('data-zone-name') == 'snippet']
            if not products:
                print("❌ Не удалось найти товары. Сохраняем скриншот...")
                driver.save_screenshot('no_products.png')
                return data

        print(f"✅ Найдено {len(products)} товаров для обработки")

        for i, product in enumerate(products, 1):
            try:
                print(f"\n--- Обрабатываем товар {i} ---")

                # Прокручиваем к товару
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", product)
                time.sleep(1)

                # Получаем весь текст элемента
                product_text = product.text
                print(f"Текст товара: {product_text[:200]}...")

                # Поиск названия
                name = None
                name_selectors = [
                    'h3',
                    'a[href*="/product/"]',
                    '[data-zone-name="title"]',
                    '.n-snippet-card2__title',
                    '._3EX9a',
                    '.N9L7oc'  # Яндекс Маркет
                ]

                for selector in name_selectors:
                    try:
                        name_elem = product.find_element(By.CSS_SELECTOR, selector)
                        candidate_name = name_elem.text.strip()
                        if candidate_name and len(candidate_name) > 10:
                            name = candidate_name
                            print(f"Название найдено: {name[:60]}...")
                            break
                    except:
                        continue

                # Если не нашли по селекторам, ищем в тексте
                if not name and product_text:
                    lines = [line.strip() for line in product_text.split('\n') if line.strip()]
                    for line in lines:
                        if len(line) > 20 and any(word in line.lower() for word in
                                                  ['плита', 'газов', 'gorenje', 'bosch', 'electrolux', 'indesit',
                                                   'darina', 'гефест']):
                            name = line
                            print(f"Название из текста: {name[:60]}...")
                            break

                # Если все еще не нашли, берем первую длинную строку
                if not name and product_text:
                    lines = [line.strip() for line in product_text.split('\n') if len(line.strip()) > 20]
                    if lines:
                        name = lines[0]
                        print(f"Название из первой строки: {name[:60]}...")

                # Поиск цены
                price = None
                try:
                    # Ищем цену регулярным выражением (улучшенная версия)
                    price_pattern = r'(\d{1,3}(?:\s?\d{3})*(?:\s?\d{3})*)\s*[₽рруб]'
                    matches = re.findall(price_pattern, product_text, re.IGNORECASE)
                    if matches:
                        price = matches[0].replace(' ', '').replace(' ', '').replace(' ', '')
                        print(f"Цена найдена: {price}")
                    else:
                        # Пробуем селекторы цены
                        price_selectors = [
                            '[data-zone-name="price"]',
                            '.price',
                            '._1u3jP',
                            '.n-snippet-card2__price',
                            '.N9L7oc+div'  # цена после названия
                        ]
                        for selector in price_selectors:
                            try:
                                price_elem = product.find_element(By.CSS_SELECTOR, selector)
                                price_text = price_elem.text
                                price_match = re.search(price_pattern, price_text, re.IGNORECASE)
                                if price_match:
                                    price = price_match.group(1).replace(' ', '').replace(' ', '').replace(' ', '')
                                    print(f"Цена из селектора: {price}")
                                    break
                            except:
                                continue

                except Exception as e:
                    print(f"Ошибка поиска цены: {e}")

                # Сохраняем данные (упрощенная проверка)
                if name and price:
                    try:
                        # Преобразуем цену в число
                        price_num = int(price) if price.isdigit() else 0

                        data.append({
                            'Категория товара': 'Газовая плита',
                            'Модель': name,
                            'Цена': price_num
                        })
                        print(f"✅ Добавлен: {name[:50]}... - {price_num} руб.")
                    except Exception as e:
                        print(f"❌ Ошибка преобразования цены: {e}")
                else:
                    print(f"❌ Не хватает данных: name={name is not None}, price={price is not None}")

            except Exception as e:
                print(f"⚠️ Ошибка обработки товара {i}: {e}")
                continue

    except Exception as e:
        print(f"🚨 Критическая ошибка: {e}")
        driver.save_screenshot('error.png')

    finally:
        driver.quit()

    return data


def save_to_excel(data, filename='gas_stoves.xlsx'):
    """Сохраняет данные в Excel файл"""
    if data:
        # Создаем DataFrame
        df = pd.DataFrame(data)

        # Удаляем дубликаты
        df = df.drop_duplicates(subset=['Модель', 'Цена'])

        # Сортируем по цене
        df = df.sort_values('Цена', ascending=False)

        # Сохраняем в Excel
        df.to_excel(filename, index=False)
        print(f"\n💾 Сохранено {len(df)} записей в {filename}")

        # Выводим для проверки
        print("\n🏆 Топ-5 плит:")
        for i, (_, row) in enumerate(df.head().iterrows(), 1):
            print(f"{i}. {row['Модель'][:70]}... - {row['Цена']} руб.")

        # Сохраняем также в CSV для проверки
        df.to_csv('gas_stoves.csv', index=False, encoding='utf-8')
        print(f"💾 Также сохранено в gas_stoves.csv")

    else:
        print("📭 Нет данных для сохранения")


if __name__ == "__main__":
    print("🚀 Начинаем парсинг газовых плит...")

    gas_stoves_data = parse_gas_stoves()

    print(f"\n📊 Найдено товаров: {len(gas_stoves_data)}")

    save_to_excel(gas_stoves_data)

    if gas_stoves_data:
        print(f"\n🎉 Успешно! Найдено {len(gas_stoves_data)} газовых плит")
    else:
        print("\n❌ Не удалось получить данные")
