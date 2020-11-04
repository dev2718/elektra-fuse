from  pathlib import Path
import os
import kdb

#translates from filesystem paths to elektra paths (e.g. '/user/dir/@elektra.value' -> 'user/dir') 
dir_file_special_name = "@elektra.value"
def os_path_to_elektra_path(os_path):
    if Path(os_path).name == dir_file_special_name:
        return str(Path(os_path).parent).strip("/")
    else:
        return os_path.strip("/") #remove slashes ('/' is reserved for the cascading namespace)
    

def size_of_file(os_path):
    return len(file_contents(os_path))

def is_directory_empty(os_path):
    dirs, files = ls(os_path)
    return not bool(dirs) and not bool(files)
    

def update_key_value(os_path: str, new_value: bytes):
    # kdb.kdb.KDBException, may be thrown
    # validation => whole key needs to be written at once

    with kdb.KDB() as db:
        path = os_path_to_elektra_path(os_path)

        ks = kdb.KeySet()
        db.get(ks, path)
        key = ks[path]


        #try to save new_value as UTF-8 string in case it can be decoded as such
        #TODO: manage 'binary' meta-key
        try:
            new_value_as_string = new_value.decode(encoding="utf-8", errors="strict")
            key.value = new_value_as_string
        except UnicodeDecodeError:
            key.value = new_value

        db.set(ks, path) #using key instead of path here deleted the key


#unexpected behavior, this deletes child keys too (why?)
def delete_key(os_path):
    with kdb.KDB() as db:
        path = os_path_to_elektra_path(os_path)

        ks = kdb.KeySet()
        db.get(ks, path)
        key = ks[path]

        ks.cut(key)
        db.set(ks, path)

#may throw KeyError
def file_contents(os_path):
    key, _ = get_key_and_keyset(os_path)

    if key.isString():
        return key.value.encode(encoding='UTF-8') #return bytes in all cases
    elif key.isBinary():
        return key.value
    else:
        raise Error("Unsupported key type")

#creates key, or, if key already exists, does nothing
def create_key(os_path):
    path = os_path_to_elektra_path(os_path)
    with kdb.KDB() as db:
        ks = kdb.KeySet()
        db.get(ks, path)
        if not path in ks:
            key = kdb.Key(path)
            ks.append(key)
        db.set(ks, path)

def get_meta_map(os_path):
    key, _ = get_key_and_keyset(os_path)
    return { meta.name:meta.value for meta in key.getMeta() }

def has_meta(os_path, name):
    try:
        meta_map = get_meta_map(os_path)
        return name in get_meta_map(os_path)
    except KeyError:
        return False
    
#get_meta, set_meta may throw KeyError
def get_meta(os_path, name):
    return get_meta_map(os_path)[name]

def set_meta(os_path, name, value):
    meta_map = get_meta_map(os_path)
    meta_map[name] = value
    update_meta_map(os_path, meta_map)

def update_meta_map(os_path, new_meta_map):
    path = os_path_to_elektra_path(os_path)

    with kdb.KDB() as db:
        ks = kdb.KeySet()
        db.get(ks, path)
        key = ks[path]

        #delete old meta keys
        for meta_key in key.getMeta():
            key.delMeta(meta_key.name)
        
        #insert new meta keys
        for keyname in new_meta_map.keys():
            key.setMeta(keyname, new_meta_map[keyname])

        db.set(ks, path)

#may throw KeyError
def get_key_and_keyset(os_path):
    path = os_path_to_elektra_path(os_path)

    with kdb.KDB() as db:
        ks = kdb.KeySet()
        db.get(ks, path)
        key = ks[path]
        return (key, ks)

def key_type(os_path):
    if os_path in [".", "..", "/", "/user", "/system"]:
        return (True, False)

    dirs, files = ls(os_path)

    return (bool(dirs), bool(files))

def is_dir(os_path):
    dirs, _ = ls(os_path)
    return bool(dirs)

def is_list_prefix(prefix, list_):
    if len(prefix) > len(list_):
        return False
    
    for (i, item) in enumerate(prefix):
            if list_[i] != item:
                return False
    return True

def is_path_prefix(prefix, path):
    return is_list_prefix(prefix.split("/"), path.split("/"))

def ls(os_path):
    if os_path == "/":
        return ({"user", "system"}, [])

    path = os_path_to_elektra_path(os_path)

    with kdb.KDB() as db:
        ks = kdb.KeySet()
        db.get(ks, path)

        below = {name.split(path)[1] for name in ks.unpack_names() if is_path_prefix(path, name)}
        
        dirs = {name.split("/")[1] for name in below if "/" in name}
        files = {name for name in below if not "/" in name}

        if '' in files:
            files.remove('')
            files.add(dir_file_special_name)

        return (dirs, files)