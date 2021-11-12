
# from PyQt5.QtWidgets import QApplication
# from .FetchData_Background_decorator import *

class Getdata_Mediator():
    @staticmethod
    def loadNothing( **kargs):
        return [1,2,3]

    # @staticmethod
    # def tab1_benchmark(symbol, begin_date, end_date, **kargs):
    #     try:
    #         ticks = get_security_kdata([symbol], begin_date, end_date, "1day", "before")
    #         return (ticks['close'] * 100.0 / ticks.at[0, 'open'] - 100.0).tolist()
    #     except Exception as e:
    #         print("Err:", e)
    #         print(traceback.format_exc())
    #         return []

getdata_mediator = Getdata_Mediator()

