from flask import Flask,request,render_template,session,redirect,url_for
from flask_session import Session
from flask_mysqldb import MySQL
from modules.functions import *
import hashlib
from pprint import pprint
from datetime import datetime
import json
app = Flask(__name__,template_folder="templates",static_folder="static")

app.config["SESSION_PERMANENT"]=False
app.config["SESSION_TYPE"]="filesystem"
Session(app)

app.config['MYSQL_HOST']="localhost"
app.config['MYSQL_USER']="root"
app.config['MYSQL_PASSWORD']="Ik$25o522os"
app.config['MYSQL_DB']="surveyfeedback"
mysql = MySQL(app)


@app.route("/",methods=["GET","POST"])
def hello_world():
    d={"user_name":""}
    if authenticate(mysql,session):
        d['user_name']= (session['user_name'][:12]) + ("..." if len(session['user_name'])>12 else "")
        return render_template('index.html',data=d)
    return redirect('/login')


@app.route("/login",methods=["GET","POST"])
def login():
    d={"errors":[]}
    if request.method =="POST":
        user_name = request.form.get("user_name")
        passcode = request.form.get("passcode")
        h = hashlib.new("SHA256")
        h.update(passcode.encode())
        passcode_h = h.hexdigest()
        a=f'select count(1) as cnt from users_table where user_name ="{user_name}" and passcode = "{passcode_h}" '

        if mysql_db(mysql,a,"get")==((1,),):
            q = f'SELECT user_id from users_table where user_name = "{user_name}"'
            session['user_id'] = mysql_db(mysql,q,"get")[0][0]
            session['user_name'] = user_name
            session['passcode']=passcode_h
            d['user_name']= (session['user_name'][:12]) + ("..." if len(session['user_name'])>12 else "")
            return redirect(url_for('hello_world'))
        d['errors'].append("Login Failed")
    return render_template('signIn.html',data=d)

@app.route("/logout")
def logout():
    if "user_name" in session:
        del session['user_name']
        del session['passcode']
        del session['user_id']
    return "Logged Out Successfully!"


@app.route("/register",methods=['POST','GET'])
def register():
    d={"errors":[]}
    e=False
    if request.method == 'POST':
        if "user_name" in request.form:
            user_name=request.form.get("user_name")
        if "email_address" in request.form:
                email_address=request.form.get("email_address")
        if "passcode" in request.form:
                passcode=request.form.get("passcode")
        if user_name.isalnum() == False or len(user_name)<7:
            #Check Existence in database
            d['errors'].append("Username Invalid...(Enter more than 7 chars with no space)")
            e =True
        if len(passcode)<7:
            d['errors'].append("Passcode Invalid...(Enter more than 7 chars with no space)")
            e=True
        if e:
            return render_template('register.html',data=d)
        #Hashing the passcode
        h = hashlib.new("SHA256")
        h.update(passcode.encode())
        passcode_h = h.hexdigest()
        a = f'INSERT INTO users_table (user_name,passcode,email_address) VALUES ("{user_name}","{passcode_h}","{email_address}");'
        mysql_db(mysql,a,"commit")
        #Saving in Session
        session['user_id']= mysql_db(mysql,"SELECT LAST_INSERT_ID();","get")[0][0]
        session['user_name']=user_name
        session['passcode'] = passcode_h
        #Redirecting and logging in to HomePage
        return redirect(url_for('hello_world'))
       
    return render_template('register.html',data=d)

@app.route("/my_surveys")
def my_surveys():
    d={}
    d['content'] = []
    if authenticate(mysql,session)==False:
        return redirect('/login')
    q = f'SELECT survey_id, user_id, survey_title, survey_description, brand_logo, status, date_created, visibility_description,status_description FROM surveys_table INNER JOIN visibility_table on surveys_table.visibility = visibility_table.visibility_id INNER JOIN status_table on status_table.status_id = surveys_table.status where user_id={session["user_id"]};'
    f = mysql_db(mysql,q,"get")
    for i in f:
        
        q2 = f'SELECT count(*) as cnt FROM response where survey_id={i[0]}'
        resp = mysql_db(mysql,q2,"get")
        temp = list(i)
        temp.append(resp[0][0])
        d['content'].append(temp)
    
    d['user_name']= (session['user_name'][:12]) + ("..." if len(session['user_name'])>12 else "")
    return render_template('my_surveys.html',data=d)

@app.route("/ans_survey",methods=["POST","GET"])
def get_survey_access():
    d={'errors':[]}
    if authenticate(mysql,session)==False:
        return redirect('/login')
    if request.method == 'GET':
        survey_id =request.args['code']
        q=f'SELECT survey_id, user_name,status,visibility,survey_title, survey_description, brand_logo, date_created FROM surveys_table INNER JOIN users_table on users_table.user_id = surveys_table.user_id where survey_id ={survey_id};'
        f = mysql_db(mysql,q,"fetchone")
        if not f:
            d['errors'].append("Survey code does not exist!")
            return render_template('errors.html',data=d)
        elif f[2]==1:
            d['errors'].append("This is Survey has been completed!")
            return render_template('errors.html',data=d)
        elif f[2] == 3 or f[3] == 3:
            d['errors'].append("Survey code does not exist!")
            return render_template('errors.html',data=d)
        q=f'SELECT * FROM response where survey_id={survey_id} and user_id={session["user_id"]}'
        f = mysql_db(mysql,q,"fetchone")
        if f:
            d['errors'].append("Your response already taken!")
            return render_template('errors.html',data=d)
        # get all questions:
        q=f'SELECT * FROM surveyfeedback.questions where SurveyId ={survey_id};'
        questions = mysql_db(mysql,q,"dict")

        # getting options
        ids = [str(i['QuestionId']) for i in questions]
        q2s = ' or '.join(ids)
        q2 = "SELECT * FROM surveyfeedback.question_options where QuestionId = " + q2s
        options = mysql_db(mysql,q2,"dict")
        questions = sorted(questions, key=lambda d: d['order'])
        for i in questions:
            opts=[]
            for j in options:
                if i['QuestionId'] == j['QuestionId']:
                    opts.append(j)
            opts = sorted(opts, key=lambda d: d['order'])
            i['options']= opts
        d['questions'] = questions
        d['survey_details'] =f
      
        return render_template('ans_survey.html',data=d)
    if request.method =="POST":
        ans_data = request.json
        date = datetime.now()
        date_s = date.strftime("%Y-%m-%d")
        mysql_db(mysql,f"INSERT INTO response (survey_id, user_id, date )VALUES ({ans_data['survey_id']},{session['user_id']}, '{date_s}');","commit")
        response_id = mysql_db(mysql,"SELECT LAST_INSERT_ID();","get")[0][0]
        pprint(ans_data['ans'])
        for i in ans_data['ans']:
            if i['questiontype_id'] == 2:
                mysql_db(mysql,f"INSERT INTO answer (response_id, question_id, answer )VALUES ({response_id},{i['question_id']}, '{i['val']}');","commit")
            elif i['questiontype_id'] == 1:
                mysql_db(mysql,f"INSERT INTO answer (response_id, question_id )VALUES ({response_id},{i['question_id']});","commit")
                ans_id = mysql_db(mysql,"SELECT LAST_INSERT_ID();","get")[0][0]
                mysql_db(mysql,f"INSERT INTO answer_option (answer_id, question_option_id )VALUES ({ans_id},{i['optId']});","commit")
        
        return str("Please visit My Surveys")
    return 'a'



@app.route("/create_survey",methods=["GET","POST"])
def create_survey():
    if request.method == "POST":
        data = request.json
        date = datetime.now()
        date_s = date.strftime("%Y-%m-%d")
        json_dump = json.dumps(data['questions'])
        
        q=f"CALL InsertSurveyData({session['user_id']},'{data['survey_title']}', '{data['survey_desc']}',{data['visibility']},'{date_s}','{json_dump}') "
        print(q)
        mysql_db(mysql,q,"commit")
        
        return str("Please visit My Surveys")
    return render_template('create_survey.html')


@app.route("/delete_survey",methods=["POST"])
def delete_survey():
    if authenticate(mysql,session)==False:
        return redirect('/login')
    q=f"CALL DeleteSurvey({request.form.get('id')});"
    print(q)
    mysql_db(mysql,q,"commit")
    return redirect(url_for('my_surveys'))


if __name__ == "__main__":
    app.run(debug=True)