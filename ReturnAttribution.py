"""
Author: Xin Yang
Date: June 09 2022
The following is the implementation for the Brinson Model which discuss how to evaluate the return attribution.

There are three kinds of measure approaches for the Brinson Model:
1. Return-based attribution, -> 基于收益
2. Holding-based attribution, -> 基于持仓
3. Transations-based attribution. -> 基于交易

The correctness for the performance is 3 < 2 < 1. However, for most funds, the holdings will only release completely on the second season
and the final season of the year, therefore we decide to use the first approach as measurement.

Details of model:
Brison, Hood, Beeboower "Determinantes of Portfolio Performance" 1986 ; BHB Model
Brison, Fachler "Measuring Non-US Equity Portfolio Performance" 1985, BF Model

API： AKShare
"""
import akshare as ak
import pandas as pd
import datetime
import os

'''
We need to manually insert the benchmark. In here, for 002983 长信军工量化混合, the benchmark is:
1. 申万国防军工指数 801740 权重： 60%
2. 中证综合债指数 H11009 权重： 40%
according to the annual report
'''
benchmark = dict()
benchmark[0] = ['801740',0.6]
benchmark[1] = ['H11009',0.4]

#We use the 2021Q4 as example here.
#Startdate: 20210931 ; enddate: 20211231; time: 2021; fund_num: 002983
def select_the_fund(fund_num: str,time: str,startdate: str, enddate: str) -> pd.DataFrame:
    '''
    This method is to firstly get the return rate and the weight of the fund and benchmark;
    :param fund_num: the index number of the fund, in here the number is 002983 长信军工量化混合
    :param time: the year for measurement
    :param startdate: the startdate of measurement
    :param enddate: the enddate of measurement
    :return: pd.Dataframe as the decomposition of return for benchmark and portfolio
    '''

    fund_portfolio_hold_em_df = ak.fund_portfolio_hold_em(symbol=fund_num, date=time)
    sw_index_daily_df = ak.sw_index_daily(symbol=benchmark[0][0],start_date=startdate, end_date=enddate)
    #stock_zh_index_hist_csindex_df = ak.stock_zh_index_hist_csindex(symbol=benchmark[1][0], start_date=startdate, end_date=enddate)
    stock_zh_index_hist_csindex_df = ak.index_zh_a_hist(symbol='000012', period="monthly", start_date=startdate, end_date=enddate)
    index_zh_a_hist_df = ak.index_zh_a_hist(symbol="000985",period = "monthly",start_date=startdate,end_date =enddate)

    #Step1: The benchmark return rate
    start_num = stock_zh_index_hist_csindex_df['收盘'][0]
    end_num = stock_zh_index_hist_csindex_df['收盘'][len(stock_zh_index_hist_csindex_df)-1]
    holding_return_rate = end_num / start_num -1
    benchmark[1].append(holding_return_rate)

    start_num = sw_index_daily_df['close'][len(sw_index_daily_df)-1]
    end_num = sw_index_daily_df['close'][0]
    holding_return_rate = end_num / start_num -1
    benchmark[0].append(holding_return_rate)

    start_num = index_zh_a_hist_df['收盘'][0]
    end_num = index_zh_a_hist_df['收盘'][len(index_zh_a_hist_df)-1]
    holding_return_rate = end_num / start_num -1

    #Step2: Check the weight of the fund
    fund_season_4 = fund_portfolio_hold_em_df[fund_portfolio_hold_em_df.季度.__eq__("2021年4季度股票投资明细")]

    sw_index_cons_df = ak.sw_index_cons(symbol=benchmark[0][0])
    list_of_index = sw_index_cons_df['stock_code'].to_list()

    fund_on_index = fund_portfolio_hold_em_df[fund_portfolio_hold_em_df.季度.__eq__("2021年4季度股票投资明细")][fund_portfolio_hold_em_df.股票代码.isin(sw_index_cons_df['stock_code'].to_list())]
    fund_not_on_index = fund_portfolio_hold_em_df[fund_portfolio_hold_em_df.季度.__eq__("2021年4季度股票投资明细")][fund_portfolio_hold_em_df.股票代码.isin(sw_index_cons_df['stock_code'].to_list())==False]

    #Step3: Check the return rate of for industry as allocation
    return_rate_on_index = None
    return_rate_not_on_index = None

    def helping_function(fund_on_index: str) -> float:
        '''
        This method is to calculate the return rate in portfolio
        :param fund_on_index:
        :return: return rate
        '''
        name = fund_on_index['股票代码'].tolist()
        proportion = fund_on_index['占净值比例'].tolist()
        portfolio_return_rate = 0
        for each in range(0, len(name)):
            stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol=name[each], period="monthly", start_date=startdate, end_date=enddate, adjust="qfq")
            try:
                return_rate = (stock_zh_a_hist_df['收盘'][len(stock_zh_a_hist_df)-1] - stock_zh_a_hist_df['收盘'][0])/ stock_zh_a_hist_df['收盘'][0]
                portfolio_return_rate += proportion[each] * 0.01 * return_rate
            except:
                continue
        portfolio_return_rate = portfolio_return_rate / (sum(proportion) * 0.01)

        return portfolio_return_rate

    return_rate_on_index = helping_function(fund_on_index)
    return_rate_not_on_index = helping_function(fund_not_on_index)
    proportion_on_index = sum(fund_on_index['占净值比例'].tolist()) * 0.01
    proportion_not_on_index = sum(fund_not_on_index['占净值比例'].tolist()) * 0.01
    proportion_on_currency = 1 - proportion_not_on_index - proportion_on_index
    output = dict()
    output['行业'] = ['军工行业','其他行业','货币基金']
    output['组合权重'] = [proportion_on_index,proportion_not_on_index,proportion_on_currency]
    output['基准权重'] = [benchmark[0][1],0,benchmark[1][1]]
    output['组合收益'] = [return_rate_on_index,return_rate_not_on_index,benchmark[1][2]]
    output['基准收益'] = [benchmark[0][2],holding_return_rate,benchmark[1][2]]
    df_output = pd.DataFrame(output)
    print(df_output)
    if 'Return-Decomposition-Output' not in os.listdir():
        os.makedirs("Return-Decomposition-Output")
    df_output.to_csv("Return-Decomposition-Output/" + fund_num + "-Decomposition.csv")
    return df_output

def BHB_Model_Analysis(df_output:pd.DataFrame,fund_num: str) -> pd.DataFrame:
    '''
    The input is of the decomposition about the return and weight between portfolio and benchmark after the analysis from the raw data
    We now do the BHB Model Analysis to get three conclusions:
    1. Excess return from allocation effect;
    2. Excess return from securities selection;
    3. Excess return from interaction effect;
    :param df_output: The input of the dataframe after return rate decomposition
    :return: the pd.dataframe about the result of BHB model
    '''

    #Allocation Effect, Selection Effect, Interaction Effect
    AE = 0
    SE = 0
    IE = 0
    for each_row in df_output.iterrows():
        AE += (each_row[1]['组合权重'] - each_row[1]['基准权重']) * each_row[1]['基准收益']
        SE += (each_row[1]['组合权重']) * (each_row[1]['组合收益'] - each_row[1]['基准收益'])
        IE += (each_row[1]['组合权重'] - each_row[1]['基准权重']) * (each_row[1]['组合收益'] - each_row[1]['基准收益'])

    #To see the actual return rate of the fund
    fund_open_fund_info_em_df = ak.fund_open_fund_info_em(fund="002983", indicator="单位净值走势")
    b = datetime.date(2021,9,30)
    c = datetime.date(2021,12,31)
    start = fund_open_fund_info_em_df[fund_open_fund_info_em_df.净值日期.__eq__(b)]['单位净值'].item()
    close = fund_open_fund_info_em_df[fund_open_fund_info_em_df.净值日期.__eq__(c)]['单位净值'].item()
    return_rate = (close - start)  / start
    output = dict()
    output['配置效应'] = [AE]
    output['选股效应'] = [SE]
    output['交叉效应'] = [IE]
    output['误差'] = [return_rate - AE - SE - IE]
    output_df = pd.DataFrame(output)
    print(output_df)
    if 'BHB-Output' not in os.listdir():
        os.makedirs("BHB-Output")
    output_df.to_csv("BHB-Output/" + fund_num + "-BHBresult.csv")
    return output_df

def BF_Model_Analysis(df_output:pd.DataFrame,fund_num: str) -> pd.DataFrame:
    '''
    The input is of the decomposition about the return and weight between portfolio and benchmark after the analysis from the raw data
    We now do the BF Model Analysis to get three conclusions:
    1. Excess return from allocation effect;
    2. Excess return from securities selection;
    3. Excess return from interaction effect;
    :param df_output: The input of the dataframe after return rate decomposition
    :return: the pd.dataframe about the result of BF model
    '''

    #Allocation Effect, Selection Effect, Interaction Effect
    AE = 0
    SE = 0
    IE = 0
    for each_row in df_output.iterrows():
        AE += (each_row[1]['组合权重'] - each_row[1]['基准权重']) * (each_row[1]['基准收益'] - (benchmark[0][2] * benchmark[0][1] + benchmark[1][2] * benchmark[1][1]))
        SE += (each_row[1]['组合权重']) * (each_row[1]['组合收益'] - each_row[1]['基准收益'])
        IE += (each_row[1]['组合权重'] - each_row[1]['基准权重']) * (each_row[1]['组合收益'] - each_row[1]['基准收益'])

    #To see the actual return rate of the fund
    fund_open_fund_info_em_df = ak.fund_open_fund_info_em(fund="002983", indicator="单位净值走势")
    b = datetime.date(2021,9,30)
    c = datetime.date(2021,12,31)
    start = fund_open_fund_info_em_df[fund_open_fund_info_em_df.净值日期.__eq__(b)]['单位净值'].item()
    close = fund_open_fund_info_em_df[fund_open_fund_info_em_df.净值日期.__eq__(c)]['单位净值'].item()
    return_rate = (close - start)  / start
    output = dict()
    output['配置效应'] = [AE]
    output['选股效应'] = [SE]
    output['交叉效应'] = [IE]
    output['误差'] = [return_rate - AE - SE - IE]
    output_df = pd.DataFrame(output)
    print(output_df)
    if 'BF-Output' not in os.listdir():
        os.makedirs("BF-Output")
    output_df.to_csv("BF-Output/" + fund_num + "-BF_result.csv")
    return output_df



decomposition = select_the_fund("002983","2021","20210930","20211231")
BHB_Model_Analysis(decomposition,"002983")
BF_Model_Analysis(decomposition,"002983")

