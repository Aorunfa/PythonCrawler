'''
coding:utf-8
@Software: PyCharm
@Time: 2024/1/4 0:24
@Author: Aocf
@versionl: 3.
'''
import pandas as pd
import pymysql
from sqlalchemy import create_engine


class SqlUtils(object):
    """
    实现数据库的增删查改操作
    """

    def __init__(self, config, dtype_dict=None):
        self.engine = create_engine(self._config_parse(**config))

        if dtype_dict is None:
            self.dtype_dict = {'object': 'VARCHAR(20)',
                               'int64': 'INT',
                               'int32': 'INT',
                               'int16': 'SMALLINT',
                               'float16': 'NUMERIC(10, 4)',  # 整数10位 小数2位
                               'float32': 'NUMERIC(10, 4)',
                               'float64': 'NUMERIC(10, 4)',
                               'datetime64[ns]': 'DATETIME',
                               'bool': 'BOOLEAN',
                              }
        else:
            self.dtype_dict = dtype_dict

    def _config_parse(self, user, passwd, localhost, database):
        return rf"mysql+pymysql://{user}:{passwd}@{localhost}/{database}"

    def _datatype_parse(self, df: pd.DataFrame, text_col=None):
        """
        解析dataframe每一列对应的sql数据类型
        :param df:
        :return:
        """
        datatype_dict = dict(zip(df.columns, [self.dtype_dict[str(x)] for x in df.dtypes]))
        if text_col is not None:
            if isinstance(text_col, list):
                for col in text_col:
                    datatype_dict[col] = 'TEXT'
            else:
                datatype_dict[text_col] = 'TEXT'
        return datatype_dict

    def creat_table(self, table_name: str, df: pd.DataFrame, text_col=None, pkeys=None,
                    ukeys=None, idxs=None, pid=None, pnums=4, fixed_drop=True):
        """
        自动检索pd.Dataframe数据列与格式创建表格
        分区按照范围分区
        """
        datatype_dict = self._datatype_parse(df, text_col)
        sql_datatype, sql_key, sql_idx, sql_ukey, sql_partition = '', '', '', '', ''
        # data type
        for col, dtype in datatype_dict.items():
            sql_datatype += f'{col} {dtype},'
        sql_col_datatype = sql_datatype[:-1]
        # primary key
        if pkeys is not None:
            if isinstance(pkeys, list):
                sql_key = f', PRIMARY KEY (%s)' % str(pkeys)[1:-1].replace("'", '')
            else:
                sql_key = f', PRIMARY KEY ({pkeys})'
        # index
        if idxs is not None:
            if isinstance(idxs, list):
                sql_idx = f', INDEX (%s)' % str(idxs)[1:-1].replace("'", '')
            else:
                sql_idx = f', INDEX ({idxs})'
        # unique key
        if ukeys is not None:
            if isinstance(ukeys, list):
                sql_ukey = f', UNIQUE KEY (%s)' % str(ukeys)[1:-1].replace("'", '')
            else:
                sql_ukey = f',  UNIQUE KEY ({ukeys})'

        # 分区键必须出现在键里面(主键，若有)
        if pid is not None:
            if pkeys is not None:
                assert pid in pkeys or pid in [pkeys], '分区字段不在键字段中 请检查'
            sql_partition = f'PARTITION by HASH ({pid}) partitions {pnums}'

        sql = f'CREATE TABLE {table_name} ({sql_col_datatype}{sql_key}{sql_ukey}{sql_idx}){sql_partition}'

        # run
        if not self.find_table(table_name):
            self.run_sql(sql)
        elif fixed_drop:
            self.del_table(table_name)
            self.run_sql(sql)

    def put_data(self, df: pd.DataFrame, table_name, mode='append'):
        """
        将dataframe上传至数据库
        :param df:
        :param table_name:
        :param mode: append or replace
        :return:
        """


        df.to_sql(name=table_name,
                  con=self.engine,
                  if_exists=mode,
                  index=False)

    def get_data(self, sql: str):
        """
        查询表格返回dataframe
        :param sql: 查询语句
        :return:
        """
        return pd.read_sql_query(sql, self.con)

    def del_table(self, table_name):
        self.run_sql(f'DROP TABLE {table_name}')

    def find_table(self, table_name):
        sql = f"SHOW TABLES LIKE '{table_name}'"
        return self.run_sql(sql)

    def run_sql(self, sql):
        try:
            rstl = self.engine.execute(sql)

            return rstl
        except Exception as e:
            print(f'sql语句运行失败, sql={sql}')
            print(e)
            # 回滚
            # self.con.rollback()
            return None

    def __del__(self):
        """
        关闭游标和连接
        :return:
        """
        self.cursor.close()
        self.con.close()

if __name__ == '__main__':
    config = {
            "host": "localhost",
            "port": 3306,
            "database": "aocf",
            "charset": "utf8",
            "user": "root",
            "passwd": "w0haizai"
        }
    mysql = SqlUtils(config)
    # 建表
    d = {'name':'aocf',
         'age': 23,
         'w': 175.1,
         'p': 'fsegsgzsjsfsfasefearfiufhuSHuishyuifgrygubvubv',
         'timestamp': pd.to_datetime('2023-02-04').timestamp(),
         'date': pd.to_datetime('2023-02-04'),
         'good': True,
         'bit': 1}
    df = pd.DataFrame(d, index=[0])
    # mysql.creat_table(table_name='test',
    #                   df=df,
    #                   text_col=['p'], pkeys=['name', 'bit'], ukeys=['good', 'bit'],
    #                   idxs=['w', 'timestamp'], pid='bit')
    # 写入
    mysql.put_data(df, 'test', mode='replace')
    # 查询
    # r'mysql+pymysql://root:w0haizai@localhost/aocf'
    # 删除