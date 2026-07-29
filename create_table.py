import psycopg2

def create_tables():
# Connexion à PostgreSQL (adapter host, dbname, user, password)
    conn = psycopg2.connect(
        host="localhost",
        dbname="air_quality",
        user="postgres",
        password="postgres"
    )
    cur = conn.cursor()
#Lecture de schema.sql
    with open("schema.sql", "r") as f:
        schema_sql = f.read()

    try:
        cur.execute(schema_sql)
        conn.commit()
        print("[OK] Tables créées avec succès")
    except Exception as e:
        print("[ERREUR] Impossible de créer les tables :", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_tables()
