# print under 100BTC list
# time interval: 1min -> 5min

import time
import pymysql
import datetime
from operator import itemgetter
from bittrex import Bittrex
import pymysql

# DB관련 변수
ip = 'localhost' #서버호스트주소
id = 'root' #DB이름
pw = 'autoset' #DB비번
name = 'bittrex'
chs ='utf8'
LOG_ID = "12.15테스트"
#---DB연결
conn = pymysql.connect(ip,id,pw,name,charset="utf8")
curs = conn.cursor()
sql_example = """insert into lsy_parsinglog(id,log)
                   values (%s, %s)"""
sql_bitcoin = """insert into lsy_bitcoin(stock,buy,sell,time) values (%s,%s,%s,%s)"""

# used api version -> version 2
# API_V2_0 = 'v2.0'
bit_API = Bittrex(None, None)

# reference for trading volume(buy + sell)
btc_refer = 1000


# return marketName's history result
def get_market_history(MarketName):
    # can edit bit_API.get_market_history()
    res = bit_API.get_market_history(MarketName)
    success = res["success"]
    if success:
        return res["result"]
    else:
        print("No History. Please Wait..")
        return None

# make string to datetime (+9 hours)
def make_datetime(timestamp):
    timestamp = timestamp.split('.')[0]
    date_time = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
    date_time = date_time.replace(second=0) + datetime.timedelta(hours=9)
    #date_time = date_time + datetime.timedelta(hours=9)
    return date_time

# check target market - a stock that base volume under 100 BTC in 24 hours
def check_target_market():
    target_market_list = []
    for tmp in bit_API.get_market_summaries()['result']:
        if  tmp['BaseVolume'] < btc_refer:
            if tmp['MarketName'].find('BTC-') != -1:
                # print(tmp['MarketName'], tmp['BaseVolume'])       # for checking
                target_market_list.append(tmp['MarketName'])

    return target_market_list

# check target_market's 1min tics
# at first: last_time = program start time
def check_buy_n_sell(market_name, last_time):
    # last_time: datetime, market_name: string
    histories = get_market_history(market_name)
    default_time = make_datetime('1970-01-01T12:00:00')
    before_check_time = default_time
    if not histories == None:
        # sorting histories by time
        histories = sorted(histories, key=itemgetter('TimeStamp'))
        print(market_name)          # for test
        buy = 0.0
        sell = 0.0
        print("Check")
        for history in histories:
            current_time = make_datetime(history["TimeStamp"])
            try:
                if current_time > last_time:
                    if before_check_time == current_time:
                        # sum
                        if history["OrderType"] == "BUY":
                            buy += history["Total"]
                        else:
                            sell += history["Total"]

                        # if last, print sum and return last_time
                        if history == histories[-1]:
                            curs.execute(sql_bitcoin, (market_name,buy,sell,before_check_time))
                            conn.commit()
                            print(before_check_time)
                            if buy == 0 and sell == 0:
                                print("0 %% (%.2f / %.2f)" % (buy, buy + sell))
                            else:
                                print("%.2f %% (%.2f / %.2f)" % ((buy / (buy + sell)) * 100, buy, buy + sell))
                            print("BUY: ", buy)
                            print("SELL: ", sell)

                            last_time = before_check_time
                            return last_time

                    elif before_check_time < current_time:
                        # print and renew sum data  -> for test (insert to DB)
                        if before_check_time != default_time:
                            curs.execute(sql_bitcoin, (market_name, buy, sell, before_check_time))
                            conn.commit()
                            print(before_check_time)
                            if buy == 0 and sell == 0:
                                print("0 %% (%.2f / %.2f)" % (buy, buy + sell))
                            else:
                                print("%.2f %% (%.2f / %.2f)" % ((buy / (buy + sell)) * 100, buy, buy + sell))
                            print("BUY: ", buy)
                            print("SELL: ", sell)
                            last_time = before_check_time

                            # clear buy and sell sum
                            buy = 0.0
                            sell = 0.0

                        if history["OrderType"] == "BUY":
                            buy += history["Total"]
                        else:
                           sell += history["Total"]

                    before_check_time = current_time

            except:
                print("No Time. Please Wait..")
                pass

        return last_time

SEC_TO_MINUTE = 60
if __name__ =="__main__":
    # get current time and insert to DB
    now = datetime.datetime.now()
    curs.execute(sql_example, (LOG_ID,now))
    conn.commit()

    target_markets = check_target_market()
    time_dic = {}
    # set time_dic 'now'
    for market in target_markets:
        time_dic[market] = now

    while True:
        for market in target_markets:
            new_time = check_buy_n_sell(market, time_dic[market])
            time_dic[market] = new_time
            #print(time_dic[market])
        time.sleep(0.5)
