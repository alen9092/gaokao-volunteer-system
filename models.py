from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    id_card = db.Column(db.String(18), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    credits = db.Column(db.Integer, default=5)
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    referred_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_admin = db.Column(db.Boolean, default=False)

    inviter = db.relationship('User', remote_side=[id], backref='invitees')


class School(db.Model):
    __tablename__ = 'schools'
    code = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), default='')
    attribute = db.Column(db.String(20), default='')
    level = db.Column(db.String(20), default='')
    city = db.Column(db.String(30), default='')
    province = db.Column(db.String(20), default='')
    is_985 = db.Column(db.Boolean, default=False)
    is_211 = db.Column(db.Boolean, default=False)
    is_double_first = db.Column(db.Boolean, default=False)


class AdmissionRecord(db.Model):
    __tablename__ = 'admission_records'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(10), nullable=False)
    batch = db.Column(db.String(20), default='')
    school_code = db.Column(db.String(10), default='')
    school_name = db.Column(db.String(100), default='')
    major_code = db.Column(db.String(20), default='')
    major_name = db.Column(db.String(200), default='')
    min_score = db.Column(db.Integer, nullable=False)
    min_rank = db.Column(db.Integer, nullable=True)
    subject_req = db.Column(db.String(50), default='')

    __table_args__ = (
        db.Index('idx_admission_year_subject', 'year', 'subject'),
        db.Index('idx_admission_rank', 'year', 'subject', 'min_rank'),
        db.Index('idx_admission_school', 'school_code'),
    )


class ScoreDistribution(db.Model):
    __tablename__ = 'score_distribution'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(10), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    count = db.Column(db.Integer, default=0)
    cumulative = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.Index('idx_score_year_subject', 'year', 'subject'),
    )


class EnrollmentPlan(db.Model):
    __tablename__ = 'enrollment_plans'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    batch = db.Column(db.String(30), default='')
    subject = db.Column(db.String(20), default='')
    plan_type = db.Column(db.String(20), default='')
    school_code = db.Column(db.String(10), default='')
    school_name = db.Column(db.String(100), default='')
    major_code = db.Column(db.String(20), default='')
    major_name = db.Column(db.String(200), default='')
    plan_count = db.Column(db.Integer, default=0)
    subject_req = db.Column(db.String(50), default='')
    tuition = db.Column(db.Integer, nullable=True)
    duration = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.Index('idx_plan_year', 'year'),
    )


class CreditTransaction(db.Model):
    __tablename__ = 'credit_transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(50), default='')
    related_user_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='transactions', foreign_keys=[user_id])


class SimulationHistory(db.Model):
    __tablename__ = 'simulation_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(10), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    filters_json = db.Column(db.Text, default='{}')
    results_json = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='simulations')


class CardCode(db.Model):
    __tablename__ = 'card_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    batch_name = db.Column(db.String(50), default='')
    status = db.Column(db.String(10), default='unused')  # unused / used
    used_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='redeemed_cards')


class RechargeOrder(db.Model):
    __tablename__ = 'recharge_orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_no = db.Column(db.String(32), unique=True, nullable=False)
    amount_yuan = db.Column(db.Integer, nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    pay_method = db.Column(db.String(20), default='')
    transaction_id = db.Column(db.String(100), default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='recharge_orders')
