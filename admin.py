from datetime import datetime, timezone
from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import db, User, CreditTransaction, RechargeOrder, CardCode
from decorators import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin', methods=['GET', 'POST'])
@admin_required
def index():
    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'topup':
            user_id = int(request.form.get('user_id', 0))
            amount = int(request.form.get('amount', 0))
            if user_id and amount > 0:
                user = db.session.get(User, user_id)
                if user:
                    user.credits += amount
                    db.session.add(CreditTransaction(
                        user_id=user.id, amount=amount, reason='admin_grant',
                        created_at=datetime.now(timezone.utc)
                    ))
                    db.session.commit()
                    flash(f'已为用户 {user.username} 充值 {amount} 次', 'success')
                else:
                    flash('用户不存在', 'danger')
        elif action == 'verify_order':
            order_id = int(request.form.get('order_id', 0))
            order = db.session.get(RechargeOrder, order_id)
            if order and order.status == 'pending':
                from recharge import _complete_order
                _complete_order(order)
                flash(f'订单已通过！卡密 {order.transaction_id} 已生成，用户兑换后 +{order.credits} 次到账', 'success')
            else:
                flash('订单不存在或已处理', 'danger')
        elif action == 'fast_verify':
            order_no = request.form.get('order_no', '').strip()
            order = RechargeOrder.query.filter_by(order_no=order_no).first()
            if order and order.status == 'pending':
                from recharge import _complete_order
                _complete_order(order)
                flash(f'核销成功！卡密 {order.transaction_id} 已生成', 'success')
            elif order and order.status == 'completed':
                flash('该订单已处理过', 'warning')
            else:
                flash('订单号不存在或已处理', 'danger')
        elif action == 'gen_cards':
            count = int(request.form.get('count', 0))
            credits = int(request.form.get('card_credits', 30))
            batch_name = request.form.get('batch_name', '').strip() or ''
            if 1 <= count <= 500 and credits > 0:
                cards = _generate_cards(count, credits, batch_name)
                flash(f'已生成 {len(cards)} 张卡密，每张 {credits} 次', 'success')
            else:
                flash('数量需在1-500之间，次数需大于0', 'danger')
        return redirect(url_for('admin.index'))

    users = User.query.order_by(User.created_at.desc()).all()
    orders = (RechargeOrder.query
              .order_by(RechargeOrder.created_at.desc())
              .limit(30).all())
    cards = (CardCode.query
             .order_by(CardCode.created_at.desc())
             .limit(50).all())
    total_users = len(users)
    return render_template('admin.html', users=users, orders=orders, cards=cards, total_users=total_users)


def _generate_cards(count, credits, batch_name=''):
    """Generate unique card codes. Format: GK-XXXX-XXXX-XXXX"""
    import secrets
    import string
    alphabet = string.ascii_uppercase + string.digits
    # Remove confusing chars: O/0, I/1, L
    alphabet = alphabet.translate(str.maketrans('', '', 'O0I1L'))
    cards = []
    for _ in range(count):
        for _ in range(100):  # retry loop for uniqueness
            parts = [''.join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
            code = 'GK-' + '-'.join(parts)
            if not CardCode.query.filter_by(code=code).first():
                break
        card = CardCode(code=code, credits=credits, batch_name=batch_name)
        db.session.add(card)
        cards.append(card)
    db.session.commit()
    return cards
