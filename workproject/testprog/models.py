from django.db import models
import os
import requests
from dotenv import load_dotenv

load_dotenv()

#Таблица рассылок
class sendmessage(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    text = models.TextField(verbose_name='Сообщение')
    filetype = models.CharField(max_length=255,verbose_name='Тип файла')
    fileid = models.TextField(verbose_name='fileid Tg')
    datesend = models.DateTimeField(auto_now_add=True, verbose_name='Дата отправки')
    userswhom_id = models.JSONField(verbose_name='Результат рассылки')


    class Meta:
        db_table = 'sendmessages'
        managed = False
        verbose_name = "Отправленные сообщения"
        verbose_name_plural = "Отправленные сообщения"

    def __str__(self):
        return f"{self.id}|{self.userswhom_id}"

#Таблица товаров
class shop(models.Model):
    id = models.AutoField(primary_key=True)
    category = models.TextField(verbose_name='Категория')
    subcategory = models.TextField(verbose_name='Подкатегория')
    name = models.TextField(verbose_name='Товар')
    description = models.TextField(verbose_name='Описание')
    photoid = models.FileField(upload_to='shop_photos/', null=True, blank=True,verbose_name='fileid Tg')
    count = models.IntegerField(verbose_name='Кол-во')
    price = models.IntegerField(verbose_name='Цена')
    onsell = models.BooleanField(verbose_name='В продаже')
    dateadded = models.DateTimeField(auto_now_add=True, verbose_name='Добавлен')

    class Meta:
        db_table = 'shop'
        managed = False
        verbose_name = "Товар"
        verbose_name_plural = "Товар"

    def __str__(self):
        return self.name
    #фукнция загрузки фото на сервер телеграм и запись ссылки в таблицу
    def save(self, *args, **kwargs):
        if self.photoid:
            super().save(*args, **kwargs)
            file_path = self.photoid.path

            if os.path.exists(file_path) == True:
                tokenbot = os.getenv('bottoken')
                groupid = os.getenv('chanelid')
                topicid = os.getenv('topicid')
                #Загрузка в группу ТГ
                url = f"https://api.telegram.org/bot{tokenbot}/sendPhoto"
                data = {
                    'chat_id': groupid,
                    'caption': f"Категория: {self.category}\nПодкатегория: {self.subcategory}\n\nНазвание: {self.name}\nКол-во: {self.count}\nЦена {self.price}",
                    'reply_to_message_id': topicid
                }
                with open(file_path, "rb") as p:
                    file = p.read()
                files = {
                    'photo': file
                }

                response = requests.post(url, data=data, files=files)
                data = response.json()
                if data['result']['photo']:
                    self.photoid = data['result']['photo'][-1]['file_id']
                else:
                    self.photoid = None
                    self.onsell = False
                if os.path.exists(file_path) == True:
                    os.remove(file_path)

        super().save(*args, **kwargs)

#Таблица пользователей
class user(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.BigIntegerField(verbose_name='ID пользователя')
    username = models.TextField(verbose_name='НИК пользователя')
    shipp_adress = models.TextField(verbose_name='Адресс последней доставки')
    dateadded = models.DateTimeField(auto_now_add=True, verbose_name='Дата активации')
    lastonline = models.DateTimeField( verbose_name='Дата взаимодействия')


    class Meta:
        db_table = 'users'
        managed = False
        verbose_name = "Пользователи"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return str(self.user_id)

#Таблица вопросов
class FAQ(models.Model):
    id = models.AutoField(primary_key=True)
    quest = models.TextField(verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')


    class Meta:
        db_table = 'faq'
        managed = False
        verbose_name = "Вопросы"
        verbose_name_plural = "Вопросы"

    def __str__(self):
        return str(self.quest)

#Таблица добавления админов для рабботы через группу тг
class admins(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.BigIntegerField()
    username = models.CharField(max_length=255)
    dateadded = models.DateTimeField(auto_now_add=True, editable=False)


    class Meta:
        db_table = 'tgadmins'
        managed = False
        verbose_name = "Администраторы Telegram"
        verbose_name_plural = "Администраторы Telegram"

    def __str__(self):
        return str(self.user_id)

#Таблица для хранения настроек для бота
class settings (models.Model):
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=255, editable=False)
    values = models.TextField()
    dateadded = models.DateTimeField(auto_now_add=True, editable=False)


    class Meta:
        db_table = 'settings'
        managed = False
        verbose_name = "Настройки"
        verbose_name_plural = "Настройки"

    def __str__(self):
        return str(self.key)

#Таблица логирования
class Logs (models.Model):
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=255)
    typedata = models.CharField(max_length=255)
    values = models.TextField()
    dateadded = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'logs'
        managed = False
        verbose_name = "ЛОГИ"
        verbose_name_plural = "ЛОГИ"

    def __str__(self):
        return str(self.key)