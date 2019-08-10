from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 连接数据库
db_engine = create_engine("mysql+pymysql://yanglin:123456@localhost:3306/music_db?charset=utf8mb4")

# 创建会话对象，用于数据表的操作
db_session = sessionmaker(bind=db_engine)
sql_session = db_session()
Base = declarative_base()


# 映射数据表
class Song(Base):
    # 表名
    __tablename__ = 'song'
    # 字段、属性
    song_id = Column(Integer, primary_key=True)
    song_name = Column(String(50))
    song_album = Column(String(100))
    song_interval = Column(String(25))
    song_songmid = Column(String(25))
    song_singer = Column(String(50))


# 创建数据表
Base.metadata.create_all(db_engine)


# 定义函数insert_data
def insert_data(song_dict):
    # 连接数据库
    db_engine_ = create_engine("mysql+pymysql://yanglin:123456@localhost:3306/music_db?charset=utf8")
    # 创建绘会话对象，用于操作数据库
    db_session_ = sessionmaker(bind=db_engine_)
    sql_session_ = db_session_()
    data = Song(
        song_name=song_dict['song_name'],
        song_album=song_dict['song_album'],
        song_interval=song_dict['song_interval'],
        song_songmid=song_dict['song_songmid'],
        song_singer=song_dict['song_singer'],
    )
    sql_session_.add(data)
    sql_session_.commit()
