from loguru import logger
import time


# Класс для хранения информации о сессии пользователя
class User:
    def __init__(self, message):
        self.user_id = message.from_user.id
        self.username = message.from_user.username
        self.user_first_name = message.from_user.first_name
        self.user_last_name = message.from_user.last_name
        self.status = 'session_start'
        self.scenario = ''
        self.city_name = ''
        self.destination_id = 0
        self.page_size = 0
        self.min_price = 0
        self.max_price = 0
        self.min_distance = 0.0
        self.max_distance = 0.0
        self.datetime = time.time()
        self.chat_id = 0
        self.numb_photo = 0

    # метод сохранения цены отеля
    def set_price(self, input_text: str) -> bool:
        try:
            self.min_price = int(input_text.split('-')[0])
            self.max_price = int(input_text.split('-')[1])
        except ValueError:
            logger.error('Ошибка ввода диапазона цен')
            return False
        else:
            self.status = 'price_ok'
            return True

    # проверка/сохранение количества отелей
    def set_page_size(self, input_text: str) -> bool:
        try:
            self.page_size = int(input_text)
            if not 0 < self.page_size < 26:
                raise ValueError
        except ValueError:
            logger.error('Ошибка ввода количества отелей')
            return False
        else:
            self.status = 'page_size_ok'
            return True

    # проверка/сохранение количества фотографий отелей
    def set_numb_photo(self, input_text: str) -> bool:
        try:
            self.numb_photo = int(input_text)
            if not 0 <= self.numb_photo <= 25:
                raise ValueError
        except ValueError:
            logger.error('Ошибка ввода количества фотографий')
            return False
        else:
            self.status = 'numb_photo_ok'
            return True

    # проверка/сохранение диапазона расстояний
    def set_distance(self, input_text: str) -> bool:
        try:
            self.min_distance = int(input_text.split('-')[0])
            self.max_distance = int(input_text.split('-')[1])
        except ValueError:
            logger.error('Ошибка ввода диапазона расстояний')
            return False
        else:
            self.status = 'distance_ok'
            return True

    # сохранение названия отеля
    def set_city(self, city_name: str) -> None:
        self.city_name = city_name
        self.destination_id = 0

    # сохранение id отеля
    def set_destination_id(self, id) -> None:
        self.destination_id = id
        self.status = 'city_ok'

    # сохранение текущего сценария
    def set_scenario(self, scenario: str) -> None:
        self.scenario = scenario
        self.set_status('scenario')

    def set_status(self, status) -> None:
        self.status = status
        if status == 'session_start':
            self.scenario = ''
            self.city_name = ''
            self.destination_id = 0

    # инициализация данных по городу при начале новой сессии поиска
    def set_session_start(self) -> None:
        self.scenario = ''
        self.city_name = ''
        self.destination_id = 0

    # подготовка данных для базы данных истории поиска
    def get_user_log(self) -> dict:
        user_log_dict = {
            'user_id': self.user_id,
            'datetime': self.datetime,
            'city_name': self.city_name,
            'scenario': self.scenario
        }
        return user_log_dict

    def __str__(self) -> str:
        return f'{self.user_id}, {self.username}, {self.user_first_name}, {self.user_last_name}, ' \
               f'{self.status}'
