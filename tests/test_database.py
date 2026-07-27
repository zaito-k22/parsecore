from sqlalchemy import text

from app.db.session import engine


def main():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(result.scalar())


if __name__ == "__main__":
    main()