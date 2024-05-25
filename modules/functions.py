from flask_mysqldb import MySQL
def authenticate(mysql,session):
    user_name=""
    passcode_h=""
    if "user_name" in session:
        user_name = session['user_name']
    if "passcode" in session:
        passcode_h = session['passcode']
    if not user_name or not passcode_h:
        return False
    a=f'select count(1) as cnt from users_table where user_name ="{user_name}" and passcode = "{passcode_h}" '
    f = mysql_db(mysql,a,"get")

    if f==((1,),):
   
        return True
    else:
        return False
def mysql_db(mysql,query,others="commit"):
        if others=="dict":
            cur = mysql.connection.cursor()
            cur.execute(query)
            fetchdata = cur.fetchall()
            columns = cur.description
            a = [i[0] for i in columns]
            l = [{a[jj]:fetchdata[ii][jj] for jj,j in enumerate(a)} for ii,i in enumerate(fetchdata)]
            cur.close()
            return l
        elif others=="fetchone":
            cur = mysql.connection.cursor()
            cur.execute(query)
            fetchdata = cur.fetchone()
            cur.close()
            return fetchdata
        elif others=="get":
            cur = mysql.connection.cursor()
            cur.execute(query)
            fetchdata = cur.fetchall()
            cur.close()
            return fetchdata
        elif others=="commit":
            cur = mysql.connection.cursor()
            cur.execute(query)
            cur.connection.commit()

            cur.close()
        