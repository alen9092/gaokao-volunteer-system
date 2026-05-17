from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def login_required(f):
    """Redirect to login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录后再使用此功能。', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def require_credits(f):
    """Check user has at least 1 credit, deduct 1 on success."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.credits < 1:
            flash('免费次数已用完！请邀请好友注册获取免费次数，或联系管理员充值。', 'danger')
            return redirect(url_for('auth.profile'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Only admins can access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('无权访问此页面。', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated
