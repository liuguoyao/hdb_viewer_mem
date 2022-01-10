import numpy as np
import pandas as pd
import pickle
import os

def read_item_last(filename,index_symbol):
    if not os.path.exists(filename) or not os.path.getsize(filename) > 0:
        return None
    # read file last item
    mm_header = np.memmap(filename, dtype=np.uint32, mode='r', shape=(1, 2), offset=0)
    curpos, dtypelen = mm_header[0][0], mm_header[0][1]
    if 0 == curpos:
        return None
    mm_dtype = np.memmap(filename, dtype=np.byte, mode='r', shape=(dtypelen,), offset=8)
    itemdtypes_descr = pickle.loads(mm_dtype)
    itemdtypes = np.dtype(itemdtypes_descr)
    mm_item = np.memmap(filename, dtype=itemdtypes, mode='r', shape=(1, 1),
                        offset=8 + dtypelen + (curpos - 1) * itemdtypes.itemsize)
    itemdf = pd.DataFrame([pd.Series(list(mm_item[0][0]), index=itemdtypes.names)], index=[index_symbol])
    return itemdf

def append_item(filename,item):
    mm_header = np.memmap(filename, dtype=np.uint32, mode='r+', shape=(1, 2), offset=0)
    curpos, dtypelen = mm_header[0][0], mm_header[0][1]
    if 0 == curpos:
        typesbytes = pickle.dumps(item.total_dtypes.descr)
        # p = pickle.loads(typesbytes)
        mm_header[0][1] = len(typesbytes)
        dtypelen = len(typesbytes)
        mm = np.memmap(filename, dtype=np.byte, mode='r+', shape=(len(typesbytes),), offset=8)
        for ind, v in enumerate(typesbytes):
            mm[ind] = v

    mm = np.memmap(filename, dtype=item.total_dtypes, mode='r+', shape=(1,),
                   offset=8 + dtypelen + curpos * item.total_dtypes.itemsize)
    mm[0] = item.total_array_data[0]
    # mm.flush()

    mm_header[0][0] = curpos + 1