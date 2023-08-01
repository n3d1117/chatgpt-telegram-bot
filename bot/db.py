import psycopg2
from psycopg2.extras import NamedTupleCursor


class Database:
    def __init__(self):
        self.connection = psycopg2.connect(
            "user=postgres host=localhost port=5432 dbname=bot_db")
        self.connection.autocommit = True

    def fetch_one(self, query, arg=None, factory=None, clean=None):
        """ Получает только одно ЕДИНСТВЕННОЕ значение (не ряд!) из таблицы
        :param query: Запрос
        :param arg: Переменные
        :param factory: dic (возвращает словарь - ключ/значение) или list (возвращает list)
        :param clean: С параметром вернет только значение. Без параметра вернет значение в кортеже.
        """
        try:
            cur = self.__connection(factory)
            self.__execute(cur, query, arg)
            return self.__fetch(cur, clean)

        except (Exception, psycopg2.Error) as error:
            self.__error(error)

    def fetch_all(self, query, arg=None, factory=None):
        """ Получает множетсвенные данные из таблицы
        :param query: Запрос
        :param arg: Переменные
        :param factory: dic (возвращает словарь - ключ/значение) или list (возвращает list)
        """
        try:
            cur = self.__connection(factory)
            self.__execute(cur, query, arg)
            return cur.fetchall()

        except (Exception, psycopg2.Error) as error:
            self.__error(error)

    def query_update(self, query, arg, message=None):
        """ Обновляет данные в таблице и возвращает сообщение об успешной операции """
        try:
            cur = self.connection.cursor()
            cur.execute(query, arg)
            return message

        except (Exception, psycopg2.Error) as error:
            self.__error(error)

    def close(self):
        cur = self.connection.cursor()
        cur.close()
        self.connection.close()

    def __connection(self, factory=None):
        # Dic - возвращает словарь - ключ/значение
        if factory == 'dic':
            cur = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # List - возвращает list (хотя и называется DictCursor)
        elif factory == 'list':
            cur = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Tuple
        else:
            cur = self.connection.cursor()

        return cur

    @staticmethod
    def __execute(cur, query, arg=None):
        # Метод 'execute' всегда возвращает None
        if arg:
            cur.execute(query, arg)
        else:
            cur.execute(query)

    @staticmethod
    def __fetch(cur, clean):
        # Если запрос был выполнен успешно, получим данные с помощью 'fetchone'
        if clean == 'no':
            # Вернет:
            #   Название:
            #       ('Royal Caribbean Cruises',)
            #   Дата:
            #       (datetime.datetime(2020, 6, 2, 13, 36, 35, 61052, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)),)
            fetch = cur.fetchone()
        else:
            # Вернет:
            #   Название:
            #       Royal Caribbean Cruises
            #   Дата:
            #       (da2020-06-02 13:36:35.061052+00:00
            fetch = cur.fetchone()[0]
        return fetch

    @staticmethod
    def __error(error):
        # В том числе, если в БД данных нет, будет ошибка на этапе fetchone
        print('Данных в бд нет или ошибка: {}'.format(error))
        return None


