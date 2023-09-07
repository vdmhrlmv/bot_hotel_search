import os
from typing import Any

from telebot import TeleBot, types
from dotenv import load_dotenv
from loguru import logger

from botrequests.RequestsFromHotelsAPI import RequestToAPI
from botrequests.UserHistoryDB import SqliteDB
from botrequests.Session import User
import time

# настройка логирования
logger.add('bot_logfile.log', format='{time}|{level}|{module}|{message}', backtrace=True, diagnose=True, mode='w')


# класс бота, реализует основной сценарий
class MyTeleBot(TeleBot):

    # Инициализация объекта для доступа к API-процедурам Hotels
    hotels_api = RequestToAPI()
    # Инициализация объекта взаимодействия с базой данных истории запросов пользователей
    DB = SqliteDB()

    def __init__(self, token: Any) -> None:
        super().__init__(token)

        # Начальная инициализация базы данных для хранения истории запросов,
        # списка результатов поиска,
        # словаря для хранения объектов - состояние активных пользователей работающих с ботом.
        self.DB.db_connect(file_name='HistoryDB.sqlite3')
        self.result_list = []
        self.user_dict = dict()

    def start(self, message) -> None:
        """Начало работы бота"""
        # Создание объекта пользователя, если он еще не создан
        if not self.user_dict.get(message.from_user.id):
            self.user_dict[message.from_user.id] = User(message)
        self.user_dict[message.from_user.id].set_session_start()

        # Обработка команд:
        if message.text == '/start':
            """Вызывается по команде `/start`."""
            # параметры активации клавиатуры для выбора команд
            markup = self.show_keyboard(['/lowprice', '/highprice', '/bestdeal', '/history'], )
            self.send_message(message.from_user.id, "Выберите команду.\n "
                                                    "Справка по командам - /help:", reply_markup=markup)
        elif message.text == '/help':
            """Вызывается по команде `/help`."""
            self.send_message(message.from_user.id, 'Помощь по командам бота:'
                                                    '\n/lowprice — вывод самых дешёвых отелей в городе.'
                                                    '\n/highprice — вывод самых дорогих отелей в городе.'
                                                    '\n/bestdeal — вывод отелей, наиболее подходящих по цене '
                                                    'и расположению от центра.'
                                                    '\n/history — вывод истории поиска.'
                                                    '\n/start — начало работы с ботом.',
                                                    reply_markup=types.ReplyKeyboardRemove())
        elif message.text == '/lowprice':
            """Вызывается по команде `/lowprice`."""

            # Получение списка из последних трех запрошенных пользователем городов
            # и подготовка на его основе кнопок для выбора
            markup = self.last_city_request(message.from_user.id)
            self.send_message(message.from_user.id, 'Поиск самых дешёвых отелей в городе.'
                                                    '\n\nВведите название города, или выберите один из '
                                                    'последних вариантов поиска:',
                                                    reply_markup=markup)
            # Сохранение сценария выбранного пользователем в объекте пользователя
            self.user_dict[message.from_user.id].set_scenario('/lowprice')
            # Указание обработчика для следующего сообщения
            self.register_next_step_handler(message, self.city_search)

        elif message.text == '/highprice':
            """Вызывается по команде `/highprice`."""
            markup = self.last_city_request(message.from_user.id)
            self.send_message(message.from_user.id, 'Поиск самых дорогих отелей в городе.'
                                                    '\n\nВведите название города, или выберите один из '
                                                    'последних вариантов поиска:',
                                                    reply_markup=markup)
            self.user_dict[message.from_user.id].set_scenario('/highprice')
            self.register_next_step_handler(message, self.city_search)
        elif message.text == '/bestdeal':
            """Вызывается по команде `/bestdeal`."""
            markup = self.last_city_request(message.from_user.id)
            self.send_message(message.from_user.id, 'Поиск отелей, наиболее подходящих по цене и расположению '
                                                    'от центра.'
                                                    '\n\nВведите название города, или выберите один из '
                                                    'последних вариантов поиска:',
                                                    reply_markup=markup)
            self.user_dict[message.from_user.id].set_scenario('/bestdeal')
            self.register_next_step_handler(message, self.city_search)
        elif message.text == '/history':
            """Вызывается по команде `/history`."""
            markup = self.show_keyboard(['3', '5', '10', '15'], )
            self.send_message(message.from_user.id, 'Cколько последних найденных отелей показать:', reply_markup=markup)
            self.register_next_step_handler(message, self.user_history)

    # Вывод истории запросов пользователя
    def user_history(self, message) -> None:

        # Получение истории запросов текущего пользователя из БД
        log = self.DB.db_get_user_log(user_id=message.from_user.id, limit=int(message.text))
        markup = self.show_keyboard(['/start'],)

        # Форматирование вывода истории
        self.send_message(message.from_user.id, 'История Ваших запросов:', reply_markup=types.ReplyKeyboardRemove())
        if log:
            self.send_message(message.from_user.id, f'Дата: {time.ctime(log[0][1])}\nКоманда: {log[0][0]}')
            prev_datetime = log[0][1]
            hotel_list = ''
            while len(log) > 0:
                item = log.pop(0)
                if prev_datetime == item[1]:
                    hotel_list += f'{item[2]}\n'
                else:
                    self.send_message(message.from_user.id, f'Результаты поиска:\n{hotel_list}', reply_markup=markup)
                    self.send_message(message.from_user.id, f'Дата: {time.ctime(item[1])}\nКоманда: {item[0]}')
                    hotel_list = f'{item[2]}\n'
                    prev_datetime = item[1]
            self.send_message(message.from_user.id, f'Результаты поиска:\n{hotel_list}', reply_markup=markup)
        else:
            self.send_message(message.from_user.id, 'История Ваших запросов пуста...', reply_markup=markup)

    # Процедура поиска запрошенного пользователем города
    def city_search(self, message) -> None:
        # Если введена команда /start - то выход из текущего сценария
        if not self.return_to_start(message):
            self.send_message(message.from_user.id, '...ищу город...')
            # Сохранение в объекте пользователя запрашиваемого города
            self.user_dict[message.from_user.id].set_city(message.text)
            # Поиск id города
            destination_id = self.hotels_api.city_search(message.text)
            if destination_id > 0:
                self.user_dict[message.from_user.id].set_destination_id(destination_id)
                markup = self.show_keyboard(['5', '10', '15', '20', '25'])
                # Если город найден, то переход к следующему вопросу
                self.send_message(message.from_user.id, 'Какое количество отелей вывести?', reply_markup=markup)
                self.register_next_step_handler(message, self.page_size_request)
            else:
                self.send_message(message.from_user.id, 'Город не найден, попробуйте ещё раз.')
                self.register_next_step_handler(message, self.city_search)

    # Запрос количества выводимых отелей
    def page_size_request(self, message) -> None:
        if not self.return_to_start(message):
            if self.user_dict[message.from_user.id].set_page_size(message.text):
                markup = self.show_keyboard(['Да', 'Нет'], )
                self.send_message(message.from_user.id, 'Выводить фотографии отелей?', reply_markup=markup)
                self.register_next_step_handler(message, self.select_hotels_photo)
            else:
                self.send_message(message.from_user.id, '...количество отелей должно быть не более 25-ти.')
                self.register_next_step_handler(message, self.page_size_request)

    # Запрос по выводу фотографий отелей
    def select_hotels_photo(self, message) -> None:
        if not self.return_to_start(message):
            if message.text.lower() == 'да':
                markup = self.show_keyboard(['1', '3', '5', '10', '15'], )
                self.send_message(message.from_user.id, 'Какое количество фотографий вывести?', reply_markup=markup)
                self.register_next_step_handler(message, self.number_of_photo_request)
            else:
                self.user_dict[message.from_user.id].set_numb_photo('0')
                self.send_message(message.from_user.id, '...вывод фотографий отключен.',
                                  reply_markup=types.ReplyKeyboardRemove())
                # Если вывод фото не нужен - то переход к запросу данных по отелям
                self.scenario_start(message)

    # Запрос количества фотографий
    def number_of_photo_request(self, message) -> None:
        if not self.return_to_start(message):

            if self.user_dict[message.from_user.id].set_numb_photo(message.text):
                self.scenario_start(message)
            else:
                self.send_message(message.from_user.id, '...количество фотографий должно быть не более 25-ти.')
                self.register_next_step_handler(message, self.number_of_photo_request)

    # Выполнение запросов данных по отелям
    def scenario_start(self, message) -> None:
        if self.user_dict[message.from_user.id].scenario != '/bestdeal':
            self.send_message(message.from_user.id, '...ищу отели...', reply_markup=types.ReplyKeyboardRemove())

        # Запрос данных по сценарию /lowprice
        if self.user_dict[message.from_user.id].scenario == '/lowprice':
            self.result_list = self.hotels_api.hotels_search(self.user_dict[message.from_user.id].destination_id,
                                                             self.user_dict[message.from_user.id].page_size,
                                                             hotel_photo=self.user_dict[message.from_user.id]
                                                             .numb_photo)
            self.user_dict[message.from_user.id].set_status('search_lowprice')
            self.result_output(message)

        # Запрос данных по сценарию /highprice
        elif self.user_dict[message.from_user.id].scenario == '/highprice':
            self.result_list = self.hotels_api.hotels_search(self.user_dict[message.from_user.id].destination_id,
                                                             self.user_dict[message.from_user.id].page_size,
                                                             sort_order='PRICE_HIGHEST_FIRST',
                                                             hotel_photo=self.user_dict[message.from_user.id]
                                                             .numb_photo)
            self.user_dict[message.from_user.id].set_status('search_highprice')
            self.result_output(message)

        # Если активен сценарий /bestdeal то переход к запросам диапазонов цен и расстояний
        elif self.user_dict[message.from_user.id].scenario == '/bestdeal':
            self.send_message(message.from_user.id, 'В каком диапазоне цен $ выбирать отели?'
                                                    '\nmin - max', reply_markup=types.ReplyKeyboardRemove())
            self.register_next_step_handler(message, self.price_range_request)

    # Запрос диапазона цен
    def price_range_request(self, message) -> None:
        if not self.return_to_start(message):
            if self.user_dict[message.from_user.id].set_price(message.text):
                self.send_message(message.from_user.id, 'Введите диапазон расстояний от центра города, км'
                                                        '\nmin - max')
                self.register_next_step_handler(message, self.distance_range_request)
            else:
                self.send_message(message.from_user.id, '...диапазон не распознан, попробуйте еще раз')
                self.register_next_step_handler(message, self.price_range_request)

    # Запрос диапазона расстояний и данных по отелям для сценария /bestdea
    def distance_range_request(self, message) -> None:
        if not self.return_to_start(message):
            if not self.user_dict[message.from_user.id].set_distance(message.text):
                self.send_message(message.from_user.id, '...диапазон не распознан, попробуйте еще раз')
                self.register_next_step_handler(message, self.distance_range_request)
            else:
                self.send_message(message.from_user.id, '...ищу отели...')

            # запрос данных по отелям для сценария /bestdeal
            self.result_list = self.hotels_api.hotels_search(self.user_dict[message.from_user.id].destination_id,
                                                             self.user_dict[message.from_user.id].page_size,
                                                             sort_order='PRICE',
                                                             min_distance=self.user_dict[message.from_user.id]
                                                             .min_distance,
                                                             max_distance=self.user_dict[message.from_user.id]
                                                             .max_distance,
                                                             min_price=self.user_dict[message.from_user.id].min_price,
                                                             max_price=self.user_dict[message.from_user.id].max_price,
                                                             hotel_photo=self.user_dict[message.from_user.id]
                                                             .numb_photo)
            self.result_output(message)

    # Вывод в чат результатов поиска отелей
    def result_output(self, message) -> None:
        for i in self.result_list:
            self.send_message(message.from_user.id, str(i))
            # вывод местоположения отеля на карте
            lat = i.hotel_location['lat']
            lon = i.hotel_location['lon']
            if lat != 0 and lon != 0:
                self.send_location(message.from_user.id, latitude=lat, longitude=lon)
            # вывод фотографий отеля
            for i_photo in i.hotel_image_url:
                self.send_photo(message.from_user.id, photo=i_photo, caption=i.hotel_name)
        # Подготовка кнопки перехода на старт
        markup = self.show_keyboard(['/start'])

        logger.info(self.user_dict[message.from_user.id].get_user_log())

        # Запись в базу данных результатов запроса
        self.DB.db_insert(self.user_dict[message.from_user.id].get_user_log(),
                          [i_hotel.hotel_name for i_hotel in self.result_list])

        logger.info(f'Количество найденных отелей - {len(self.result_list)}.')
        self.send_message(message.from_user.id, f'Количество найденных отелей - {len(self.result_list)}.'
                                                f'\n\n Новый поиск - /start'
                                                f'\n Помощь по командам бота - /help', reply_markup=markup)
        # Удаление пользователя из списка активных пользователей
        try:
            self.user_dict.pop(message.from_user.id)
        except KeyError:
            logger.error('Ошибка при удалении пользователя.')

    # функция перехвата команды старт
    def return_to_start(self, message) -> bool:
        if message.text == '/start':
            markup = self.show_keyboard(['/start'])
            self.send_message(message.from_user.id, 'Возврат на старт.', reply_markup=markup)
            self.register_next_step_handler(message, self.start)
            return True
        else:
            return False

    # Функция отображение кнопок в чате
    @staticmethod
    def show_keyboard(list_of_button: list) -> Any:
        markup = types.ReplyKeyboardMarkup(row_width=len(list_of_button))
        list_of_itembtn = [types.KeyboardButton(str(i)) for i in list_of_button]
        for button in list_of_itembtn:
            markup.add(button)
        return markup

    # Функция запроса из истории трех последних городов
    def last_city_request(self, user_id: int) -> Any:
        last_city_list = self.DB.db_city_list(user_id=user_id)
        if len(last_city_list) == 0:
            markup = types.ReplyKeyboardRemove()
        else:
            markup = self.show_keyboard(self.DB.db_city_list(user_id=user_id))
        return markup

# Переменные окружения
load_dotenv()
my_bot = MyTeleBot(os.getenv('BOT_TOKEN'))


@my_bot.message_handler(content_types=['text'])
def start_bot(message):
    my_bot.start(message)


if __name__ == '__main__':
    logger.info('Бот запущен...')
    while True:
        try:
            my_bot.polling(none_stop=True, interval=0)
        except Exception as e:
            logger.error(e)
            time.sleep(10)
