import uuid
import hashlib
import os
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import current_user
from models import db, User, RechargeOrder, CreditTransaction, CardCode
from decorators import login_required

recharge_bp = Blueprint('recharge', __name__)

# V免签密钥 — 在V免签后台设置一个一样的
WEBHOOK_KEY = os.environ.get('RECHARGE_WEBHOOK_KEY', 'gaokao-recharge-secret')

# 定价
PRICE_YUAN = 1
CREDITS = 30


def _gen_order_no():
    return datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + uuid.uuid4().hex[:8].upper()


@recharge_bp.route('/recharge')
@login_required
def page():
    orders = (RechargeOrder.query
              .filter_by(user_id=current_user.id)
              .order_by(RechargeOrder.created_at.desc())
              .limit(20).all())
    return render_template('recharge.html', price=PRICE_YUAN, credits=CREDITS, orders=orders)


@recharge_bp.route('/recharge/create', methods=['POST'])
@login_required
def create_order():
    order_no = _gen_order_no()
    order = RechargeOrder(
        user_id=current_user.id,
        order_no=order_no,
        amount_yuan=PRICE_YUAN,
        credits=CREDITS,
        status='pending',
    )
    db.session.add(order)
    db.session.commit()
    return jsonify({'ok': True, 'order_no': order_no, 'amount': PRICE_YUAN})


@recharge_bp.route('/recharge/status/<order_no>')
@login_required
def order_status(order_no):
    """Poll order status. When completed, returns the card code."""
    order = RechargeOrder.query.filter_by(order_no=order_no, user_id=current_user.id).first()
    if not order:
        return jsonify({'ok': False, 'msg': '订单不存在'})
    result = {
        'ok': True,
        'status': order.status,
        'credits': order.credits if order.status == 'completed' else 0,
    }
    if order.status == 'completed' and order.transaction_id:
        card = CardCode.query.filter_by(code=order.transaction_id).first()
        if card and card.status == 'unused':
            result['card_code'] = card.code
    return jsonify(result)


@recharge_bp.route('/recharge/webhook', methods=['GET', 'POST'])
def webhook():
    """
    支付回调 — 兼容 V免签 格式。
    V免签 发送 GET 或 POST:
      price=1.00  remarks=订单号  type=wechat/alipay  sign=MD5(price+remarks+key)
    也可以发送 JSON: {"price":"1.00","remarks":"订单号","type":"wechat","sign":"..."}
    """
    if request.is_json:
        data = request.get_json(silent=True) or {}
        price = data.get('price', '')
        order_no = data.get('remarks', '').strip()
        sign = data.get('sign', '')
    else:
        price = request.args.get('price', request.form.get('price', ''))
        order_no = request.args.get('remarks', request.form.get('remarks', '')).strip()
        sign = request.args.get('sign', request.form.get('sign', ''))

    # 验证签名: MD5(price + remarks + key)
    expected = hashlib.md5((price + order_no + WEBHOOK_KEY).encode()).hexdigest()
    if sign and sign != expected:
        return jsonify({'ok': False, 'msg': '签名验证失败'}), 403

    if not order_no:
        return jsonify({'ok': False, 'msg': '缺少订单号(remarks)'}), 400

    order = RechargeOrder.query.filter_by(order_no=order_no).first()
    if not order:
        return jsonify({'ok': False, 'msg': '订单不存在'}), 404

    if order.status == 'completed':
        return jsonify({'ok': True, 'msg': '已处理'})

    _complete_order(order)
    return jsonify({'ok': True, 'msg': '充值成功'})


@recharge_bp.route('/recharge/redeem', methods=['POST'])
@login_required
def redeem_card():
    """Redeem a card code for credits."""
    code = request.form.get('code', '').strip().upper()
    if not code:
        return jsonify({'ok': False, 'msg': '请输入卡密'})

    card = CardCode.query.filter_by(code=code).first()
    if not card:
        return jsonify({'ok': False, 'msg': '卡密不存在，请检查是否输入正确'})
    if card.status == 'used':
        return jsonify({'ok': False, 'msg': '该卡密已被使用过'})

    # Mark card as used
    card.status = 'used'
    card.used_by = current_user.id
    card.used_at = datetime.now(timezone.utc)

    # Credit the user
    current_user.credits += card.credits
    db.session.add(CreditTransaction(
        user_id=current_user.id,
        amount=card.credits,
        reason='recharge',
        created_at=datetime.now(timezone.utc)
    ))
    db.session.commit()

    return jsonify({
        'ok': True,
        'msg': f'卡密兑换成功！+{card.credits} 次已到账',
        'credits': card.credits,
        'total': current_user.credits
    })


def _complete_order(order):
    """Payment confirmed — generate a card code for the user to redeem."""
    import secrets
    import string
    alphabet = string.ascii_uppercase + string.digits
    alphabet = alphabet.translate(str.maketrans('', '', 'O0I1L'))
    # Generate unique code
    for _ in range(100):
        parts = [''.join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
        code = 'GK-' + '-'.join(parts)
        if not CardCode.query.filter_by(code=code).first():
            break

    card = CardCode(
        code=code,
        credits=order.credits,
        batch_name='auto',
    )
    db.session.add(card)

    order.status = 'completed'
    order.completed_at = datetime.now(timezone.utc)
    order.transaction_id = code  # link card code to order
    db.session.commit()
