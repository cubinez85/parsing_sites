import pandas as pd
import re

file_path = "C:/Users/Oleg/PycharmProjects/data_analytic/parsing/Gefest_gas_cookers.xlsx"
data = pd.read_excel(file_path)
print(data)
df = data.copy()
print(df.info())


# Функция для извлечения кода модели
def extract_model_code(model_name):
    # Ищем паттерн: 4 цифры, тире, 2 цифры
    pattern = r'\b\d{4}-\d{2}\b'
    match = re.search(pattern, str(model_name))
    if match:
        return match.group()
    else:
        # Альтернативный паттерн для некоторых моделей
        pattern_alt = r'\b\d{3}-\d{2}\b'  # для моделей типа 700-02
        match_alt = re.search(pattern_alt, str(model_name))
        if match_alt:
            return match_alt.group()
        else:
            return None


# Применяем функцию к столбцу "Модель"
df['Код модели'] = df['Модель'].apply(extract_model_code)

# Проверяем результат
print("\nПосле заполнения кодов моделей:")
print(df.head(10))
print(f"\nКоличество заполненных кодов: {df['Код модели'].notna().sum()} из {len(df)}")
print(f"\nУникальные коды моделей: {df['Код модели'].unique()}")

# Если есть пропуски, можно попробовать альтернативные методы
if df['Код модели'].isna().any():
    print(f"\nПропущенные коды в строках: {df[df['Код модели'].isna()].index.tolist()}")


    # Дополнительная попытка найти коды
    def extract_model_code_advanced(model_name):
        # Ищем любую комбинацию цифр с тире
        patterns = [
            r'\b\d{4}-\d{2}\b',  # XXXX-XX
            r'\b\d{3}-\d{2}\b',  # XXX-XX
            r'\b\d{4}-\d{1}\b',  # XXXX-X
            r'\b\d{3}-\d{1}\b',  # XXX-X
        ]

        for pattern in patterns:
            match = re.search(pattern, str(model_name))
            if match:
                return match.group()
        return None


    # Применяем расширенную функцию к пропущенным значениям
    mask = df['Код модели'].isna()
    df.loc[mask, 'Код модели'] = df.loc[mask, 'Модель'].apply(extract_model_code_advanced)

# Финальная проверка
print(f"\nИтоговое количество заполненных кодов: {df['Код модели'].notna().sum()} из {len(df)}")

# Создаем сводные таблицы для сравнения цен по источникам
print("\n" + "=" * 80)
print("СВОДНЫЕ ТАБЛИЦЫ ДЛЯ СРАВНЕНИЯ ЦЕН ПО ИСТОЧНИКАМ")
print("=" * 80)

# 1. Сводная таблица: средние цены по моделям и источникам
pivot_mean = pd.pivot_table(df,
                            values='Цена',
                            index='Код модели',
                            columns='Источник',
                            aggfunc='mean',
                            fill_value=0).round(2)

print("\n1. СРЕДНИЕ ЦЕНЫ ПО МОДЕЛЯМ И ИСТОЧНИКАМ:")
print(pivot_mean)

# 2. Сводная таблица: минимальные цены по моделям и источникам
pivot_min = pd.pivot_table(df,
                           values='Цена',
                           index='Код модели',
                           columns='Источник',
                           aggfunc='min',
                           fill_value=0).round(2)

print("\n2. МИНИМАЛЬНЫЕ ЦЕНЫ ПО МОДЕЛЯМ И ИСТОЧНИКАМ:")
print(pivot_min)

# 3. Сводная таблица: максимальные цены по моделям и источникам
pivot_max = pd.pivot_table(df,
                           values='Цена',
                           index='Код модели',
                           columns='Источник',
                           aggfunc='max',
                           fill_value=0).round(2)

print("\n3. МАКСИМАЛЬНЫЕ ЦЕНЫ ПО МОДЕЛЯМ И ИСТОЧНИКАМ:")
print(pivot_max)

# 4. Сводная таблица: количество предложений по моделям и источникам
pivot_count = pd.pivot_table(df,
                             values='Цена',
                             index='Код модели',
                             columns='Источник',
                             aggfunc='count',
                             fill_value=0)

print("\n4. КОЛИЧЕСТВО ПРЕДЛОЖЕНИЙ ПО МОДЕЛЯМ И ИСТОЧНИКАМ:")
print(pivot_count)

# 5. Анализ разницы цен между источниками
if len(pivot_mean.columns) > 1:
    # Вычисляем разницу между максимальной и минимальной средней ценой для каждой модели
    price_range = pivot_mean.max(axis=1) - pivot_mean.min(axis=1)
    price_range_percent = (price_range / pivot_mean.min(axis=1) * 100).round(2)

    price_comparison = pd.DataFrame({
        'Мин_цена': pivot_mean.min(axis=1),
        'Макс_цена': pivot_mean.max(axis=1),
        'Разница_абс': price_range,
        'Разница_%': price_range_percent
    })

    print("\n5. АНАЛИЗ РАЗНИЦЫ ЦЕН МЕЖДУ ИСТОЧНИКАМИ:")
    print(price_comparison.sort_values('Разница_%', ascending=False))

# 6. Общая статистика по источникам
source_stats = df.groupby('Источник').agg({
    'Цена': ['count', 'mean', 'min', 'max'],
    'Код модели': 'nunique'
}).round(2)

source_stats.columns = ['Кол-во_предложений', 'Средняя_цена', 'Мин_цена', 'Макс_цена', 'Уникальных_моделей']
print("\n6. ОБЩАЯ СТАТИСТИКА ПО ИСТОЧНИКАМ:")
print(source_stats)

# Сохраняем все результаты в Excel файл
output_path = "C:/Users/Oleg/PycharmProjects/data_analytic/parsing/Gefest_gas_cookers_analysis.xlsx"

with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    # Основные данные
    df.to_excel(writer, sheet_name='Исходные_данные', index=False)

    # Сводные таблицы
    pivot_mean.to_excel(writer, sheet_name='Средние_цены_по_источникам')
    pivot_min.to_excel(writer, sheet_name='Минимальные_цены_по_источникам')
    pivot_max.to_excel(writer, sheet_name='Максимальные_цены_по_источникам')
    pivot_count.to_excel(writer, sheet_name='Количество_предложений')

    # Анализ разницы цен
    if len(pivot_mean.columns) > 1:
        price_comparison.to_excel(writer, sheet_name='Анализ_разницы_цен')

    # Общая статистика
    source_stats.to_excel(writer, sheet_name='Статистика_по_источникам')

    # Детализированная таблица для анализа
    detailed_analysis = df.groupby(['Код модели', 'Источник']).agg({
        'Цена': ['count', 'mean', 'min', 'max']
    }).round(2)
    detailed_analysis.columns = ['_'.join(col).strip() for col in detailed_analysis.columns.values]
    detailed_analysis.reset_index().to_excel(writer, sheet_name='Детальный_анализ', index=False)

print(f"\n" + "=" * 80)
print(f"Файл с анализом успешно сохранен: {output_path}")
print("=" * 80)
print("Содержимое файла:")
print("- 'Исходные_данные': данные с заполненными кодами моделей")
print("- 'Средние_цены_по_источникам': средние цены по моделям и источникам")
print("- 'Минимальные_цены_по_источникам': минимальные цены")
print("- 'Максимальные_цены_по_источникам': максимальные цены")
print("- 'Количество_предложений': количество предложений по каждому источнику")
print("- 'Анализ_разницы_цен': сравнение цен между источниками")
print("- 'Статистика_по_источникам': общая статистика по каждому источнику")
print("- 'Детальный_анализ': подробная статистика по моделям и источникам")

# Дополнительная информация
print(f"\nДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:")
print(f"Всего записей: {len(df)}")
print(f"Уникальных моделей: {df['Код модели'].nunique()}")
print(f"Источников данных: {df['Источник'].nunique()}")
print(f"Источники: {df['Источник'].unique().tolist()}")