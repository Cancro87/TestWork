from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, SuccessfulPayment, InputMediaPhoto, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import json
from datetime import datetime, timedelta
import asyncio
import os
from dotenv import load_dotenv
import asyncpg
import pytz
import traceback
from gtable import insert_into_google_sheets as tablein

#Переменные
load_dotenv()

bot = Bot(token=os.getenv('bottoken'))
dp = Dispatcher()

#Глобальные словари и списки хранения данных, чтоб не гразуить лишний раз бд
sendmsg = {'text': None, 'media': None, "keyboard": None}
categs = []
subcategs = []
namesshop = []
basketchunk = []
faqdict = []

#Контроль состояний в боте для получения сообщений
class StateChat(StatesGroup):
    curstatus = State()

#Клавиатура для админов в группе
adminkeyboard = InlineKeyboardBuilder()
adminkeyboard.button(text=f"Установить канал", callback_data=f'admin_setchanel')
adminkeyboard.button(text=f"Сделать рассылку", callback_data=f'admin_sendall')
adminkeyboard.button(text=f"Удалить последнюю", callback_data=f'admin_deletelastsend')
adminkeyboard.adjust(1, 1)

#Клавиатура отмены выбора
cancelkeyboard = InlineKeyboardBuilder()
cancelkeyboard.button(text='Отмена', callback_data=f'cancel')

#Клавиатура для пользователей
buttoncatalog = types.KeyboardButton(text="Каталог")
buttonbasket = types.KeyboardButton(text="Корзина")
buttonfaq = types.KeyboardButton(text="FAQ")
keymoarduser = types.ReplyKeyboardMarkup(keyboard=[[buttoncatalog,buttonbasket],[buttonfaq]],resize_keyboard=True)

#Асинхронная запись и изменение таблиц
async def insertdb(req, islog = False):
    try:
        if islog == True:
            req = [[f"""INSERT INTO logs (key,typedata,values) VALUES ($1,$2,$3)""",['aiogram',req[0],req[1]]]]
        connection = await asyncpg.connect(user=os.getenv('POSTGRES_USER'),
                                   password=os.getenv('POSTGRES_PASSWORD'),
                                   database=os.getenv('POSTGRES_DB'),
                                   host=os.getenv('POSTGRES_HOST'),
                                   port=os.getenv('POSTGRES_PORT'))
        for each in req:
            try:
                if islog == True:
                    await connection.execute(each[0], *each[1])
                else:
                    await connection.execute(each)
            except:
                if islog == False:
                    await connection.execute(f"INSERT INTO logs (key,typedata,values) VALUES ($1,$2,$3)", *['aiogram','ERROR',{str(traceback.format_exc())}])
                else:
                    await bot.send_message(os.getenv('chanelid'), f"ERROR in insertdb\n{traceback.format_exc()}")
    except:
        await bot.send_message(os.getenv('chanelid'), f"ERROR in insertdb\n{traceback.format_exc()}")

#Асинхронное получение данных из БД
async def getfromdb(req):
    try:
        connection = await asyncpg.connect(user=os.getenv('POSTGRES_USER'),
                                   password=os.getenv('POSTGRES_PASSWORD'),
                                   database=os.getenv('POSTGRES_DB'),
                                   host=os.getenv('POSTGRES_HOST'),
                                   port=os.getenv('POSTGRES_PORT'))
        values = await connection.fetch(req)
        await connection.close()
        result_list = [dict(record) for record in values]
        return result_list
    except:
        await insertdb(['ERROR',f"{traceback.format_exc()}"],True)

#Функция выполняющаяся при запуске, для проверки существования нужных папок и параметров в таблице настроек бота
async def startup():
    speckeys = ['subchanel','starttext','forsubscription','subgroup'] #обязательные параметры в таблице

    #Папка логирования
    #if os.path.exists(f"./LOGS") == False:
        #os.mkdir(f"./LOGS")

    #Проверка обязательных параметрво и их добавление
    settingsdata = await getfromdb(f"SELECT key,values FROM settings")
    dbkeys = [str(key['key']) for key in settingsdata]
    commands = []
    for eachkey in speckeys:
        if eachkey not in dbkeys:
            commands.append(f"INSERT INTO settings (key) VALUES ('{eachkey}')")

    await insertdb(commands) #Добавление в базу
    await bot.send_message(os.getenv('chanelid'),f"RESTARTED")


#Проверка подписок на канал и группу
async def chanel_sub_check(userid):
    #Получаем id обязательных к подписке
    data = await getfromdb(f"SELECT values FROM settings WHERE key = 'subchanel'")
    chanelid = data[0]['values']
    data = await getfromdb(f"SELECT values FROM settings WHERE key = 'subgroup'")
    groupid = data[0]['values']
    if chanelid and groupid:
        try:
            #Проверка подписки
            statuschanel = await bot.get_chat_member(chanelid, userid)
            statusgroup = await bot.get_chat_member(groupid, userid)
            statuschanel = ('LEFT' in str(statuschanel.status))
            statusgroup = ('LEFT' in str(statusgroup.status))

            if statuschanel == True or statusgroup == True:
                kb = InlineKeyboardBuilder()
                try:
                    linkdata = await bot.get_chat(chanelid)
                    link = linkdata.invite_link
                    if link:
                        kb.button(text=f"Канал", url=link)
                    else:
                        # Информирование в группу админов
                        await bot.send_message(os.getenv('chanelid'),'Не удалось получить ссылку к каналу')
                except:
                    # Информирование в группу админов
                    await bot.send_message(os.getenv('chanelid'), 'Не удалось получить ссылку к каналу')
                try:
                    linkdata = await bot.get_chat(groupid)
                    link = linkdata.invite_link
                    if link:
                        kb.button(text=f"Группа", url=link)
                    else:
                        # Информирование в группу админов
                        await bot.send_message(os.getenv('chanelid'),'Не удалось получить ссылку к группе')
                except:
                    # Информирование в группу админов
                    await bot.send_message(os.getenv('chanelid'), 'Не удалось получить ссылку к группе')
                kb.button(text=f"Проверить", callback_data=f"checksub")
                kb.adjust(1,1)
                data = await getfromdb(f"SELECT values FROM settings WHERE key = 'forsubscription'")
                textsend = data[0]['values']
                if textsend is None:
                    textsend = 'Для работы с ботом подпишитесь на группу и канал\nПосле подписки нажмите кнопку проверки'
                await bot.send_message(userid,textsend,reply_markup=kb.as_markup())
                return False
            else:
                return True
        except:
            logtext = f"chanel_sub_check\n{userid}\n{traceback.format_exc()}"
            await insertdb(['ERROR', f"{logtext}"], True)
            return True
    else:
        return True


#Проверка бота в админах перед добавлением канала или группы
async def is_bot_admin(channel_id):
    try:
        chat_administrators = await bot.get_chat(channel_id)
        if chat_administrators.invite_link:
                return chat_administrators.invite_link
        return None
    except:
        logtext = f"is_bot_admin\n{channel_id}\n{traceback.format_exc()}"
        await insertdb(['ERROR', f"{logtext}"], True)
        return None

#Имитация ошибки
@dp.message(Command('er'))
async def geter(message:Message):
    if str(message.chat.id) == os.getenv('chanelid'):
        try:
            print('HERE')
            raise Exception('TUTU')
        except:
            print(traceback.format_exc())
            await insertdb(['ERROR', f"{traceback.format_exc()}"], True)

@dp.message(Command('start'))
async def start(message:Message):
    try:
        #Поиск пользователя в базе
        data = await getfromdb(f"SELECT id FROM users WHERE user_id = {message.from_user.id}")
        if len(data) > 0:
            #Обновление онлайна в базе
            await insertdb([f"UPDATE users SET lastonline = '{datetime.now(tz=pytz.timezone('Europe/Moscow'))}' WHERE id = {data[0]['id']}"])
        else:
            #Добавление нового
            await insertdb([f"INSERT INTO users (user_id,username,lastonline) VALUES ({message.from_user.id},'https://t.me/{message.from_user.username}','{datetime.now(tz=pytz.timezone('Europe/Moscow'))}')"])

        #Получение стартового текста и проверка подписок
        data = await getfromdb(f"SELECT values FROM settings WHERE key = 'starttext'")
        if data[0]['values']:
            await message.answer(f"{data[0]['values']}")
        check = await chanel_sub_check(message.from_user.id)
        if check == True:
            await message.answer(f"Меню",reply_markup=keymoarduser)
    except:
        logtext = f"{traceback.format_exc()}"
        await insertdb(['ERROR', f"{logtext}"], True)

#Узнать свой id и id группы
@dp.message(Command('getid'))
async def getchatid(message:Message):
    await message.answer(f"Chat id: {message.chat.id}\nPersonal id: {message.from_user.id}")

#Установить группу в которой данная команда обязательным к вступлению
@dp.message(Command('setgroup'))
async def setgroup(message:Message):
    #Проверка, что сработало только на администратора бота (редактируется в Django)
    try:
        data = await getfromdb(f"SELECT user_id FROM tgadmins")
        adminslist = [int(userid['user_id']) for userid in data]
        if message.from_user.id in adminslist:
            link = await is_bot_admin(message.chat.id)
            if link:
                await insertdb([f"UPDATE settings SET values = '{message.chat.id}' WHERE key = 'subgroup'"])
                await message.answer(f'Группа добавлена для обязательного вступления')
                await bot.send_message(os.getenv('chanelid'), f"Беседа {link} добавлена обязятельной к вступлению")
            else:
                await message.answer(f"У бота нет разрешения работать с ссылкой")
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)


#Доступ админа только в группе
@dp.message(Command('admin'))
async def adminwork(message:Message):
    try:
        if str(message.chat.id) == os.getenv('chanelid'):
            data = await getfromdb(f"SELECT user_id FROM tgadmins")
            adminslist = [int(userid['user_id']) for userid in data]
            if message.from_user.id in adminslist:
                await message.answer(f"Выберите действие",reply_markup=adminkeyboard.as_markup())
            else:
                await message.answer(f"Нет доступа\n@{message.from_user.username} - {message.from_user.first_name}")
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)


#Функция генерации клавиатуры доступных категорий из базы
async def kbforcateg():
    global categs
    try:
        categs = [] #Запись в память категорий, чтоб снизить нагрузку на БД
        chunk_size = 5 #Кол-во категорий за один раз
        data = await getfromdb(f"SELECT category FROM shop WHERE onsell = true AND count > 0")
        categlist = []
        for eachcateg in data:
            if eachcateg['category'] not in categlist:
                categlist.append(eachcateg['category']) #Записываем подходящие категории
        #Генерация клавиатуры для навигации
        keyboard = InlineKeyboardBuilder()
        if len(categlist) > chunk_size:
            categs = [categlist[i:i + chunk_size] for i in range(0, len(categlist), chunk_size)]
        else:
            categs = [categlist.copy()]
        base = 1
        if len(categs) > 1:
            keyboard.button(text='❌', callback_data=f"not_prev")
            keyboard.button(text='➡️', callback_data=f"category_next_1")
            base = 2
        for each in categs[0]:
            keyboard.button(text=each, callback_data=f"opencateg_{each}")
        keyboard.adjust(base, 1)
        return keyboard
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)

#Генерация клавиатуры навигации для подкатегорий
async def subcateg(data):
    global subcategs
    try:
        subcategs = [] #Запись в память подкатегорий, чтоб снизить нагрузку на БД
        chunk_size = 5 #Кол-во подкатегорий за один раз
        #Получение и разделение на блоки подходящих категорий
        datadb = await getfromdb(f"SELECT subcategory FROM shop WHERE onsell = true AND category = '{data}' AND count > 0")
        subcateglist = []
        for eachsubcateg in datadb:
            if eachsubcateg['subcategory'] not in subcateglist:
                subcateglist.append(eachsubcateg['subcategory'])
        if len(subcateglist) > chunk_size:
            subcategs = [subcateglist[i:i + chunk_size] for i in range(0, len(subcateglist), chunk_size)]
        else:
            subcategs = [subcateglist.copy()]
        #Генерация клавиатуры для навигации
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text='❌', callback_data=f"not_prev")
        keyboard.button(text='Категории', callback_data=f"opencateg_category")
        if len(subcategs) > 1:
            keyboard.button(text='➡️', callback_data=f"subcateg_next_1")
        else:
            keyboard.button(text='❌', callback_data=f"not_next")
        for eachsub in subcategs[0]:
            keyboard.button(text=eachsub, callback_data=f"opensubcateg_{eachsub}")
        keyboard.adjust(3, 1)
        return keyboard
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)

#Функция получения нужного товара и негерации клавиатуры
async def getshop(data,toget):
    #toget индекс нужного товара
    #data название подкатегории из которой он должен быть
    try:
        datadb = await getfromdb(f"SELECT id,name,description,photoid,count,price FROM shop WHERE onsell = true AND subcategory = '{data}' AND count > 0")
        list = datadb.copy()
        keyboard = InlineKeyboardBuilder()
        if toget == 0 or toget >= len(list):
            keyboard.button(text = '❌',callback_data='not_prev')
        else:
            keyboard.button(text='⬅️', callback_data=f'getshop_card_{toget-1}_{data}')
        keyboard.button(text='Категории', callback_data=f"getshop_categ")
        if toget+1 < len(list):
            keyboard.button(text='➡️', callback_data=f'getshop_card_{toget + 1}_{data}')
        else:
            keyboard.button(text='❌', callback_data='not_next')
        if toget < len(list):
            keyboard.button(text='В корзину',callback_data=f"addbusket_{list[toget]['id']}")
        else:
            keyboard.button(text='Товар не найден', callback_data=f"getshop_categ")
        keyboard.adjust(3,1)
        if toget < len(list):
            return keyboard,list[toget] #Возвращаем клавиатуру и данные для отображения нужного товара
        else:
            return keyboard,None
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)

#Генерация клавиатуры для корзины
async def kbforbasket(userid, index = 0):
    #userid - пользователь
    #index - индекс нужного элемента в корзине
    global basketchunk
    try:
        basketchunk = []
        datadb = await getfromdb(f"SELECT id, product_id, count FROM basket WHERE user_id = {userid}") #Корзина нужного пользователя

        if len(datadb) > 0:
            list = datadb.copy()

            #Проверка на наличие нужного кол-ва и исключение ошибок при оформлении
            for each in list:
                datadbchecksum = await getfromdb(f"SELECT count, name, photoid, price FROM shop WHERE id = {each['product_id']} AND onsell = true AND count > 0")
                if len(datadbchecksum) > 0:
                    if datadbchecksum[0]['count'] >= each['count']:
                        toadd = each.copy()
                        for each in datadbchecksum[0]:
                            if each != 'count':
                                toadd[each] = datadbchecksum[0][each]
                        basketchunk.append(toadd)
                    else:
                        # Удаление из корзины если в наличии кол-ва меньше
                        await insertdb([f"DELETE FROM basket WHERE id = {each['id']}"])
                else:
                    # Удаление из корзины если товар сняли с продажи
                    await insertdb([f"DELETE FROM basket WHERE id = {each['id']}"])

            if index < len(basketchunk):
                #Генерация клавиатуры навигации
                kb = InlineKeyboardBuilder()
                if index == 0:
                    kb.button(text=f"❌",callback_data='not_prev')
                else:
                    kb.button(text=f"⬅️", callback_data=f'bask_get_{index-1}')
                kb.button(text='К оплате',callback_data='bask_pay')
                if len(basketchunk) > 1 and index+1 < len(basketchunk):
                    kb.button(text=f"➡️", callback_data=f'bask_get_{index+1}')
                else:
                    kb.button(text=f"❌", callback_data='not_next')
                kb.button(text=f"Удалить из корзины",callback_data=f"bask_remove_{basketchunk[index]['id']}")
                kb.button(text='Очистить корзину', callback_data='bask_clear')
                kb.adjust(3,1)
                return kb,basketchunk[index] #Клавиатура и данные о нужном товаре
            else:
                #Клавиатура при возникновении ошибок при получении не первого элемента
                kb = InlineKeyboardBuilder()
                kb.button(text=f"❌", callback_data='not_prev')
                kb.button(text=f"❌", callback_data='not_next')
                kb.button(text=f"Ошибка", callback_data=f"bask_get_0")
                kb.adjust(2, 1)
                return kb, None
        else:
            return None, None
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)

#Создание и выставление счета на оплату
async def genforbuy (userid,state: FSMContext):
    listbuy = [] #Список товара к покупке
    payl = {} #Данные для генерации информации о товаре для Google Sheets
    try:
        databd = await getfromdb(f"SELECT id,product_id, count FROM basket WHERE user_id = {userid}")
        for eachproduct in databd:
            #Проверка каждого товара из корзины к возможности для покупке
            productdata = await getfromdb(f"SELECT count,price,name FROM shop WHERE id = {eachproduct['product_id']} AND onsell = true AND count > 0")
            if len(productdata) == 1:
                if eachproduct['count'] <= productdata[0]['count']:
                    #Крайний срок для оплаты
                    timepay = datetime.now(tz=pytz.timezone('Europe/Moscow')) + timedelta(minutes=15)
                    #Изменение кол-ва товара (резервирование) и обновление срока для оплаты
                    await insertdb([f"UPDATE shop SET count = {productdata[0]['count']-eachproduct['count']} WHERE id = {eachproduct['product_id']}",
                                    f"UPDATE basket SET topay = '{timepay}' WHERE id = {eachproduct['id']}"])
                    #Цена за данный товар
                    topay = eachproduct['count']*productdata[0]['price']*100
                    #Данные google sheet
                    payl[f"{productdata[0]['name']}"] = {'count':eachproduct['count'],'totalsum':topay}
                    #Добавление товара к оплате
                    listbuy.append(LabeledPrice(label=f"{productdata[0]['name']} - {eachproduct['count']}", amount=topay))
                else:
                    await insertdb([f"DELETE FROM basket WHERE id = {eachproduct['id']}"]) #Недостаточное кол-во
            else:
                await insertdb([f"DELETE FROM basket WHERE id = {eachproduct['id']}"]) #невозможность корректно обработать

        #Адрес доставки
        useradres = await getfromdb(f"SELECT shipp_adress FROM users WHERE user_id = {userid}")
        desc = f"Адрес доставки\n{useradres[0]['shipp_adress']}"
        kbreturn = InlineKeyboardBuilder()
        kbreturn.button(text=f"Оплатить",pay=True)
        kbreturn.button(text='Отменить',callback_data=f'cancel')
        kbreturn.adjust(1,1)
        cancellmsg = await bot.send_invoice(userid,
                               title='Наш магазин',
                               description= desc,
                               payload=json.dumps(payl),
                               provider_token=os.getenv('sbertoken'),
                               currency='rub',
                               prices=listbuy,
                               need_name=True,
                               need_phone_number=True,
                               protect_content=True,
                               request_timeout=30,
                               reply_markup = kbreturn.as_markup())

        #Установка сосоятония для удаления клавиатуры после оплаты и снятия резерва с товара при отмене
        await state.set_state(StateChat.curstatus)
        await state.update_data(curstatus=f'getmoney_{cancellmsg.message_id}')
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)


#Клавиатура вопросов и ответов на них
async def kbforfaq(start = True, index = 0):
    global faqdict
    chunk_size = 2
    togive = ['Список вопросов'] #Список вопросов в нужном чанке
    try:
        if start == True:
            faqdict = []
            data = await getfromdb(f"SELECT quest,answer FROM faq")
            for each in data:
                faqdict.append({'q':each['quest'],'a':each['answer']})
            #Разделение вопросов на части
            if len(faqdict) > chunk_size:
                subcategs = [faqdict[i:i + chunk_size] for i in range(0, len(faqdict), chunk_size)]
            else:
                subcategs = [faqdict.copy()]
            faqdict = subcategs.copy()
        #Клавиатура с вопросами
        kb = InlineKeyboardBuilder()
        if index == 0 or len(faqdict) == 1:
            kb.button(text = '❌',callback_data='not_prev')
        else:
            kb.button(text='⬅️', callback_data=f'quest_getlist_{index-1}')
        kb.button(text='ЧАТ', callback_data=f'quest_openchat')
        if index+1 < len(faqdict):
            kb.button(text='➡️', callback_data=f'quest_getlist_{index + 1}')
        else:
            kb.button(text='❌', callback_data='not_next')
        for eachkey in faqdict[index]:
            name = faqdict[index].index(eachkey) + 1
            togive.append(f"{name} - {eachkey['q']}")
            kb.button(text=f"{name}", callback_data=f"quest_get_{index}_{faqdict[index].index(eachkey)}")
        kb.adjust(3)
        return kb,togive
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)


#Реакция на кнопку КАТАЛОГ
@dp.message(F.text == buttoncatalog.text)
async def catalogfunnc(message:Message):
    try:
        keyboard = await kbforcateg() #Получение клавиатуры для навигации
        await message.answer(f"Выберите категорию",reply_markup=keyboard.as_markup())
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)

#Реакция на кнопку КОРЗИНЫ
@dp.message(F.text == buttonbasket.text)
async def basketfunnc(message:Message):
    try:
        keyboard,data = await kbforbasket(message.from_user.id) #Генерация клавиатуры и данных на первый элемент
        if data:
            await message.answer_photo(data['photoid'],caption=f"{data['name']}\nЦена: {data['price']}\nВ корзине: {data['count']}",reply_markup=keyboard.as_markup())
        else:
            await message.answer(f"Ваша корзина пуста")
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)

#Реакция на кнопку FAQ
@dp.message(F.text == buttonfaq.text)
async def faqfunnc(message:Message):
    try:
        keyboard, data = await kbforfaq()  # Генерация клавиатуры и данных на первый элемент
        if len(data) > 0:
            await message.answer('\n'.join(data),reply_markup=keyboard.as_markup())
        else:
            await message.answer(f"Вопросов пока нет")
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)

#Ответ готовности продать товар серверу Telegram
@dp.pre_checkout_query(lambda q: True)
async def payproc(pre_check: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_check.id, ok= True)

#Взаимодействия с inline кнопками
@dp.callback_query()
async def callback(callback:CallbackQuery, state: FSMContext):
    global sendmsg, categs, subcategs, namesshop, faqdict
    try:
        if 'cancel' == callback.data:
            #Обработка кнопки Отмена
            curstate = await state.get_data()
            if 'curstatus' in curstate:
                if "basketadd_" in curstate['curstatus']:
                    # Отмена при вводе кол-во товара который уже был в корзине
                    databtn = str(curstate['curstatus']).split('_')
                    old = databtn[3]
                    id = databtn[1]
                    if int(old) != 0:
                        await insertdb([f"INSERT INTO basket (user_id,product_id,count) VALUES ({callback.from_user.id},{id},{int(old)})"])
                elif 'getmoney_' in curstate['curstatus']:
                    #Отмена при оплате
                    datatoback = await getfromdb(f"SELECT product_id,count FROM basket WHERE user_id = {callback.from_user.id} AND topay is not Null")
                    sqlreq = []
                    for eachshop in datatoback:
                        #Отмена резервирования на товар
                        indb = await getfromdb(f"SELECT count FROM shop WHERE id = {eachshop['product_id']}")
                        newwal = int(eachshop['count'] + indb[0]['count'])
                        sqlreq.append(f"UPDATE shop SET count = {newwal} WHERE id = {eachshop['product_id']}")
                    #Снятие срока оплаты на товар
                    sqlreq.append(
                        f"UPDATE basket SET topay = Null WHERE user_id = {callback.from_user.id} AND topay is not Null")
                    await insertdb(sqlreq)

            await state.clear()
            for each in sendmsg: #Очистка словаря с данными для рассылки
                sendmsg[each] = None
            await callback.message.answer(f'Отменено')
            await callback.message.edit_reply_markup(None)
        elif 'quest' in callback.data:
            #Обработка кнопок вопросов
            try:
                data = callback.data.split('_')
                if data[1] == 'getlist':
                    #Кнопки генерации вопросов
                    keyboard, data = await kbforfaq(False,int(data[2]))  # Генерация клавиатуры и данных на первый элемент
                    if len(data) > 0:
                        await callback.message.edit_text(text='\n'.join(data),reply_markup=keyboard.as_markup())
                    else:
                        await callback.message.edit_text(text=f"Вопросов пока нет",reply_markup=None)
                elif data[1] == 'get':
                    # Кнопки получения ответов
                    try:
                        await callback.message.answer(text=f"Вопрос:\n{faqdict[int(data[2])][int(data[3])]['q']}\n\nОтвет:\n{faqdict[int(data[2])][int(data[3])]['a']}")
                    except:
                        await callback.message.edit_reply_markup(None)
                elif data[1] == 'openchat':
                    #Кнопка перехода в чат
                    await callback.message.answer(f"ПОКА НЕ РЕАЛИЗОВАНО")
            except:
                await insertdb(['ERROR', f"{traceback.format_exc()}"], True)
        elif 'bask' in callback.data:
            #Обработка кнопок корзины
            try:
                data = callback.data.split('_')
                if data[1] == 'get':
                    #Получение элемента корзины
                    keyboard, datadb = await kbforbasket(callback.from_user.id,int(data[2]))
                    print(datadb)
                    if datadb:
                        await callback.message.edit_media(InputMediaPhoto(media=datadb['photoid']))
                        await callback.message.edit_caption(caption=f"{datadb['name']}\nЦена: {datadb['price']}\nВ корзине: {datadb['count']}",
                                                            reply_markup=keyboard.as_markup())
                    else:
                        await callback.message.edit_caption(caption=f"Ваша корзина пуста", reply_markup=None)
                elif data[1] == 'pay':
                    #Запрос на оплату
                    await callback.message.edit_reply_markup(None)
                    await state.set_state(StateChat.curstatus)
                    await state.update_data(curstatus=f'getshippadress')
                    await callback.message.answer(f"Напишите мне адрес доставки заказа",reply_markup=cancelkeyboard.as_markup())
                elif data[1] == 'remove':
                    # Запрос на удаление из корзины
                    await insertdb([f"DELETE FROM basket WHERE id = {int(data[2])}"])
                    keyboard, datadb = await kbforbasket(callback.from_user.id)
                    if datadb:
                        await callback.message.edit_media(InputMediaPhoto(media=datadb['photoid']))
                        await callback.message.edit_caption(caption=f"{datadb['name']}\nЦена: {datadb['price']}\nВ корзине: {datadb['count']}",reply_markup=keyboard.as_markup())
                    else:
                        await callback.message.edit_caption(caption=f"Ваша корзина пуста",reply_markup=None)
                elif data[1] == 'clear':
                    # Запрос на очистку
                    await callback.message.edit_reply_markup(None)
                    await insertdb([f"DELETE FROM basket WHERE user_id = {callback.from_user.id}"])
                    await callback.message.answer(f"Корзина очищена")
            except:
                await insertdb(['ERROR', f"{traceback.format_exc()}"], True)
        elif 'addbusket' in callback.data:
            #Добавление товаров в корзину
            await state.clear()
            try:
                datakb = callback.data.split('_')
                datadb = await getfromdb(f"SELECT count FROM shop WHERE id = {int(datakb[1])} AND onsell = true AND count > 0")
                if len(datadb) > 0:
                    await state.set_state(StateChat.curstatus)
                    datacheckuser = await getfromdb(f"SELECT count,id FROM basket WHERE user_id = {callback.from_user.id} AND product_id = {datakb[1]}")
                    # Проверка на наличие уже товара в корзине
                    if len(datacheckuser) == 0:
                        await state.update_data(curstatus=f"basketadd_{datakb[1]}_{datadb[0]['count']}_0")
                        await callback.message.answer(f"Отправь кол-во товара",reply_markup=cancelkeyboard.as_markup())
                    else:
                        await state.update_data(curstatus=f"basketadd_{datakb[1]}_{datadb[0]['count']}_{datacheckuser[0]['count']}")
                        await insertdb([f"DELETE FROM basket WHERE id = {datacheckuser[0]['id']}"])
                        await callback.message.answer(f"Товар уже был в корзине в кол-ве {datacheckuser[0]['count']}\nОтправь необходимое общее кол-во товара",reply_markup=cancelkeyboard.as_markup())
                else:
                    await callback.answer(f"К сожалению товар закончился")
            except:
                await insertdb(['ERROR', f"{traceback.format_exc()}"], True)
        elif 'getshop_' in callback.data:
            #Клавиатура под карточками товара
            try:
                datakb = callback.data.split('_')
                if datakb[1] == 'categ':
                    #Выход в категории
                    keyboard = await kbforcateg()
                    await callback.message.edit_reply_markup(None)
                    await callback.message.answer(text='Выберите категорию', reply_markup=keyboard.as_markup())
                elif datakb[1] == 'card':
                    #Получение нужной карточки
                    keyboard, data = await getshop(datakb[3], int(datakb[2]))
                    if data:
                        await callback.message.edit_media(InputMediaPhoto(media=data['photoid']))
                        await callback.message.edit_caption(caption=f"{data['name']}\nЦена: {data['price']}\nВ наличии: {data['count']}\n\n{data['description']}",reply_markup=keyboard.as_markup())
                    else:
                        await callback.message.edit_reply_markup(reply_markup=keyboard.as_markup())
            except:
                await insertdb(['ERROR', f"{traceback.format_exc()}"], True)
        elif 'opensubcateg' in callback.data:
            #Клавиатура открытия подкатегорий
            try:
                data = callback.data.split('_')[1]
                if data == 'category':
                    #Выйти в категории
                    keyboard = await kbforcateg()
                    await callback.message.edit_text(text='Выберите категорию', reply_markup=keyboard.as_markup())
                else:
                    #Получить товар подкатегории
                    keyboard, data = await getshop(data, 0)
                    await callback.message.edit_reply_markup(None)
                    if data:
                        await callback.message.answer_photo(photo=data['photoid'],caption=f"{data['name']}\nЦена: {data['price']}\nВ наличии: {data['count']}\n\n{data['description']}",reply_markup=keyboard.as_markup())
                    #await callback.message.edit_text(text='Выберите товар',reply_markup=keyboard.as_markup())
            except:
                await insertdb(['ERROR', f"{traceback.format_exc()}"], True)
                await callback.message.edit_reply_markup(None)
        elif 'subcateg' in callback.data:
            #Клавиатура списка подкатегорий
            try:
                keyboard = InlineKeyboardBuilder()
                data = callback.data.split('_')[1]
                if data[1] == 'next':
                    keyboard.button(text='⬅️', callback_data=f"subcateg_prev_{int(data[2]) - 1}")
                    keyboard.button(text='Категории', callback_data=f"opensubcateg_category")
                    if len(categs) > (int(data[2]) + 1):
                        keyboard.button(text='➡️', callback_data=f"subcateg_next_{(int(data[2]) + 1)}")
                    else:
                        keyboard.button(text='❌', callback_data=f"not_next")
                    for each in categs[int(data[2])]:
                        keyboard.button(text=each, callback_data=f"opensubcateg_{each}")
                elif data[1] == 'prev':
                    if int(data[2]) != 0:
                        keyboard.button(text='⬅️', callback_data=f"subcateg_prev_{int(data[2]) - 1}")
                    else:
                        keyboard.button(text='❌', callback_data=f"not_prev")
                    keyboard.button(text='Категории', callback_data=f"opensubcateg_category")
                    keyboard.button(text='➡️', callback_data=f"subcateg_next_{(int(data[2]) + 1)}")
                    for each in categs[int(data[2])]:
                        keyboard.button(text=each, callback_data=f"opensubcateg_{each}")
                keyboard.adjust(3, 1)
                await callback.message.edit_reply_markup(reply_markup=keyboard.as_markup())
            except:
                await callback.message.edit_reply_markup(None)
                await insertdb(['ERROR', f"{traceback.format_exc()}"], True)
        elif 'opencateg' in callback.data:
            #Клавиатура получения подкатегорий из категории
            try:
                keyboard = InlineKeyboardBuilder()
                data = callback.data.split('_')[1]
                if data == 'category':
                    #К списку категорий
                    keyboard = await kbforcateg()
                    await callback.message.edit_text(text='Выберите категорию', reply_markup=keyboard.as_markup())
                else:
                    #Получить подкатегории
                    keyboard = await subcateg(data)
                    await callback.message.edit_text(text='Выберите подкатегорию',reply_markup=keyboard.as_markup())
            except:
                await insertdb(['ERROR', f"{traceback.format_exc()}"], True)
                await callback.message.edit_reply_markup(None)
        elif 'category' in callback.data:
            #Клавиатура с категориями
            try:
                keyboard = InlineKeyboardBuilder()
                data = callback.data.split('_')
                if data[1] == 'next':
                    keyboard.button(text='⬅️', callback_data=f"category_prev_{int(data[2])-1}")
                    if len(categs) > (int(data[2])+1):
                        keyboard.button(text='➡️', callback_data=f"category_next_{(int(data[2])+1)}")
                    else:
                        keyboard.button(text='❌', callback_data=f"not_next")
                    for each in categs[int(data[2])]:
                        keyboard.button(text=each, callback_data=f"opencateg_{each}")
                elif data[1] == 'prev':
                    if int(data[2]) != 0:
                        keyboard.button(text='⬅️', callback_data=f"category_prev_{int(data[2]) - 1}")
                    else:
                        keyboard.button(text='❌', callback_data=f"not_prev")
                    keyboard.button(text='➡️', callback_data=f"category_next_{(int(data[2]) + 1)}")
                    for each in categs[int(data[2])]:
                        keyboard.button(text=each, callback_data=f"opencateg_{each}")
                keyboard.adjust(2,1)
                await callback.message.edit_reply_markup(reply_markup=keyboard.as_markup())
            except:
                await callback.message.edit_reply_markup(None)
                await insertdb(['ERROR', f"{traceback.format_exc()}"], True)
        elif 'admin' in callback.data:
            #Обработка кнопок администратора в группе
            await state.clear()
            data = await getfromdb(f"SELECT user_id FROM tgadmins")
            adminslist = [int(userid['user_id']) for userid in data]
            if callback.data == 'admin_setchanel' and callback.from_user.id in adminslist:
                #Кнопка установки канала
                await state.set_state(StateChat.curstatus)
                await state.update_data(curstatus=f'updatechanel')
                await callback.message.answer(f"Перешлите сюда пост из нужного канала",reply_markup=cancelkeyboard.as_markup())
                await callback.message.edit_reply_markup(None)
            elif callback.data == 'admin_sendall' and callback.from_user.id in adminslist:
                #Кнопка создания рассылки
                await state.set_state(StateChat.curstatus)
                await state.update_data(curstatus=f'getmsgforsend')
                checkkeyboardsend = cancelkeyboard.copy()
                checkkeyboardsend.button(text=f"Проверить",callback_data='admin_checkforall')
                #Пока не нажать проверить или отменить будет записывать все данные в словарь
                for each in sendmsg:  # Очистка словаря с данными для рассылки
                    sendmsg[each] = None
                await callback.message.answer(f"Отправьте сообщение которое хотите разослать (можно пересылать или отправлять отдельно фото, текст. клавиатуру)\nПо окончанию для проверки нажмите кнопку 'Проверить'",
                                              reply_markup=checkkeyboardsend.as_markup())
                await callback.message.edit_reply_markup(None)
            elif callback.data == 'admin_deletelastsend' and callback.from_user.id in adminslist:
                #Запрос подтверждения удаления последней рассылки
                deleteallkeyboardsend = cancelkeyboard.copy()
                deleteallkeyboardsend.button(text=f"Удалить", callback_data='admin_deletespam')
                await callback.message.answer(f"Вы уверены что хотите удалить последнюю рассылку у всех?", reply_markup=deleteallkeyboardsend.as_markup())
                await callback.message.edit_reply_markup(None)
            elif callback.data == 'admin_checkforall':
                #Запрос получившегося сообщения перед отправкой
                await callback.message.edit_reply_markup(None)
                if sendmsg['media'] or sendmsg['text']:
                    if sendmsg['media']:
                        if 'photo' in sendmsg['media']:
                            await callback.message.answer_photo(sendmsg['media']['photo'], caption=sendmsg['text'], reply_markup=sendmsg['keyboard'])
                        else:
                            await callback.message.answer_video(sendmsg['media']['video'], caption=sendmsg['text'], reply_markup=sendmsg['keyboard'])
                    else:
                        await callback.message.answer(sendmsg['text'],reply_markup=sendmsg['keyboard'])
                    sendallkeyboardsend = cancelkeyboard.copy()
                    sendallkeyboardsend.button(text=f"Запустить", callback_data='admin_launchspam')
                    await callback.message.answer(f"Запустить ли рассылку по пользователям?", reply_markup=sendallkeyboardsend.as_markup())
                else:
                    await callback.message.answer(f"Вы ничего не загрузили. Попробуйте заново")
            elif callback.data == 'admin_deletespam':
                #Удаление последней рассылки
                await callback.message.edit_reply_markup(None)
                await callback.message.answer(f"Начинаю удаление")
                data = await getfromdb(f"SELECT userswhom_id FROM sendmessages WHERE id = (SELECT MAX(id) FROM sendmessages)")
                if len(data) > 0:
                    listusers = json.loads(data[0]['userswhom_id'])
                    success = 0
                    for eachuser in listusers:
                        if eachuser != 'total':
                            try:
                                await bot.delete_message(int(eachuser), int(listusers[eachuser]))
                                success += 1
                            except Exception as e:
                                if 'message to delete not found' in str(e):
                                    #Уже были удалены до этого
                                    success += 1
                                print('log')
                    await callback.message.answer(f"Успешно удалено {success} из {len(listusers)-1}")
            elif callback.data == 'admin_launchspam':
                #Запуск рассылки по всем
                await callback.message.answer(f"Начинаю рассылку")
                await callback.message.edit_reply_markup(None)
                jsonempty = {'total': 0}
                fileid = ''
                filetype = ''
                data = await getfromdb(f"SELECT user_id FROM users")
                if len(data) > 0:
                    listusers = [int(each['user_id']) for each in data]
                    success = 0
                    for eachuser in listusers:
                        try:
                            if sendmsg['media']:
                                if 'photo' in sendmsg['media']:
                                    fileid = sendmsg['media']['photo']
                                    filetype = 'photo'
                                    newmsg = await bot.send_photo(eachuser,sendmsg['media']['photo'],caption=sendmsg['text'],reply_markup=sendmsg['keyboard'])
                                else:
                                    filetype = 'video'
                                    fileid = sendmsg['media']['video']
                                    newmsg = await bot.send_video(eachuser,sendmsg['media']['video'],caption=sendmsg['text'],reply_markup=sendmsg['keyboard'])
                            else:
                                newmsg = await bot.send_message(eachuser,sendmsg['text'],reply_markup=sendmsg['keyboard'])
                            jsonempty[eachuser] = newmsg.message_id
                            success += 1
                        except:
                            await insertdb(['ERROR', f"{traceback.format_exc()}"], True)
                    await callback.message.answer(f"Успешно разослали {success} из {len(data)}")
                    jsonempty['total'] = f'{success} из {len(data)}'
                await insertdb([f"INSERT INTO sendmessages (text,filetype,fileid,userswhom_id) VALUES ('{sendmsg['text']}','{filetype}','{fileid}','{json.dumps(jsonempty)}')"])
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)

#Удачная оплата
@dp.message(F.successful_payment)
async def mess(payment: SuccessfulPayment,state: FSMContext):
    # currency='RUB' total_amount=2300 invoice_payload='TEST PAY' telegram_payment_charge_id='7268797935_58327683_843992_7377758005785025708' provider_payment_charge_id='7268797935_58327683_843992_7377758005785025708' shipping_option_id=None order_info=OrderInfo(name='Damir', phone_number='79568866653', email=None, shipping_address=None)
    try:
        data = payment.successful_payment
        #Данные для вставку в таблицу ГУГЛ
        name = f"{data.order_info.name}"
        phone = f"{data.order_info.phone_number}"
        userid = f"{payment.from_user.id}"
        payed = f"{int(data.total_amount) / 100} {data.currency}"
        date = f"{datetime.now(tz=pytz.timezone('Europe/Moscow'))}"
        inform = json.loads(data.invoice_payload)
        #Текст для вставки в таблицу
        informtext = ''
        for eachkey in inform:
            informtext += f"{eachkey} - Кол-во: {inform[eachkey]['count']} | Оплачено {int(inform[eachkey]['totalsum']) / 100}\n"
        whereinfo = await getfromdb(f"SELECT shipp_adress FROM users WHERE user_id = {userid}")
        if len(whereinfo) == 1:
            where = whereinfo[0]['shipp_adress']
        else:
            where = 'Уточнить'

        #Удаление кнопок на сообщении
        curstate = await state.get_data()
        if 'curstatus' in curstate:
            databtn = str(curstate['curstatus']).split('_')
            try:
                await bot.edit_message_reply_markup(payment.from_user.id, int(databtn[1]))
            except:
                await insertdb(['ERROR', f"{traceback.format_exc()}"], True)
        await state.clear()
        await tablein([userid, name, phone, where, informtext, payed, date])
        await insertdb([f"DELETE FROM basket WHERE user_id = {userid} AND topay is not Null"])
    except:
        await insertdb(['ERROR', f"PAY\n{payment}\n{state}\n{traceback.format_exc()}"], True)

#обработка сообщений при активном состоянии
@dp.message(StateChat.curstatus)
async def onestate(message: types.Message,state: FSMContext):
    global sendmsg #Словарь рассылки по всем
    curstate = await state.get_data()
    try:
        data = await getfromdb(f"SELECT user_id FROM tgadmins")
        adminslist = [int(userid['user_id']) for userid in data]
        if str(message.chat.id) == os.getenv('chanelid') and message.from_user.id in adminslist:
            #Сообщения только из группы админа
            if curstate['curstatus'] == "updatechanel":
                #Получение пересыла от канала для обязательной подписки
                if message.forward_from_chat:
                    newchanelid = message.forward_from_chat.id
                    result = await is_bot_admin(newchanelid) #Проверка на админа
                    if result:
                        await insertdb([f"UPDATE settings SET values = {newchanelid} WHERE key = 'subchanel'"])
                        await message.answer(f"Канал успешно обновлен")
                        await state.clear()
                    else:
                        botdata = await bot.get_me()
                        await message.answer(
                            f"Бот не явлеятся администратором данного канала или не имеет доступа к ссылке канала\nДобавьте в администраторы @{botdata.username} и перешлите повторно")
                else:
                    await message.answer(f"Сообщение не является пересылом")
            elif curstate['curstatus'] == "getmsgforsend":
                #Получение данных для общей рассылки, принимает по частям
                if message.photo:
                    if sendmsg['media']:
                        sendmsg['media']['photo'] = message.photo[-1].file_id
                    else:
                        sendmsg['media'] = {'photo':str(message.photo[-1].file_id)}
                elif message.video:
                    if sendmsg['media']:
                        sendmsg['media']['video'] = message.video.file_id
                    else:
                        sendmsg['media'] = {'video':str(message.video.file_id)}
                if message.text or message.caption:
                    if message.text:
                        sendmsg['text'] = message.text
                    else:
                        sendmsg['text'] = message.caption
                if message.reply_markup:
                    sendmsg['keyboard'] = message.reply_markup
        else:
            #Все сообщения
            if "basketadd_" in curstate['curstatus']:
                #Состояние ожидания кол-ва товара для корзины
                databtn = str(curstate['curstatus']).split('_')
                max = int(databtn[2]) #Наличие в магазине
                id = int(databtn[1]) #ID товара
                try:
                    userint = int(message.text)
                    #Проверка на допустимое кол-во
                    if userint <= max and userint > 0:
                        await insertdb([f"INSERT INTO basket (user_id,product_id,count) VALUES ({message.from_user.id},{id},{userint})"])
                        await message.answer(f"Добавлено {userint}")
                        await state.clear()
                    else:
                        await message.answer(f'Доступно {max} товара\nОтправьте допустимое кол-во')
                except:
                    await message.answer(f"Введите число")
            elif curstate['curstatus'] == 'getshippadress':
                #Состояние получения адреса доставки
                if message.text:
                    await insertdb([f"UPDATE users SET shipp_adress = '{message.text}' WHERE user_id = {message.from_user.id}"])
                    await state.clear()
                    await genforbuy(message.from_user.id,state)
                else:
                    await message.answer(f"Мне нужен текстовый адрес")
    except:
        await insertdb(['ERROR', f"{traceback.format_exc()}"], True)


async def main():
    await startup() #Вызов функции подготовки данных к работе
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())