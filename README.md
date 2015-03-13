# rss-email
Отправка RSS на E-mail

## О проекте

Проект создан как принципиальная замена Google Reader. Из RSS-лент формируется письмо со ссылками и отправляется по почте. Написан на Python.

## Новости
[RSS](https://github.com/mono9lith/rss-email/releases.atom)

* 06.03.15 Версия 1.5:
  * рефакторинг
  * изменён лог
  * добавлена поддержка нескольких пользователей в 1 конфиге
  * теперь настройки в конфиге меняются без перезапуска
  * формат конфига изменён на json
  * теперь новости приходят в виде вложенного HTML-файла (почтовые клиенты портят HTML письма)
  * добавлено сохранение json-файлов с новостями 
* 15.09.14 Версия 1.4:
  * рефакторинг
  * исправление мелких ошибок
  * изменён лог
  * добавлено сохранение HTML файлов 
* 25.03.14 Версия 1.3:
  * добавлены description
  * улучшения быстродействия
  * добавлена возможность извлечения ссылок из HTML
  * исправлены дублирующиеся новости
  * добавлена чистка отсутствующих в конфиге записей из базы
  * теперь скрипт сам отрабатывает каждые 10 минут
  * переделан конфиг, он стал более удобным 
* 18.06.13 Версия 1.2:
  * Незначительные оптимизации.
  * Чистка кода. 
* 11.06.13 Версия 1.1:
  * Расширенные настройки. 
* 07.06.13 Версия 1.0:
  * Первый выпуск.

## Требования

1. Python версии 3.0 и выше.
1. config.json
1. typo.py 

## Использование

* ```(опционально) mkdir archive_<config name>; ARCHIVE -> True```
* ```nohup nice -19 python3 rss.py &```

Настройка извлечения ссылок из HTML: нужно передать родительский элемент, атрибут и значение ("div", "class", "b-infografic-itemtext")

config.json

```json
{                                                                              
    "user_1": {                                                                
        "FROM": "example@mail.com",                                            
        "TO": "example@mail.com",                                              
        "LOGIN": "example@mail.com",                                           
        "PASSWORD": "mysuperpassword",                                         
        "SMTP": "smtp.mail.com",                                               
        "SMTP_PORT": 587,                                                      
        "TLS": true,                                                           
        "HOUR": 8,                                                             
        "RECORDS_MAX": 250,                                                    
        "TITLE_LENGTH_MAX": 150,                                               
        "DESC_LENGTH_MAX": 250,                                                
        "FEEDS": {                                                             
            "какая-то группа лент": {                                          
                "какая-то лента новостей1": "http://lenta.ru/rss/last24",      
                "какая-то лента новостей2": "http://habrahabr.ru/rss/"
            }                                                                  
        }                                                                      
    },                                                                         
    "user_2": {                                                                
        "FROM": "example@mail.com",                                            
        "TO": "example@mail.com",                                              
        "LOGIN": "example@mail.com",                                           
        "PASSWORD": "mysuperpassword",                                         
        "SMTP": "smtp.mail.com",                                               
        "SMTP_PORT": 587,                                                      
        "TLS": true,                                                           
        "HOUR": 8,                                                             
        "RECORDS_MAX": 250,                                                    
        "TITLE_LENGTH_MAX": 150,                                               
        "DESC_LENGTH_MAX": 250,                                                
        "FEEDS": {                                                             
            "какая-то группа лент": {                                          
                "какая-то лента новостей1": "http://lenta.ru/rss/last24",      
                "какая-то лента новостей2": "http://habrahabr.ru/rss/",
                "Итар-Тасс инфографика": {                                     
                    "url": "http://itar-tass.com/infographics",                
                    "root": ["div", "class", "b-infografic-item__text"]        
                },                                                             
            }                                                                  
        }                                                                      
    }                                                                          
}
```

## Авторы

* Александр ```<mono9lith at gmail dot com>```

## Ссылки

* [Google code](https://code.google.com/p/rss-email/)

## Иллюстрация

![иллюстрация](https://docs.google.com/uc?export=view&id=0BxX1CJOPtyaLRTVkbTREYXJkUlE "иллюстрация")

[оригинал изображения](https://docs.google.com/uc?export=view&id=0BxX1CJOPtyaLRTVkbTREYXJkUlE)
