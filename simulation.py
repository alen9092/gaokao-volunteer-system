import json
from datetime import datetime, timezone
from collections import defaultdict
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user
from models import db, AdmissionRecord, ScoreDistribution, School, CreditTransaction, SimulationHistory
from decorators import login_required

sim_bp = Blueprint('simulation', __name__)


def _cap_top_rank(user_score, user_rank, subject):
    """
    When user score exceeds the top data range (max_2025_score - 10),
    use an effective rank so classification doesn't break for top scorers.
    Returns (effective_rank, max_2025_score).
    """
    max_2025 = db.session.query(
        db.func.max(AdmissionRecord.min_score)
    ).filter(
        AdmissionRecord.year == 2025,
        AdmissionRecord.subject == subject
    ).scalar() or 689

    if user_score > 0 and user_score > (max_2025 - 10):
        sd = ScoreDistribution.query.filter(
            ScoreDistribution.year == 2025,
            ScoreDistribution.subject == subject,
            ScoreDistribution.score == max_2025 - 10
        ).first()
        if sd and sd.cumulative:
            return sd.cumulative, max_2025
        return 300, max_2025

    return user_rank, max_2025


def predict_2026_ranks(subject, batch_filter, province_filter):
    """
    Aggregate 2023-2025 data per major, predict 2026 min_rank.
    Group by (school_name, major_name) since codes may differ across years.
    Returns list of dicts with prediction results.
    """
    query = AdmissionRecord.query.filter(
        AdmissionRecord.subject == subject,
        AdmissionRecord.min_rank.isnot(None),
        AdmissionRecord.min_rank > 0,
    )
    if batch_filter:
        query = query.filter_by(batch=batch_filter)

    all_rows = query.all()

    # Group by (school_name, major_name, school_code)
    groups = defaultdict(lambda: {'ranks': {}, 'scores': {}, 'school_code': '', 'major_code': '', 'batch': '', 'subject_req': ''})
    for r in all_rows:
        key = (r.school_name.strip(), r.major_name.strip())
        g = groups[key]
        g['ranks'][r.year] = r.min_rank
        g['scores'][r.year] = r.min_score
        if r.school_code:
            g['school_code'] = r.school_code
        if r.major_code:
            g['major_code'] = r.major_code
        if r.batch:
            g['batch'] = r.batch
        if r.subject_req:
            g['subject_req'] = r.subject_req

    predictions = []
    for (school_name, major_name), g in groups.items():
        ranks = g['ranks']
        years = sorted(ranks.keys())

        if len(years) == 0:
            continue

        # Predict 2026 rank with weighted average + trend
        if len(years) == 3:
            # Weighted: recent years matter more
            pred_rank = ranks[2025] * 0.5 + ranks[2024] * 0.3 + ranks[2023] * 0.2
        elif len(years) == 2:
            newer = max(years)
            older = min(years)
            pred_rank = ranks[newer] * 0.6 + ranks[older] * 0.4
        else:
            # Only 1 year → use as-is with small adjustment
            pred_rank = list(ranks.values())[0]

        # Get latest score and batch info
        latest_year = max(years)
        latest_score = g['scores'].get(latest_year, 0)

        pred_rank = int(pred_rank)

        predictions.append({
            'school_name': school_name,
            'school_code': g['school_code'],
            'major_name': major_name,
            'major_code': g['major_code'],
            'batch': g['batch'],
            'subject_req': g['subject_req'],
            'pred_rank': pred_rank,
            'latest_score': latest_score,
            'years_available': len(years),
            'year_ranks': {str(y): ranks[y] for y in years},
        })

    # Filter by province if needed
    if province_filter:
        codes_in_province = set(
            s.code for s in School.query.filter_by(province=province_filter).all()
        )
        predictions = [p for p in predictions if p['school_code'] in codes_in_province]

    return predictions


@sim_bp.route('/simulate', methods=['GET', 'POST'])
@login_required
def simulate():
    results = None
    user_score = None
    user_rank = None

    if request.method == 'POST':
        if current_user.credits < 1:
            flash('免费次数已用完！请邀请好友或联系管理员充值。', 'danger')
            return redirect(url_for('auth.profile'))

        user_score = int(request.form.get('score', 0))
        user_rank = int(request.form.get('rank', 0))
        subject = request.form.get('subject', '物理类')
        province_filter = request.form.get('province', '').strip()
        batch_filter = request.form.get('batch', '').strip()

        if user_rank <= 0:
            flash('请输入有效的位次', 'danger')
            return redirect(url_for('simulation.simulate'))

        # 位次系统：高于680分使用分数→位次直接映射
        if user_score > 680:
            user_rank = 751 - user_score
            effective_rank = user_rank
            max_2025 = 750
        else:
            # Cap effective rank for top scorers (score > max_2025 - 10)
            effective_rank, max_2025 = _cap_top_rank(user_score, user_rank, subject)

        # Predict 2026 ranks for all majors
        predictions = predict_2026_ranks(subject, batch_filter, province_filter)

        # Classify into 冲/稳/保 based on predicted 2026 rank vs effective rank
        charge, stable, safe = [], [], []
        for p in predictions:
            pr = p['pred_rank']
            if user_score > 680:
                # 位次系统：680分以上 → 稳=清北华五 / 保=中上985
                stable_threshold = 120   # 清北华五线
                safe_threshold = 600     # 中上985线

                if pr <= stable_threshold:
                    stable.append(p)
                elif pr <= safe_threshold:
                    safe.append(p)
            elif user_rank < 100:
                # Top students: no charge, everything is stable or safe
                if pr <= effective_rank * 3.0:
                    stable.append(p)
                elif pr <= effective_rank * 12.0:
                    safe.append(p)
            else:
                if pr < effective_rank * 0.80:
                    charge.append(p)
                elif pr < effective_rank * 0.98:
                    charge.append(p)
                elif pr <= effective_rank * 1.10:
                    stable.append(p)
                elif pr <= effective_rank * 1.50:
                    safe.append(p)

        # Sort and limit
        charge = sorted(charge, key=lambda p: p['pred_rank'], reverse=True)[:30]
        stable = sorted(stable, key=lambda p: p['pred_rank'])[:30]
        safe = sorted(safe, key=lambda p: p['pred_rank'])[:30]

        # Attach school metadata
        all_codes = set(p['school_code'] for p in charge + stable + safe if p['school_code'])
        schools = School.query.filter(School.code.in_(list(all_codes))).all()
        school_map = {s.code: s for s in schools}

        for p_list in [charge, stable, safe]:
            for p in p_list:
                p['_school'] = school_map.get(p['school_code'])

        results = {'charge': charge, 'stable': stable, 'safe': safe}

        # Deduct credit
        current_user.credits -= 1
        db.session.add(CreditTransaction(
            user_id=current_user.id, amount=-1, reason='simulation',
            created_at=datetime.now(timezone.utc)
        ))

        # Save history
        db.session.add(SimulationHistory(
            user_id=current_user.id,
            score=user_score, subject=subject, year=2026,
            filters_json=json.dumps({'province': province_filter, 'batch': batch_filter}),
            results_json=json.dumps({
                'user_rank': user_rank,
                'charge': [{'sn': p['school_name'], 'mn': p['major_name'], 'pr': p['pred_rank']} for p in charge],
                'stable': [{'sn': p['school_name'], 'mn': p['major_name'], 'pr': p['pred_rank']} for p in stable],
                'safe': [{'sn': p['school_name'], 'mn': p['major_name'], 'pr': p['pred_rank']} for p in safe],
            })
        ))
        db.session.commit()

    # Dropdown options
    batches = (db.session.query(AdmissionRecord.batch)
               .distinct().order_by(AdmissionRecord.batch).all())
    batches = [b[0] for b in batches if b[0]]

    provinces = (db.session.query(School.province)
                 .filter(School.province != '')
                 .distinct().order_by(School.province).all())
    provinces = [p[0] for p in provinces if p[0]]

    return render_template('simulation.html',
                           results=results, user_rank=user_rank, user_score=user_score,
                           batches=batches, provinces=provinces)
