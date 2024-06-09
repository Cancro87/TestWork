import json
import traceback
from django.contrib import admin
import os
import requests
from dotenv import load_dotenv
load_dotenv()
from .models import sendmessage,shop,user, FAQ,admins, settings, Logs
from django.utils.deprecation import MiddlewareMixin
from django.core.mail import mail_admins
from django.http import HttpResponseServerError

#Обработка непредвиденных ошибок
class ExceptionLoggingMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        error_trace = traceback.format_exc()
        log_error("admin", "Exception", error_trace)

        mail_admins(
            subject='Ошибка в админке',
            message=f'Ошибка в админке: {error_trace}',
            fail_silently=True
        )
        return HttpResponseServerError("возникла ошибка")

#Функция записи в таблицу LOGS
def log_error(key, typedata, values):
    try:
        log_entry = Logs(
            key=key,
            typedata=typedata,
            values=values
        )
        log_entry.save()
    except Exception as e:
        #Реализовать отправку ошибки в телеграм
        pass

#Поля по таблице вопросов
class faqTable(admin.ModelAdmin):
    list_display = ('id','quest','answer')
    search_fields = ('quest','answer')

#Поля по таблице админов
class adminsTable(admin.ModelAdmin):
    list_display = ('id','user_id','username','dateadded')

#Поля по таблице настроек
class settingsTable(admin.ModelAdmin):
    list_display = ('id','key','values','dateadded')
    readonly_fields = ('id', 'key')

    #Запрет доступа на добавление и удаление полей
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

#Поля по таблице пользователей
class usersTable(admin.ModelAdmin):
    readonly_fields = ('id','user_id','username','dateadded','lastonline','shipp_adress')
    list_display = ('id','user_id','username','dateadded','lastonline')
    search_fields = ('user_id', 'username','shipp_adress')

    #Запрет на редактирование из админки
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

#Поля по таблице логов
class logTable(admin.ModelAdmin):
    readonly_fields = ('id','key','typedata','values','dateadded')
    list_display = ('id','key','typedata','values','dateadded')
    search_fields = ('key', 'typedata','values','dateadded')

    # Запрет на редактирование из админки
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

#Поля по таблице товаров
class shopTable(admin.ModelAdmin):
    list_display = ('id','category','subcategory','name','description','photoid','count','price','onsell','dateadded')
    fields = ('category','subcategory','name','description','count', 'price','onsell', 'photoid')
    readonly_fields = ('dateadded','id')
    search_fields = ('category','subcategory','name')

    # Стиль для добавления нового товара
    class Media:
        css = {
            'all': ('shop.css',),
        }

#Поля по таблице рассылов
class sendAdmin(admin.ModelAdmin):
    readonly_fields = ('id','text', 'filetype', 'fileid', 'datesend', 'userswhom_id')
    list_display = ('id','text', 'filetype', 'fileid', 'datesend', 'userswhom_id')
    search_fields = ('text', 'datesend')
    actions = ['deletespam']

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    #Действие для удаление нужной рассылки у пользователей
    @admin.action(description=f"Удалить выбранные рассылки у пользователей")
    def deletespam(self,request,queryset):
        for obj in queryset:
            tokenbot = os.getenv('bottoken')
            URL = f"https://api.telegram.org/bot{tokenbot}/deleteMessage"
            data = str(obj).split('|')
            jsondatas = json.loads(data[1].replace("'",'"'))
            success = 0
            for eachuser in jsondatas:
                if eachuser != 'total':
                    try:
                        dataparse = {
                            "chat_id": eachuser,
                            "message_id": jsondatas[eachuser]
                        }
                        response = requests.post(URL, data=dataparse)
                        resp = response.json()
                        if resp['ok'] == False:
                            if 'message to delete not found' in resp['description']:
                                success += 1
                            else:
                                log_error("admin", "INFORM _ deletemsg", resp['description'])
                        else:
                            success += 1
                        #raise Exception('hhh')
                    except:
                        log_error("admin", "ERROR", traceback.format_exc())


            self.message_user(request, f"Рассылка {data[0]} удалена у {success} из {len(jsondatas)-1}")


#Регистрация моделей
admin.site.register(sendmessage, sendAdmin)
admin.site.register(shop, shopTable)
admin.site.register(user, usersTable)
admin.site.register(FAQ, faqTable)
admin.site.register(admins, adminsTable)
admin.site.register(settings, settingsTable)
admin.site.register(Logs, logTable)

