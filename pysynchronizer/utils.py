
import os

from uuid import UUID, uuid4

def is_valid_uuid(uuid_to_test):
    try:
        uuid_obj = UUID(uuid_to_test)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test

def generate_uuid():
    return str(uuid4())

def column_print(rows):
    col_width = []
    for row in rows:
        for idx, col in enumerate(row):
            if idx == len(col_width):
                col_width.append(0)
            col_width[idx] = max(col_width[idx], len(str(col)) + 2)

    for row in rows:
        print("".join(str(col).ljust(col_width[idx]) for idx, col in enumerate(row)))

def dbus_path_to_uuid(path):
    return path.rsplit('/',1)[1].replace('_','-')

def uuid_to_dbus_path(prefix, uuid):
    return prefix + uuid.replace('-','_')

def disable_argo_inet():
    if 'INET_IS_ARGO' in os.environ:
        del os.environ['INET_IS_ARGO']

def enable_argo_inet():
    os.environ['INET_IS_ARGO'] = "1"
