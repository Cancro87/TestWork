import gspread
from oauth2client.service_account import ServiceAccountCredentials

async def insert_into_google_sheets(row_values):
    # Настройка доступа к API Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('./gtablework.json', scope)
    client = gspread.authorize(creds)

    # Работа с таблицей
    sheet = client.open_by_key(f'14H5SF-VKFEB5XGsufx6cGrlji5ixAhdwToXphMZaT18').worksheet('Заказы')
    sheet.append_row(row_values)
    return True

