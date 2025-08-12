# app.py
from flask import Flask, render_template, session, redirect, url_for
from flask_mysqldb import MySQL

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'

# MySQL 설정
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'  #변경 '010417'
app.config['MYSQL_DB'] = 'shortory'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)
app.mysql = mysql  # current_app.mysql 로 접근할 수 있게 등록

# Blueprints
from auth.routes import auth_bp
from creator.routes import creator_bp
from reviewer.routes import reviewer_bp
from timestamp.routes import timestamp_bp
from reviewer.result_routes import result_bp

app.register_blueprint(auth_bp)
app.register_blueprint(creator_bp)
app.register_blueprint(reviewer_bp)
app.register_blueprint(timestamp_bp)
app.register_blueprint(result_bp)

# ✅ 메인: 항상 랜딩 페이지 렌더
@app.route('/')
def index():
    return render_template('main/main.html')


@app.route('/go')
def go():
    if not session.get('loggedin'):
        return redirect(url_for('auth.login'))
    role = session.get('role')
    if role == 'reviewer':
        return redirect(url_for('reviewer.myroom'))
    if role == 'creator':
        return redirect(url_for('creator.dashboard'))
    # 알 수 없는 역할이면 로그인 화면으로
    return redirect(url_for('auth.login'))

@app.route('/home')
def home():
    if 'loggedin' in session:
        return f"환영합니다, {session['username']}님!"
    return redirect(url_for('auth.login'))

@app.route('/test_db')
def test_db():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users")
        data = cursor.fetchall()
        cursor.close()
        return f"DB 연결 성공! users 테이블에 {len(data)}개 데이터가 있습니다."
    except Exception as e:
        return f"DB 연결 실패: {e}"

if __name__ == '__main__':
    app.run(debug=True)
