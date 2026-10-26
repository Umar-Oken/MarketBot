from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import DeclarativeBase, declared_attr, sessionmaker

from config import settings


class Base(DeclarativeBase):
    @declared_attr
    def __tablename__(cls):
        table_name = cls.__name__.lower()
        return table_name + "s" if not table_name.endswith("y") else table_name[:-1] + "ies"

        # category -> categories


class Database:
    def __init__(self):
        self._engine = None
        self._session = None

    def init(self):
        self._engine = create_engine(settings.postgresql_url())
        self._session = sessionmaker(self._engine, expire_on_commit=False)()

    def __getattr__(self, item):
        return getattr(self._session, item)

    def create_all(self):
        Base.metadata.create_all(self._engine)

    def drop_all(self):
        Base.metadata.drop_all(self._engine)


db = Database()
db.init()


class AbstractClass:
    @classmethod
    def commit(cls):
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    # CREATE
    @classmethod
    def create(cls, **kwargs):
        _obj = cls(**kwargs)
        db.add(_obj)
        cls.commit()
        return _obj

    # Read(get all)
    @classmethod
    def get_all(cls):
        query = select(cls).order_by(cls.id.desc())
        results = db.execute(query)
        return results.scalars()

    @classmethod
    def get(cls, _id):
        query = select(cls).where(cls.id == _id)
        result = db.execute(query)
        return result.scalar()

    @classmethod
    def update(cls, _id, **kwargs):
        query = update(cls).where(cls.id == _id).values(**kwargs)
        updated_obj = db.execute(query)
        cls.commit()
        db.expite_all()
        return updated_obj.scalar()

    @classmethod
    def delete(cls, _id):
        query = delete(cls).where(cls.id == _id).returning(cls)
        deleted_obj = db.execute(query)
        cls.commit()
        db.expite_all()
        return deleted_obj.scalar()

    @classmethod
    def truncate(cls, _id):
        query = delete(cls).returning(cls)
        trancated_obj = db.execute(query)
        cls.commit()
        db.expite_all()
        return trancated_obj.scalar()


class Model(AbstractClass, Base):
    __abstract__ = True
