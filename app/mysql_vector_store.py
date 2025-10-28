from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql.expression import func
from sqlalchemy.dialects import mysql
import numpy as np
import logging

from app.config import settings
from app.exceptions import StorageError

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Person(Base):
    __tablename__ = 'persons'
    id = Column(Integer, primary_key=True)
    person_id = Column(String(255), unique=True, nullable=False)
    best_image = Column(mysql.LONGBLOB, nullable=False)
    embeddings = relationship("Embedding", back_populates="person")

class Embedding(Base):
    __tablename__ = 'embeddings'
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.id'))
    embedding = Column(LargeBinary)
    person = relationship("Person", back_populates="embeddings")

class MySQLVectorStore:
    def __init__(self):
        try:
            self.engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
        except Exception as e:
            logger.error(f"Failed to connect to MySQL with SQLAlchemy: {e}")
            raise StorageError(f"Could not connect to MySQL with SQLAlchemy: {e}")

    def store_embeddings(self, person_id: str, embeddings: list[list[float]], best_image: bytes) -> int:
        if not embeddings:
            return 0
        session = self.Session()
        try:
            person = Person(person_id=person_id, best_image=best_image)
            session.add(person)
            session.flush()  # Flush to get the person.id
            for embedding in embeddings:
                embedding_bytes = np.array(embedding).astype(np.float32).tobytes()
                session.add(Embedding(person_id=person.id, embedding=embedding_bytes))
            session.commit()
            return len(embeddings)
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to store embeddings: {e}")
            raise StorageError(f"Failed to store embeddings: {e}")
        finally:
            session.close()

    def search(self, embedding: list[float], threshold: float, limit: int = 1) -> list[tuple[str, float]]:
        session = self.Session()
        try:
            input_embedding = np.array(embedding).astype(np.float32)
            all_embeddings = session.query(Person.person_id, Person.best_image, Embedding.embedding).join(Embedding).all()
            
            results = []
            for person_id, best_image, db_embedding_bytes in all_embeddings:
                db_embedding = np.frombuffer(db_embedding_bytes, dtype=np.float32)
                similarity = np.dot(input_embedding, db_embedding) / (np.linalg.norm(input_embedding) * np.linalg.norm(db_embedding))
                if similarity >= threshold:
                    results.append((person_id, similarity, best_image))
            
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]
        except Exception as e:
            logger.error(f"Failed to search embeddings: {e}")
            raise StorageError(f"Failed to search embeddings: {e}")
        finally:
            session.close()

    def exists(self, person_id: str) -> bool:
        session = self.Session()
        try:
            return session.query(Person).filter(Person.person_id == person_id).first() is not None
        except Exception as e:
            logger.error(f"Failed to check existence: {e}")
            raise StorageError(f"Failed to check existence: {e}")
        finally:
            session.close()

    def delete_embeddings(self, person_id: str) -> bool:
        session = self.Session()
        try:
            person = session.query(Person).filter(Person.person_id == person_id).first()
            if person:
                session.delete(person)
                session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete embeddings: {e}")
            raise StorageError(f"Failed to delete embeddings: {e}")
        finally:
            session.close()

    def update_embeddings(self, person_id: str, embeddings: list[list[float]], best_image: bytes) -> int:
        self.delete_embeddings(person_id)
        return self.store_embeddings(person_id, embeddings, best_image)

    def health_check(self) -> bool:
        try:
            connection = self.engine.connect()
            connection.close()
            return True
        except Exception:
            return False