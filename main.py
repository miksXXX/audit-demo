from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
import pandas as pd
import io

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
      <body style="font-family: sans-serif; max-width: 600px; margin: 40px auto;">
        <h2>Анализ убыточных товаров</h2>
        <p>Загрузите Excel-отчёт Wildberries или Ozon:</p>
        <form action="/analyze" method="post" enctype="multipart/form-data">
          <input type="file" name="file" accept=".xlsx,.xls" required>
          <button type="submit">Анализировать</button>
        </form>
      </body>
    </html>
    """

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(file: UploadFile = File(...)):
    content = await file.read()
    df = pd.read_excel(io.BytesIO(content))

    # === Wildberries: колонки из отчёта "Продажи" ===
    if 'Ваша цена' in df.columns:
        df['profit'] = (
            df['Ваша цена'] 
            - df.get('Себестоимость', 0) 
            - df.get('Логистика', 0) 
            - df.get('К перечислению продавцу', 0) * 0.05  # пример комиссии
        )
        sku_col = 'Номер поставки'
        platform = 'Wildberries'

    # === Ozon: колонки из финансового отчёта ===
    elif 'Наименование товара' in df.columns and 'К оплате продавцу' in df.columns:
        df['profit'] = (
            df['К оплате продавцу']
            - df.get('Себестоимость', 0)
            - df.get('Доставка', 0)
        )
        sku_col = 'Артикул'
        platform = 'Ozon'

    else:
        return "<h3>Не удалось распознать формат отчёта.</h3><p>Поддерживаются: отчёты Wildberries («Продажи») и Ozon (финансовый отчёт).</p>"

    # Находим убыточные позиции
    loss_items = df[df['profit'] < 0]
    total_loss = abs(loss_items['profit'].sum())

    # Генерируем HTML-отчёт
    rows = ""
    for _, row in loss_items.head(10).iterrows():
        rows += f"<tr><td>{row.get(sku_col, '—')}</td><td>{row['profit']:.0f} ₽</td></tr>"

    return f"""
    <html>
      <body style="font-family: sans-serif; max-width: 700px; margin: 40px auto;">
        <h2>Результат анализа ({platform})</h2>
        <p>⚠️ Обнаружено <b>{len(loss_items)}</b> убыточных позиций.</p>
        <p>Общий убыток: <b>{total_loss:,.0f} ₽</b></p>
        
        <table border="1" style="margin-top: 20px; border-collapse: collapse;">
          <tr><th>SKU / Артикул</th><th>Убыток (₽)</th></tr>
          {rows}
        </table>

        <p style="margin-top: 30px;">
          <a href="/" style="color: #e74c3c; text-decoration: none;">← Загрузить другой отчёт</a>
        </p>
        <p style="margin-top: 20px; font-size: 0.9em; color: #888;">
          Данные не сохраняются. Анализ происходит в браузере.
        </p>
      </body>
    </html>
    """
