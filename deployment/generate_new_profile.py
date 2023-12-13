import os
import sqlalchemy as db
import json

def main():

    print("Enter data source's profile name:")
    profile_name = input()

    print("Enter database type (mysql or postgresql):")
    db_type = input()

    print("Enter host:")
    host = input()

    print("Enter port:")
    port = input()

    print("Enter username:")
    username = input()

    print("Enter password:")
    password = input()

    print("Enter database name:")
    database = input()

    db_url = None
    schema = None
    if db_type == "mysql":
        db_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    elif db_type == "postgresql":
        db_url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        print("Enter schema name:")
        schema = input()
    else:
        print("Invalid database type")
        exit(1)

    print(f"Generated SQLAlchemy URL:{db_url}")

    print("Please confirm (Y/N):")
    confirm = input()

    if confirm == "Y":
        print('checking connection...')
        engine = db.create_engine(db_url)
        connection = engine.connect()
        print('connected to database')

        print("Enter table name (no schema name, seperated by ,), leave blank means all tables:")
        tables_string = input()
        if len(tables_string) > 0 and tables_string.strip() != '':
            # Split text on commas
            split_text = tables_string.split(",")

            # Trim each string
            if schema:
                split_tables = [schema + '.' + x.strip() for x in split_text]
            else:
                split_tables = [x.strip() for x in split_text]
        else:
            split_tables = []

        metadata = db.MetaData()
        if schema:
            metadata.reflect(bind=connection, schema=schema)
        else:
            metadata.reflect(bind=connection)
        tables = metadata.tables
        table_info = {}

        for table_name, table in tables.items():
            # If table name is provided, only generate DDL for those tables. Otherwise, generate DDL for all tables.
            if len(split_tables) > 0 and table_name not in split_tables:
                continue
            # Start the DDL statement
            ddl = f"CREATE TABLE {table_name} -- {table.comment} \n (\n"
            column_descriptions = []
            for column in table.columns:
                # get column description
                ddl += f"  {column.name} {column.type} -- {column.comment},\n"
            ddl = ddl.rstrip(',\n') + "\n)"  # Remove the last comma and close the CREATE TABLE statement
            table_info[table_name] = {}
            table_info[table_name]['ddl'] = ddl
            table_info[table_name]['description'] = table.comment

            print(f'added table {table_name}')

        with open(os.path.join(os.getcwd(), 'config_files', '1_config.json')) as f:
            profiles = json.load(f)

            if profile_name in profiles['data_sources']:
                print("Profile already exists. Do you want to overwrite? (Y/N)")
                confirm = input()
                if confirm == "Y":
                    profiles['data_sources'][profile_name]['ddl'] = table_info
                    profiles['data_sources'][profile_name]['db_url'] = db_url
                else:
                    print("Profile not added.")
                    exit(0)
            else:
                profiles['data_sources'][profile_name] = {
                    'db_url': db_url,
                    'ddl': table_info,
                    'hints': '',
                    'search_samples': [],
                    'opensearch': {'index_name': '$AOS_INDEX'}
                }
        with open(os.path.join(os.getcwd(), 'config_files', '1_config.json'), 'w', encoding='utf-8') as f:
            json.dump(profiles, f, ensure_ascii=False, indent=4)
        print("Profile added successfully!")
        # print(table_info)
        # print(json.dumps(table_info))
    else:
        print("Profile not added.")
        exit(0)


if __name__ == '__main__':
    main()