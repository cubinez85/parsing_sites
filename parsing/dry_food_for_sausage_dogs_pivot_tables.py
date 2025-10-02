import pandas as pd
import time

file_path = "C:/Users/Oleg/PycharmProjects/data_analytic/parsing/food_for_sausge_dogs_all_markets.xlsx"
data = pd.read_excel(file_path)
print(data)
df = data.copy()
print(df.info())

# Создание сводных таблиц

# 1. Базовая статистика по ценам в каждом маркете
pivot_basic_stats = df.pivot_table(
    values='Цена',
    index='Источник',
    aggfunc=['count', 'mean', 'median', 'min', 'max', 'std']
).round(2)

# Переименование столбцов для лучшей читаемости
pivot_basic_stats.columns = ['Количество товаров', 'Средняя цена', 'Медианная цена',
                             'Минимальная цена', 'Максимальная цена', 'Стандартное отклонение']

# 2. Количество товаров по маркетам
pivot_count = df.pivot_table(
    values='Цена',
    index='Источник',
    aggfunc='count'
).rename(columns={'Цена': 'Количество товаров'})

# 3. Средние цены по маркетам
pivot_mean = df.pivot_table(
    values='Цена',
    index='Источник',
    aggfunc='mean'
).round(2).rename(columns={'Цена': 'Средняя цена'})

# 4. Медианные цены по маркетам
pivot_median = df.pivot_table(
    values='Цена',
    index='Источник',
    aggfunc='median'
).rename(columns={'Цена': 'Медианная цена'})

# 5. Минимальные и максимальные цены по маркетам
pivot_min_max = df.pivot_table(
    values='Цена',
    index='Источник',
    aggfunc=['min', 'max']
).round(2)
pivot_min_max.columns = ['Минимальная цена', 'Максимальная цена']

# 6. Стандартное отклонение цен (показатель разброса цен)
pivot_std = df.pivot_table(
    values='Цена',
    index='Источник',
    aggfunc='std'
).round(2).rename(columns={'Цена': 'Стандартное отклонение'})


# 7. Ценовые диапазоны по маркетам
def price_range_group(price):
    if price <= 300:
        return 'До 300 руб'
    elif price <= 500:
        return '301-500 руб'
    elif price <= 700:
        return '501-700 руб'
    else:
        return 'Свыше 700 руб'


df['Ценовая группа'] = df['Цена'].apply(price_range_group)

pivot_price_groups = df.pivot_table(
    values='Цена',
    index='Источник',
    columns='Ценовая группа',
    aggfunc='count',
    fill_value=0
).rename(columns={'Цена': 'Количество'})


# 8. Топ-5 самых дорогих товаров в каждом маркете
def get_top_expensive(df, n=5):
    result = {}
    for market in df['Источник'].unique():
        market_data = df[df['Источник'] == market].nlargest(n, 'Цена')[['Название товара', 'Цена']]
        result[market] = market_data
    return result


top_expensive = get_top_expensive(df, 5)


# 9. Топ-5 самых дешевых товаров в каждом маркете
def get_top_cheap(df, n=5):
    result = {}
    for market in df['Источник'].unique():
        market_data = df[df['Источник'] == market].nsmallest(n, 'Цена')[['Название товара', 'Цена']]
        result[market] = market_data
    return result


top_cheap = get_top_cheap(df, 5)

# Сохранение всех таблиц в Excel файл
output_file = "C:/Users/Oleg/PycharmProjects/data_analytic/parsing/analysis_food_prices.xlsx"

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Основные сводные таблицы
    pivot_basic_stats.to_excel(writer, sheet_name='Основная статистика')
    pivot_count.to_excel(writer, sheet_name='Количество товаров')
    pivot_mean.to_excel(writer, sheet_name='Средние цены')
    pivot_median.to_excel(writer, sheet_name='Медианные цены')
    pivot_min_max.to_excel(writer, sheet_name='Мин и Макс цены')
    pivot_std.to_excel(writer, sheet_name='Стандартное отклонение')
    pivot_price_groups.to_excel(writer, sheet_name='Ценовые группы')

    # Топ товары по маркетам
    start_row = 0
    for market, data in top_expensive.items():
        data.to_excel(writer, sheet_name='Топ дорогие', startrow=start_row)
        writer.sheets['Топ дорогие'].cell(row=start_row + 1, column=1, value=f"Маркет: {market}")
        start_row += len(data) + 3

    start_row = 0
    for market, data in top_cheap.items():
        data.to_excel(writer, sheet_name='Топ дешевые', startrow=start_row)
        writer.sheets['Топ дешевые'].cell(row=start_row + 1, column=1, value=f"Маркет: {market}")
        start_row += len(data) + 3

    # Исходные данные
    df.to_excel(writer, sheet_name='Исходные данные', index=False)

print(f"Анализ сохранен в файл: {output_file}")
print("Созданы следующие листы:")
print("- Основная статистика")
print("- Количество товаров")
print("- Средние цены")
print("- Медианные цены")
print("- Мин и Макс цены")
print("- Стандартное отклонение")
print("- Ценовые группы")
print("- Топ дорогие товары")
print("- Топ дешевые товары")
print("- Исходные данные")

# Дополнительный вывод в консоль для быстрого просмотра
print("\n" + "=" * 50)
print("ОСНОВНАЯ СТАТИСТИКА ПО МАРКЕТАМ:")
print("=" * 50)
print(pivot_basic_stats)

print("\n" + "=" * 50)
print("РАСПРЕДЕЛЕНИЕ ПО ЦЕНОВЫМ ГРУППАМ:")
print("=" * 50)
print(pivot_price_groups)