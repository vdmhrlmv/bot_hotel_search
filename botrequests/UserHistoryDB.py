import os.path
import sqlite3
from loguru import logger


# Класс взаимодействия с базой данных SQLite
class SqliteDB:

    def __init__(self):
        self.db_filename = '../UserHistoryDB.sqlite3'  # имя файла базы данных по умолчанию
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Начальная инициализация базы данных, создание если ее нет
    # база данных состоит из двух таблиц - userquery и hotels связанных по полю id
    # в таблице userquery - хранится информация о параметрах запроса
    # в таблице hotels - список найденных отелей
    def db_connect(self, file_name: str = None) -> None:
        if file_name:
            self.db_filename = file_name
        db_path = os.path.join(self.BASE_DIR, self.db_filename)
        try:
            sqlite_connection = sqlite3.connect(db_path)
            cursor = sqlite_connection.cursor()
            logger.info('БД успешно подключена')
            create_table1_query = """CREATE TABLE userquery (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT 
                                    constraint id
			                        references hotels (id)
				                    on delete cascade,
                                    user_id INTEGER NOT NULL,
                                    datetime INTEGER NOT NULL,
                                    city_name TEXT,
                                    scenario TEXT);"""
            cursor.execute(create_table1_query)
            sqlite_connection.commit()
            logger.info(f'userquery таблица успешно создана. {cursor.fetchall()}')

            create_table2_query = """CREATE TABLE hotels (
                                                id INTEGER,
                                                hotel_name TEXT);"""
            cursor.execute(create_table2_query)
            sqlite_connection.commit()
            logger.info(f'hotels таблица успешно создана. {cursor.fetchall()}')
            cursor.close()

        except sqlite3.Error as e:
            logger.error(f'Ошибка БД. {e}')
        finally:
            if sqlite_connection:
                sqlite_connection.close()
                logger.info('Соединение с БД закрыто')

    # Запись истории запросов пользователей
    def db_insert(self, in_dict_user: dict, in_list_hotel: list) -> None:
        db_path = os.path.join(self.BASE_DIR, self.db_filename)
        try:
            # Соединение с БД
            sqlite_connection = sqlite3.connect(db_path)
            cursor = sqlite_connection.cursor()
            logger.info('БД успешно подключена')

            # список полей для запроса
            dict_data = [in_dict_user['user_id'], in_dict_user['datetime'], in_dict_user['city_name'],
                         in_dict_user['scenario']]
            # текст SQL-запроса
            sqlite_insert_query = """INSERT INTO userquery
                                    (user_id, datetime, city_name, scenario)
                                    VALUES (?, ?, ?, ?);"""
            # выполнение запроса
            cursor.execute(sqlite_insert_query, dict_data)
            sqlite_connection.commit()

            # получение id последней добавленной записи
            user_id = [in_dict_user['user_id']]
            sqlite_select_id = """SELECT id FROM userquery WHERE user_id = ? ORDER BY id DESC LIMIT 1"""
            cursor.execute(sqlite_select_id, user_id)
            query_result = cursor.fetchall()
            logger.info(f'Данные в userquery успешно добавлены. {query_result}')
            cursor.close()

            # Формирование списка отелей для добавления в таблицу hotels
            records_to_insert = list()
            for row in in_list_hotel:
                records_to_insert += (query_result[0][0], row),

            #logger.info(f"records_to_insert: {records_to_insert}")

            # выполнение запроса по добавлению в БД списка найденных отелей
            cursor = sqlite_connection.cursor()
            sqlite_insert_query = """INSERT INTO hotels
                                                (id, hotel_name)
                                                VALUES (?, ?);"""

            cursor.executemany(sqlite_insert_query, records_to_insert)
            sqlite_connection.commit()
            logger.info(f'Данные в hotels успешно добавлены.')

        except sqlite3.Error as e:
            logger.error(f'Ошибка БД. {e}')
        finally:
            if sqlite_connection:
                sqlite_connection.close()
                logger.info('Соединение с БД закрыто')

    # Получение из БД истории запросов пользователя
    def db_get_user_log(self, user_id: int, limit: int) -> list:
        query_result = []
        db_path = os.path.join(self.BASE_DIR, self.db_filename)
        try:
            sqlite_connection = sqlite3.connect(db_path)
            cursor = sqlite_connection.cursor()

            log_filter = [user_id, limit]
            sqlite_select_query = """SELECT userquery.scenario, userquery.datetime, hotels.hotel_name 
                                    FROM userquery LEFT JOIN hotels ON hotels.id = userquery.id 
                                    WHERE user_id = ? 
                                    ORDER BY userquery.datetime DESC
                                    LIMIT ?;"""
            cursor.execute(sqlite_select_query, log_filter)

            query_result = cursor.fetchall()
            cursor.close()

        except sqlite3.Error as e:
            logger.error(f'Ошибка БД. {e}')
        finally:
            if sqlite_connection:
                sqlite_connection.close()
                logger.info('Соединение с БД закрыто')
            #logger.info(query_result)
            return query_result

    # Запрос списка их последних трех названий городов, которые были запрошены пользователем
    def db_city_list(self, user_id: int) -> list:
        query_result = []
        db_path = os.path.join(self.BASE_DIR, self.db_filename)
        try:
            sqlite_connection = sqlite3.connect(db_path)
            cursor = sqlite_connection.cursor()

            log_filter = [user_id, ]
            sqlite_select_query = """SELECT DISTINCT city_name
                                            FROM userquery 
                                            WHERE user_id = ? 
                                            ORDER BY datetime DESC
                                            LIMIT 3;"""
            cursor.execute(sqlite_select_query, log_filter)

            for i in cursor.fetchall():
                query_result.append(i[0])

            cursor.close()

        except sqlite3.Error as e:
            logger.error(f'Ошибка БД. {e}')
        finally:
            if sqlite_connection:
                sqlite_connection.close()
                logger.info('Соединение с БД закрыто')
            return query_result
