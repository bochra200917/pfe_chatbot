# test/test_sql_validation.py

from app.sql_security import validate_sql_query, SQLSecurityError

tests = [
    "SELECT ref,total_ttc FROM m38h_facture LIMIT 10",
    "SELECT * FROM users",
    "DELETE FROM m38h_societe",
    "SELECT password FROM m38h_user"
]

for sql in tests:
    print("\nTEST:", sql)
    try:
        validate_sql_query(sql)
        print("VALID")
    except SQLSecurityError as e:
        print("REJECTED:", e)