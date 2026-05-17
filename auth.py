import random
import string
import bcrypt
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, CreditTransaction
from decorators import login_required

auth_bp = Blueprint('auth', __name__)


def _make_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip()
        invite_code = request.form.get('invite_code', '').strip()

        errors = []
        if not username or len(username) < 2:
            errors.append('用户名至少2个字符')
        if not password or len(password) < 6:
            errors.append('密码至少6个字符')
        if not phone or len(phone) != 11 or not phone.isdigit():
            errors.append('请输入正确的11位手机号')
        if User.query.filter_by(username=username).first():
            errors.append('用户名已存在')
        if User.query.filter_by(phone=phone).first():
            errors.append('该手机号已注册')
        inviter = None
        if invite_code:
            inviter = User.query.filter_by(referral_code=invite_code).first()
            if not inviter:
                errors.append('邀请码无效')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html')

        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        while True:
            code = _make_code()
            if not User.query.filter_by(referral_code=code).first():
                break

        user = User(
            username=username,
            phone=phone,
            password_hash=pw_hash,
            credits=2,
            referral_code=code,
            referred_by=inviter.id if inviter else None,
        )
        db.session.add(user)
        db.session.flush()

        # New user gets 2 free credits
        db.session.add(CreditTransaction(
            user_id=user.id, amount=2, reason='register_bonus',
            created_at=datetime.now(timezone.utc)
        ))

        # Inviter gets +3
        if inviter:
            inviter.credits += 3
            db.session.add(CreditTransaction(
                user_id=inviter.id, amount=3, reason='referral',
                related_user_id=user.id,
                created_at=datetime.now(timezone.utc)
            ))

        db.session.commit()
        login_user(user)
        flash(f'注册成功！已赠送 2 次免费模拟。您的邀请码：{code}', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            login_user(user)
            flash('登录成功！', 'success')
            next_page = request.args.get('next', url_for('index'))
            return redirect(next_page)

        flash('用户名或密码错误', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))


@auth_bp.route('/profile')
@login_required
def profile():
    transactions = (CreditTransaction.query
                    .filter_by(user_id=current_user.id)
                    .order_by(CreditTransaction.created_at.desc())
                    .limit(30).all())
    invitees = User.query.filter_by(referred_by=current_user.id).all()
    return render_template('profile.html', transactions=transactions, invitees=invitees)
