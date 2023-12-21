import pytest
import sys
print(sys.path)
from nlq.data_access.dynamo_connection import ConnectConfigDao, ConnectConfigEntity
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture
def dao():
    return ConnectConfigDao('Test')


def test_crud_operations(dao):
    # Create
    entity = ConnectConfigEntity(1, 'MyDatabase', 'MySQL', 'testdb', 'localhost', 3306, 'user', 'password', 'Test DB')
    dao.add(entity)

    # Read
    retrieved = dao.get_by_name('MyDatabase')
    assert retrieved.db_name == 'testdb'

    # Update
    retrieved.comment = 'Updated comment'
    dao.update(retrieved)
    updated = dao.get_by_name('MyDatabase')
    assert updated.comment == 'Updated comment'

    # Delete
    dao.delete('MyDatabase')
    result = dao.get_by_name('MyDatabase')
    # print(f'{result=}')
    assert result is None


# def test_get_db_config(dao):
#     entity = ConnectConfigEntity(1, 'MyDB', 'MySQL', 'testdb', 'localhost', 3306, 'user', 'password', 'Test DB')
#     dao.add(entity)
#
#     config = dao.get_db_config('MyDB')
#     assert config['db_name'] == 'testdb'
#     assert config['db_type'] == 'MySQL'
#
#
def test_get_db_list(dao):
    entity1 = ConnectConfigEntity(1, 'my_mysql_db', 'MySQL', 'testdb1', 'localhost', 3306, 'user', 'password', 'Test DB 1')
    entity2 = ConnectConfigEntity(2, 'my_pg_db', 'Postgres', 'testdb2', 'localhost', 5432, 'user', 'password', 'Test DB 2')

    dao.add(entity1)
    dao.add(entity2)

    db_list = dao.get_db_list()
    assert len(db_list) == 2
    assert db_list[0].db_name == 'testdb1'
    assert db_list[1].db_name == 'testdb2'

