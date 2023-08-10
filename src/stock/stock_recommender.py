import baostock as bs
import pandas as pd
from path import Path
from datetime import datetime, timedelta
import pytz
import json
import numpy as np
from .generate_html import app, app_setup
from multiprocessing import Process

tmp_dir = Path(__file__).parent.parent / 'tmp'
tmp_dir.makedirs_p()
data_dir = Path(__file__).parent.parent / 'data'
data_dir.makedirs_p()
margin_ratio = 0.2


def write_json(dict, json_path):
    with open(json_path, 'w') as js:
        json.dump(dict, js)


def get_dict_from_rs(rs):
    result_list = []
    while (rs.error_code == '0') & rs.next():
        # 分页查询，将每页信息合并在一起
        result_list.append(rs.get_row_data())
    result = pd.DataFrame(result_list, columns=rs.fields)
    dic = {}
    for field in rs.fields:
        dic[field] = result[field][-1:].values[0]
    return dic


def load_json(json_file):
    with open(json_file, 'r') as js:
        dic = json.load(js)
    return dic


class Stock:
    def __init__(self, code, name):
        self.code = code
        self.name = name
        self.stock_info = {}
        self.create_stock_dir()
        self.history_k = None
        self.profit = None

    def create_stock_dir(self):
        stock_dir = data_dir / self.code
        stock_dir.makedirs_p()
        self.stock_dir = stock_dir

    def create_stock_quarter_dir(self):
        year = last_q['year']
        quarter = last_q['quarter']
        self.season = last_q
        stock_quarter_dir = self.stock_dir / f"{year}-Q{quarter}"
        stock_quarter_dir.makedirs_p()
        self.stock_quarter_dir = stock_quarter_dir

    def get_quarter_data(self):
        self.create_stock_quarter_dir()
        self.get_profit_data()
        self.get_growth_data()
        self.get_operation_data()
        self.get_stock_industry()

    def get_history_k(self):
        preps = 'history_k'
        stock_code = self.code
        json_path = self.stock_dir / f'{preps}_{last_date}.json'
        fields = ["date", "code", "open", "high", "low", "close", "volume", "amount", "adjustflag", "peTTM", "psTTM",
                  "pbMRQ", "pcfNcfTTM", "isST"]
        if not json_path.exists():
            fields_str = ''
            for field in fields:
                fields_str += field
                fields_str += ','
            rs = bs.query_history_k_data(f"{stock_code}", fields_str[:-1],
                                         # "date,code,open,high,low,close,volume,amount,adjustflag,peTTM, psTTM, pbMRQ, pcfNcfTTM, isST",
                                         start_date='2020-01-01',
                                         end_date=f'{last_date}',
                                         frequency="d", adjustflag="3")
            print(rs.error_code)
            print(rs.error_msg)
            # 获取具体的信息
            dict = get_dict_from_rs(rs)
            write_json(dict, json_path)
        self.history_k = load_json(json_path)

    def get_profit_data(self):
        code = self.code
        preps = 'profit'
        json_path = self.stock_quarter_dir / f'{preps}.json'
        if not json_path.exists():
            rs = bs.query_profit_data(code=code, year=self.season['year'], quarter=self.season['quarter'])
            dic = get_dict_from_rs(rs)
            write_json(dic, json_path)
        self.profit = load_json(json_path)

    def get_operation_data(self):
        code = self.code
        preps = 'operation'
        json_path = self.stock_quarter_dir / f'{preps}.json'
        if not json_path.exists():
            rs = bs.query_operation_data(code=code, year=self.season['year'], quarter=self.season['quarter'])
            dic = get_dict_from_rs(rs)
            write_json(dic, json_path)
        self.operation = load_json(json_path)

    def get_balance_data(self):
        code = self.code
        preps = 'balance'
        json_path = self.stock_quarter_dir / f'{preps}.json'
        if not json_path.exists():
            rs = bs.query_balance_data(code=code, year=self.season['year'], quarter=self.season['quarter'])
            dic = get_dict_from_rs(rs)
            write_json(dic, json_path)
        self.balance = load_json(json_path)

    # def get_performance_express_report(self):
    #     code = self.code
    #     rs = bs.query_performance_express_report(code, start_date="2023-01-01", end_date=last_date)
    #     result_list = []
    #     while (rs.error_code == '0') & rs.next():
    #         result_list.append(rs.get_row_data())
    #     result_list = pd.DataFrame(result_list, columns=rs.fields)
    #     for field in rs.fields:
    #         self.stock_info[field] = result_list[field][-1:].values[0]

    def get_growth_data(self):
        code = self.code
        preps = 'growth'
        json_path = self.stock_quarter_dir / f'{preps}.json'
        if not json_path.exists():
            rs = bs.query_growth_data(code=code, year=self.season['year'], quarter=self.season['quarter'])
            dic = get_dict_from_rs(rs)
            write_json(dic, json_path)
        self.growth = load_json(json_path)

    def get_stock_industry(self):
        code = self.code
        preps = 'industry'
        json_path = self.stock_quarter_dir / f'{preps}.json'
        if not json_path.exists():
            rs = bs.query_stock_industry(code=code)
            dic = get_dict_from_rs(rs)
            write_json(dic, json_path)
        self.industry = load_json(json_path)

    def cal_safe_margin(self, method='weight'):
        self.margin = {}
        self.safe_margin = {}
        reasonable_price = None
        safe_margin_dict = {}
        self._evaluate_NetAsset()
        self._evaluate_Earnings()
        self._evaluate_PriceToSales()

        if method == 'weight':
            reasonable_price = self._cal_safe_margin_weight()
        elif method == 'middle':
            reasonable_price = self._cal_safe_margin_middle()

        current_price = float(self.history_k['close'])
        safe_margin_dict['current_price'] = current_price
        safe_margin_dict['reasonable_price'] = reasonable_price
        safe_margin_dict['buy_price'] = (1 - margin_ratio) * reasonable_price
        safe_margin_dict['sell_price'] = (1 + margin_ratio) * reasonable_price
        safe_margin_dict['buy_price_flag'] = current_price < safe_margin_dict['buy_price']
        safe_margin_dict['sell_price_flag'] = current_price > safe_margin_dict['sell_price']
        safe_margin_dict['safe_margin'] = reasonable_price - current_price
        safe_margin_dict['safe_margin_ratio'] = (reasonable_price - current_price) / current_price

        safe_margin_dict['NetAsset'] = self.margin['NetAsset']
        safe_margin_dict['Earnings'] = self.margin['Earnings']
        safe_margin_dict['PriceToSales'] = self.margin['PriceToSales']
        self.safe_margin[method] = safe_margin_dict
        # return safe_margin_dict

    def _cal_safe_margin_weight(self):
        values = [value for key, value in self.margin.items()]
        reasonable_price = np.sum(values) / len(values)
        return reasonable_price

    def _cal_safe_margin_middle(self):
        values = [value for key, value in self.margin.items()]
        reasonable_price = (np.sum(values) - max(values) - min(values)) / (len(values) - 2)
        return reasonable_price

    def _evaluate_NetAsset(self):
        '''
        净资产法 = {当前价格}/{市净率}
        :return:
        '''
        try:
            safe_margin = float(self.history_k['close']) / float(self.history_k['pbMRQ'])
            self.margin['NetAsset'] = safe_margin
        except Exception:
            pass

    def _evaluate_Earnings(self):
        '''
        盈余法 = {季度总利润}*4/{总股本}
        :return:
        '''
        try:
            safe_margin = float(self.profit['netProfit']) * 4 / float(self.profit['totalShare'])
            # * float(self.stock_info['peTTM'])
            self.margin['Earnings'] = safe_margin
        except Exception:
            pass

    def _evaluate_PriceToSales(self):
        '''
        市销率法 = {净利润}/{销售净利率}*4*{市销率}/{总股本}
        :return:
        '''
        try:
            safe_margin = float(self.profit['netProfit']) / float(self.profit['npMargin']) * 4 * float(
                self.history_k['psTTM']) / float(self.profit['totalShare'])
            self.margin['PriceToSales'] = safe_margin
        except Exception:
            pass


def get_last_date(timezone='Asia/Shanghai'):
    # 创建一个北京时区对象
    beijing_tz = pytz.timezone(timezone)

    # 获取当前的日期和时间（UTC）
    now_utc = datetime.now(pytz.utc)

    # 将当前的日期和时间转换为北京时区
    now_beijing = now_utc.astimezone(beijing_tz)

    if now_beijing.hour < 10:
        now_beijing = now_beijing - timedelta(days=1)

    # 输出日期，格式为YYYY-MM-DD
    print(now_beijing.strftime('%Y-%m-%d'))
    return now_beijing, now_beijing.strftime('%Y-%m-%d')


class QuerySystem:
    def __init__(self):
        pass

    def login(self):
        # 登陆系统
        lg = bs.login()
        # 显示登陆返回信息
        print(lg.error_code)
        print(lg.error_msg)

    def timeset(self):
        global last_date_obj, last_date
        global last_q
        last_date_obj, last_date = get_last_date()
        last_q = {}
        last_q['year'] = last_date_obj.year
        last_q['quarter'] = 1

    def logout(self):
        # 登出系统
        bs.logout()


class StockRecommender:
    def __init__(self, cluster):
        self.stock_list = None
        self.cluster = cluster
        self.stocks = []

    def data_loader(self):
        self.get_stocks_list()
        for _, stock_code, stock_name in self.stock_list.data:
            print('读取数据中：', stock_name)
            try:
                stock = Stock(stock_code, stock_name)
                stock.get_history_k()
                stock.get_quarter_data()
                stock.get_stock_industry()
                self.stocks.append(stock)
            except Exception as e:
                pass

    def analyse(self):
        for stock in self.stocks:
            stock.cal_safe_margin()

    def report(self):

        df = self.report_by_stock()
        self.report_by_industry()
        return df

    def report_by_stock(self):
        stocks = self.stocks
        index_list = ['current_price',
                      'reasonable_price',
                      'NetAsset',
                      'Earnings',
                      'PriceToSales',
                      'buy_price',
                      'sell_price',
                      'buy_price_flag',
                      'sell_price_flag',
                      'safe_margin',
                      'safe_margin_ratio',
                      ]
        index_name = ['当前价格',
                      '合理价值',
                      '净资产法',
                      '盈余法',
                      '市销率法',
                      '可买价',
                      '可卖价',
                      '买入时机',
                      '卖出时机',
                      '安全边际',
                      '安全边际率',
                      ]
        for method in [
            'weight',
            # 'middle',
        ]:
            b = []
            for stock in stocks:
                a = [stock.code, stock.name]
                for info in index_list:
                    item = stock.safe_margin[method][info]
                    if info in ['current_price',
                                'reasonable_price',
                                'NetAsset',
                                'Earnings',
                                'PriceToSales',
                                'buy_price',
                                'sell_price',
                                'safe_margin',
                                'safe_margin_ratio']:
                        item = np.around(float(item), decimals=2)
                    a.append(item)
                b.append(a)
            csv_path = tmp_dir / f'stock-recommmender-{last_date}-{method}.csv'
            columns = ['Stock Code', 'Stock Name', ] + index_name
            b = pd.DataFrame(b, columns=columns)

            b.to_csv(csv_path, encoding="gbk", index=False)
            df = pd.DataFrame(b, columns=columns)
            return df

    def report_by_industry(self):
        stocks = self.stocks
        industries = [stock.industry['industry'] for stock in stocks]
        industries = np.unique(industries)

        for industry in industries:
            indu_dir = tmp_dir / industry
            indu_dir.makedirs_p()
            index_list = ['current_price',
                          'reasonable_price',
                          'NetAsset',
                          'Earnings',
                          'PriceToSales',
                          'buy_price',
                          'sell_price',
                          'buy_price_flag',
                          'sell_price_flag',
                          'safe_margin',
                          'safe_margin_ratio',
                          ]
            for method in [
                'weight',
            ]:
                b = []
                for stock in stocks:
                    if stock.industry['industry'] != industry:
                        continue
                    a = [stock.name, stock.code, ]
                    for info in index_list:
                        a.append(stock.safe_margin[method][info])
                    b.append(a)
                csv_path = indu_dir / f'stock-recommmender-{last_date}-{method}-{industry}.csv'
                columns = [0, 0, ] + index_list
                b = pd.DataFrame(b, columns=columns)
                b.to_csv(csv_path, encoding="gbk", index=False)

    def get_stocks_list(self):
        cluster = self.cluster
        if cluster == 'sz':
            rs = bs.query_sz50_stocks(last_date)
        elif cluster == 'hs300':
            rs = bs.query_hs300_stocks(last_date)
        elif cluster == '':
            rs = bs.query_zz500_stocks(last_date)
        else:
            pass
        self.stock_list = rs


def main(cluster='hs300'):
    system = QuerySystem()
    system.timeset()
    system.login()

    # Stock Recommander Analyse
    sr = StockRecommender(cluster)
    sr.data_loader()
    sr.analyse()
    df = sr.report()

    system.logout()
    app_setup(df)
    app.run_server(debug=True)


if __name__ == '__main__':
    cluster = 'hs300'
    main(cluster)
