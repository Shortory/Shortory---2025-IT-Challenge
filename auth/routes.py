# auth/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app

auth_bp = Blueprint('auth', __name__, url_prefix='')

# 회원가입
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    role = request.args.get('role', request.form.get('role', 'creator'))
    msg = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        user_id = request.form['username']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            msg = '비밀번호가 일치하지 않습니다.'
            return render_template('auth/signup.html', msg=msg, role=role)

        cursor = current_app.mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
        account = cursor.fetchone()

        if account:
            msg = '이미 존재하는 아이디입니다.'
        else:
            cursor.execute(
                'INSERT INTO users (name, email, phone, user_id, password, role) VALUES (%s, %s, %s, %s, %s, %s)',
                (name, email, phone, user_id, password, role)
            )
            current_app.mysql.connection.commit()
            return redirect(url_for('auth.signup_success', role=role))
        cursor.close()
    return render_template('auth/signup.html', msg=msg, role=role)

# 회원가입 성공
@auth_bp.route('/signup_success')
def signup_success():
    role = request.args.get('role', 'creator')
    return render_template('auth/signup_success.html', role=role)

# 로그인
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    role = request.args.get('role', request.form.get('role', 'creator'))
    msg = ''
    if request.method == 'POST':
        user_id = request.form.get('userName')
        password = request.form.get('userPassword')

        cursor = current_app.mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = %s AND role = %s', (user_id, role))
        account = cursor.fetchone()
        cursor.close()

        if account and account['password'] == password:
            # 세션 설정
            session['loggedin'] = True
            session['user_id'] = account['id']
            session['username'] = account['user_id']
            session['role'] = account['role']

            # 리다이렉트
            if role == 'creator':
                return redirect(url_for('creator.dashboard'))
            else:
                return redirect(url_for('reviewer.myroom'))
        else:
            msg = '아이디 또는 비밀번호가 틀렸습니다.'
    return render_template('auth/login.html', msg=msg, role=role)

# 로그아웃
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
