import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger


# Класс для хранения информации по отелям
class HotelInfo:

    def __init__(self) -> None:
        self.hotel_name = ''
        self.hotel_address = ''
        self.distance_from_center = 0
        self.price = 0
        self.destination_id = None
        self.hotel_image_url = list()
        self.hotel_location = {'lat': 0.0, 'lon': 0.0}

    def set_hotel_name(self, name: str) -> None:
        self.hotel_name = name

    def set_hotel_address(self, address: str) -> None:
        self.hotel_address = address

    def set_distance_from_center(self, distance: float) -> None:
        self.distance_from_center = distance

    def set_price(self, price: int) -> None:
        self.price = price

    def set_destination_id(self, dest_id: int) -> None:
        self.destination_id = dest_id

    def __str__(self) -> str:
        return f'Название отеля: {self.hotel_name}\n' \
               f'Адрес: {self.hotel_address}\n' \
               f'Расстояние до центра: {self.distance_from_center}\n' \
               f'Цена: {self.price}'


# Класс запросов к Hotel API
class RequestToAPI:
    # Загрузка параметров доступа к сайту из файла
    load_dotenv()
    headers = {
        'x-rapidapi-key': os.getenv('X_RAPIDAPI_KEY'),
        'x-rapidapi-host': "hotels4.p.rapidapi.com"
    }
    url_locations = "https://hotels4.p.rapidapi.com/locations/search"
    url_properties = "https://hotels4.p.rapidapi.com/properties/list"
    url_photo = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"

    def __init__(self) -> None:
        self.city_name = ''
        self.dest_id = ''

    # метод поиска dectination_id города по его названию
    def city_search(self, city_name: str) -> int:
        self.dest_id = None
        self.city_name = city_name

        # Формирование строки запроса к API, получение данных в формате json
        # преобразование полученного ответа в словарь
        querystring = {"query": f"{self.city_name}", "locale": "ru_RU", "pageSize": "25", 'type': 'CITY'}
        response = requests.request("GET", self.url_locations, headers=self.headers, params=querystring)
        response_dict = json.loads(response.text)

        # получение из словаря с результатами данных по ключу destinationId
        try:
            for i_sugg in response_dict['suggestions']:
                if i_sugg['group'] == 'CITY_GROUP':
                    for i_group in i_sugg['entities']:
                        if i_group['name'].lower() == self.city_name.lower():
                            self.dest_id = i_group['destinationId']
        except KeyError:
            logger.error(f'Ошибка получения данных API <{response_dict}>')

        if self.dest_id:
            return int(self.dest_id)
        else:
            logger.error(f'Запрошенный город <{city_name}> не найден')
            return 0

    # метод поиска фотографий отеля по его id
    def get_hotels_photo(self, hotel_id: int, number_of_photo: int = 25) -> list:
        result_list = list()

        # Формирование строки запроса к API, получение данных в формате json
        # преобразование полученного ответа в словарь
        querystring = {"id": str(hotel_id)}
        response = requests.request("GET", self.url_photo, headers=self.headers, params=querystring)
        response_dict = json.loads(response.text)

        # формирование списка URL-фотографий в запрашиваемом количестве
        try:
            for i_hotel_img in enumerate(response_dict['hotelImages'], 1):
                if i_hotel_img[0] > number_of_photo:
                    break
                else:
                    result_list += i_hotel_img[1]['baseUrl'].replace('{size}', 'y'),
        except TypeError as e:
            logger.error(f'Ошибка получения ссылок на фото отеля. {e}')
        finally:
            return result_list

    # метод поиска отелей
    # входные данные:   destinationId отеля, количество отелей, способ сортировки результата
    #                   диапазон цен и расстояний до центра города
    #                   количество URL-ссылок на фото
    def hotels_search(self, dest_id, page_size: int, sort_order='PRICE', min_distance=0, max_distance=0,
                      min_price=0, max_price=0, hotel_photo=0) -> list:

        # формирование строки запроса к API
        date = str(datetime.now()).split(" ")[0]
        querystring = {"adults1": "1", "pageNumber": "1", "destinationId": f"{dest_id}", "pageSize": {page_size},
                       "checkOut": f"{date}", "checkIn": f"{date}", "sortOrder": f"{sort_order}", "locale": "ru_RU",
                       "currency": "USD"}

        if max_price > 0:
            querystring['priceMin'] = str(min_price)
            querystring['priceMax'] = str(max_price)

        # получение  ответа сервера
        response = requests.request("GET", self.url_properties, headers=self.headers, params=querystring)
        response_dict = json.loads(response.text)

        # анализ полученных данных
        result_list = []
        for i_results in response_dict['data']['body']['searchResults']['results']:
            # сброс флага проверки диапазона расстояний до центра города
            check_distance = False

            # создание объекта для сохранения данных отеля отеля
            curr_hotel = HotelInfo()
            curr_hotel.hotel_name = i_results["name"] # название отеля

            # адрес
            curr_hotel.hotel_address = (f"{i_results['address'].get('locality', '')} "
                                        f"{i_results['address'].get('postalCode', '')} "
                                        f"{i_results['address'].get('streetAddress', '')}")

            # получение списка URL-фотографий отеля
            curr_hotel.hotel_image_url = self.get_hotels_photo(hotel_id=int(i_results['id']),
                                                               number_of_photo=hotel_photo)
            # координаты местоположеня отеля
            try:
                curr_hotel.hotel_location['lat'] = float(i_results['coordinate'].get('lat', ''))
                curr_hotel.hotel_location['lon'] = float(i_results['coordinate'].get('lon', ''))
            except ValueError:
                curr_hotel.hotel_location['lat'] = 0
                curr_hotel.hotel_location['lon'] = 0
                logger.exception('Ошибка чтения координат')

            # расстояние от отеля до центра города
            for i in i_results['landmarks']:
                try:
                    if i['label'] == 'City center' or i['label'] == 'Центр города':
                        curr_hotel.distance_from_center = i['distance']
                        distance = i['distance'].split(' ')[0].replace(',', '.')

                        # проверка на вхождение отеля в заданный диапазон расстояний от центра города
                        if min_distance <= float(distance) <= max_distance or max_distance == 0:
                            check_distance = True
                except KeyError:
                    curr_hotel.distance_from_center = 'нет данных'
                    logger.exception('Ошибка получения расстояния до центра')

            # данные по цене
            try:
                curr_hotel.price = i_results['ratePlan']['price']['current']
            except KeyError:
                curr_hotel.price = "нет данных"
                logger.exception('Ошибка получения цены проживания')

            # добавление отеля в список результатов, если выполняется условие по расстоянию
            if check_distance and page_size > 0:
                result_list.append(curr_hotel)
                page_size -= 1

        return result_list
