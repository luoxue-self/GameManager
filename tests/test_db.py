import db


def test_admin_created_with_given_password():
    import secrets
    username = "admin_" + secrets.token_hex(3)
    info = db.ensure_admin(username, "s3cret-pw")
    assert info and info[0] == username

    con = db.connect()
    row = con.execute("SELECT * FROM users WHERE username=?",
                      (username,)).fetchone()
    con.close()
    assert row is not None
    assert db.verify_pw("s3cret-pw", row["password_hash"])
    assert not db.verify_pw("wrong-pw", row["password_hash"])

    # 已存在时幂等
    assert db.ensure_admin(username, "another-pw") is None
    assert db.verify_pw("s3cret-pw", row["password_hash"])


def test_games_table_columns():
    con = db.connect()
    cols = {r["name"] for r in con.execute("PRAGMA table_info(games)")}
    con.close()
    expected = {"name", "name_norm", "name_pinyin", "type", "code", "cover",
                "saved_at", "download_url", "how_to", "rating",
                "local_status", "year", "location", "dup_note"}
    assert expected <= cols


def test_code_unique_index():
    con = db.connect()
    con.execute("DELETE FROM games")
    con.execute("INSERT INTO games(name,name_norm,code) VALUES('A','a','X1')")
    con.commit()
    try:
        con.execute("INSERT INTO games(name,name_norm,code) VALUES('B','b','X1')")
        con.commit()
        raise AssertionError("编号唯一索引未生效")
    except Exception as e:
        con.rollback()
        assert "UNIQUE" in str(e).upper()
    finally:
        con.execute("DELETE FROM games")
        con.commit()
        con.close()
