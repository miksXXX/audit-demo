import os
from fastapi import FastAPI, File, UploadFile
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

    if 'Ваша цена' in df.columns:
        df['profit'] = df['Ваша цена'] - df.get('Себестоимость', 0) - df.get('Логистика', 0) - (df['Ваша цена'] * 0.15)
        sku_col = 'Номер поставки'
    elif 'Наименование товара' in df.columns and 'К оплате продавцу' in df.columns:
        df['profit'] = df['К оплате продавцу'] - df.get('Себестоимость', 0) - df.get('Доставка', 0)
        sku_col = 'Артикул'
    else:
        return "<h3>Формат не поддерживается</h3>"

    loss_items = df[df['profit'] < 0]
    total_loss = abs(loss_items['profit'].sum())

    rows = ""
    for _, row in loss_items.head(10).iterrows():
        rows += f"<tr><td>{row.get(sku_col, '—')}</td><td>{row['profit']:.0f} ₽</td></tr>"

    return f"""
    <html>
      <body style="font-family: sans-serif; max-width: 700px; margin: 40px auto;">
        <h2>Результат анализа</h2>
        <p>Убыточных позиций: {len(loss_items)}</p>
        <p>Общий убыток: {total_loss:,.0f} ₽</p>
        <table border="1" style="margin-top: 20px; border-collapse: collapse;">
          <tr><th>SKU</th><th>Убыток (₽)</th></tr>
          {rows}
        </table>
        <p><a href="/">← Назад</a></p>
      </body>
    </html>
    """

# Запуск только при прямом вызове (для локального теста)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
