import threading
import pytest
from sqlobject import SQLObject, StringCol
from sqlobject.compat import string_type
from sqlobject.tests.dbtest import getConnection, setupClass, supports
from sqlobject.tests.dbtest import setSQLiteConnectionFactory
from .test_basic import SOTestSO1


class SQLiteFactoryTest(SQLObject):
    name = StringCol()


def test_sqlite_factory():
    setupClass(SQLiteFactoryTest)

    if SQLiteFactoryTest._connection.dbName != "sqlite":
        pytest.skip("These tests require SQLite")
    if not SQLiteFactoryTest._connection.using_sqlite2:
        pytest.skip("These tests require SQLite v2+")

    factory = [None]

    def SQLiteConnectionFactory(sqlite):
        class MyConnection(sqlite.Connection):
            pass
        factory[0] = MyConnection
        return MyConnection

    setSQLiteConnectionFactory(SQLiteFactoryTest, SQLiteConnectionFactory)

    conn = SQLiteFactoryTest._connection.makeConnection()
    assert factory[0]
    assert isinstance(conn, factory[0])


def test_sqlite_factory_str():
    setupClass(SQLiteFactoryTest)

    if SQLiteFactoryTest._connection.dbName != "sqlite":
        pytest.skip("These tests require SQLite")
    if not SQLiteFactoryTest._connection.using_sqlite2:
        pytest.skip("These tests require SQLite v2+")

    factory = [None]

    def SQLiteConnectionFactory(sqlite):
        class MyConnection(sqlite.Connection):
            pass
        factory[0] = MyConnection
        return MyConnection

    from sqlobject.sqlite import sqliteconnection
    sqliteconnection.SQLiteConnectionFactory = SQLiteConnectionFactory

    setSQLiteConnectionFactory(SQLiteFactoryTest, "SQLiteConnectionFactory")

    conn = SQLiteFactoryTest._connection.makeConnection()
    assert factory[0]
    assert isinstance(conn, factory[0])
    del sqliteconnection.SQLiteConnectionFactory


def test_sqlite_aggregate():
    setupClass(SQLiteFactoryTest)

    if SQLiteFactoryTest._connection.dbName != "sqlite":
        pytest.skip("These tests require SQLite")
    if not SQLiteFactoryTest._connection.using_sqlite2:
        pytest.skip("These tests require SQLite v2+")

    def SQLiteConnectionFactory(sqlite):
        class MyConnection(sqlite.Connection):
            def __init__(self, *args, **kwargs):
                super(MyConnection, self).__init__(*args, **kwargs)
                self.create_aggregate("group_concat", 1, self.group_concat)

            class group_concat:
                def __init__(self):
                    self.acc = []

                def step(self, value):
                    if isinstance(value, string_type):
                        self.acc.append(value)
                    else:
                        self.acc.append(str(value))

                def finalize(self):
                    self.acc.sort()
                    return ", ".join(self.acc)

        return MyConnection

    setSQLiteConnectionFactory(SQLiteFactoryTest, SQLiteConnectionFactory)

    SQLiteFactoryTest(name='sqlobject')
    SQLiteFactoryTest(name='sqlbuilder')
    assert SQLiteFactoryTest.select(orderBy="name").\
        accumulateOne("group_concat", "name") == \
        "sqlbuilder, sqlobject"


def do_select():
    list(SOTestSO1.select())


def test_sqlite_threaded():
    setupClass(SOTestSO1)
    t = threading.Thread(target=do_select)
    t.start()
    t.join()
    # This should reuse the same connection as the connection
    # made above (at least will with most database drivers, but
    # this will cause an error in SQLite):
    do_select()


def test_empty_string():
    setupClass(SOTestSO1)
    test = SOTestSO1(name=None, passwd='')
    assert test.name is None
    assert test.passwd == ''


def test_memorydb():
    if not supports("memorydb"):
        pytest.skip("memorydb isn't supported")
    connection = getConnection()
    if connection.dbName != "sqlite":
        pytest.skip("These tests require SQLite")
    if not connection._memory:
        pytest.skip("The connection isn't memorydb")
    setupClass(SOTestSO1)
    connection.close()  # create a new connection to an in-memory database
    SOTestSO1.setConnection(connection)
    SOTestSO1.createTable()


def test_list_databases():
    connection = getConnection()
    if connection.dbName != "sqlite":
        pytest.skip("These tests require SQLite")
    assert connection.listDatabases() == ['main']


def test_list_tables():
    connection = getConnection()
    if connection.dbName != "sqlite":
        pytest.skip("These tests require SQLite")
    setupClass(SOTestSO1)
    assert SOTestSO1.sqlmeta.table in connection.listTables()
