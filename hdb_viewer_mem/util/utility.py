import os
import numpy as np
import shutil


def config_ini_key_value(keys, config_file):
    ret_map = dict()
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            for line in f.readlines():
                if line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                config_key = line.split("=")[0].strip()
                if len(keys) > 0:
                    if config_key not in keys:
                        continue
                config_value = line.split("=")[1].strip()
                ret_map[config_key] = config_value
    except FileNotFoundError:
        raise FileNotFoundError

    return ret_map


def config_ini_set(key_map, config_file):
    config_values = []
    with open(config_file, "r", encoding="utf-8") as f:
        for line in f.readlines():
            if line.startswith("#"):
                config_values.append(line)
                continue
            config_key = line.split("=")[0].strip()
            if config_key not in key_map:
                config_values.append(line)
                continue
            config_value = key_map[config_key]
            new_line = "%s=%s\n" % (config_key, config_value)
            config_values.append(new_line)

    with open(config_file, "w", encoding="utf-8") as f:
        f.write("".join(config_values))


def mk_file(file):
    if os.path.exists(file):
        return
    with open(file, "w"):
        pass


def rm_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)


def copy_dir(src_path, dst_path):
    """
    recursive copy files in src path to dst path.
    the dst path must not exist, else it will be rm first
    :param src_path:
    :param dst_path:
    :return:
    """
    if os.path.exists(dst_path):
        rm_dir(dst_path)
    shutil.copytree(src_path, dst_path)


def copy_file(src_file, dst_file):
    shutil.copy(src_file, dst_file)


def list_dirs(path):
    if not os.path.exists(path):
        return []
    return [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]


def list_files(path):
    if not os.path.exists(path):
        return []
    return [x for x in os.listdir(path) if os.path.isfile(os.path.join(path, x))]


def mk_dir(path):
    if os.path.exists(path):
        return
    os.makedirs(path)


if __name__ == '__main__':
    config_file = r"C:\Temp\strategy.ini"
    configs = {"bt_start_time": "2019-07-02 09:10:00",
               "bt_end_time": "2019-07-02 16:10:00"}

