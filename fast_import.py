"""
Fast data import using pandas. Run: python -u fast_import.py
"""
import os, sys, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app
from models import db, School, AdmissionRecord, ScoreDistribution

app = create_app()
DSK = 'c:/Users/22430/Desktop/高考河北数据'
DDRV = 'd:/高考数据'


def main():
    with app.app_context():
        # Clear
        for t in (AdmissionRecord, ScoreDistribution, School):
            db.session.execute(db.delete(t))
        db.session.commit()
        print("Cleared.")

        # ====== SCHOOLS (from 2024 undergrad + 2025 major) ======
        print("\n--- Schools ---")
        schools = {}  # code -> dict

        # 2024 undergrad - has 985/211 metadata
        for fname in os.listdir(DSK):
            if '专业录取数据-本科' not in fname: continue
            path = os.path.join(DSK, fname)
            print(f"  Reading {fname}...")
            df = pd.read_excel(path, header=0 if '物理' in fname else 1)
            # Normalize columns
            cols = {c: c for c in df.columns}
            name_col = next((c for c in cols if '学校' in str(c)), None)
            if not name_col: continue

            for _, row in df.iterrows():
                name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ''
                if not name: continue
                # Use hash for temp code
                code = str(abs(hash(name)) % 9000 + 1000).zfill(4)
                if code in schools: continue
                schools[code] = {
                    'code': code, 'name': name,
                    'type': str(row.get('学校类型', '')).strip() if pd.notna(row.get('学校类型', None)) else '',
                    'attribute': str(row.get('学校属性', '')).strip() if pd.notna(row.get('学校属性', None)) else '',
                    'level': str(row.get('办学层次', '')).strip() if pd.notna(row.get('办学层次', None)) else '',
                    'city': str(row.get('城市', '')).strip() if pd.notna(row.get('城市', None)) else '',
                    'province': str(row.get('省份', '')).strip() if pd.notna(row.get('省份', None)) else '',
                    'is_985': str(row.get('985', '')).strip() == '是' if pd.notna(row.get('985', None)) else False,
                    'is_211': str(row.get('211', '')).strip() == '是' if pd.notna(row.get('211', None)) else False,
                    'is_double_first': str(row.get('双一流', '')).strip() == '双一流' if pd.notna(row.get('双一流', None)) else False,
                }

        # 2025 major data for codes
        f25 = os.path.join(DSK, [f for f in os.listdir(DSK) if '25年全国' in f][0])
        print(f"  Reading 2025 major for codes...")
        df25 = pd.read_excel(f25, header=0)
        name_col = next((c for c in df25.columns if '院校名称' in str(c)), None)
        code_col = next((c for c in df25.columns if '院校代码' in str(c)), None)
        if name_col and code_col:
            for _, row in df25.iterrows():
                name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ''
                code = str(int(row[code_col])).zfill(4) if pd.notna(row[code_col]) else ''
                if not name or not code: continue
                # Update existing or add
                found = False
                for k, s in schools.items():
                    if s['name'] == name:
                        s['code'] = code
                        found = True
                        break
                if not found:
                    schools[code] = {'code': code, 'name': name,
                        'type': '', 'attribute': str(row.get('公私性质', '')).strip() if pd.notna(row.get('公私性质', None)) else '',
                        'level': '', 'city': '',
                        'province': str(row.get('所在省', '')).strip() if pd.notna(row.get('所在省', None)) else '',
                        'is_985': False, 'is_211': False, 'is_double_first': False}

        # Deduplicate by code
        unique_schools = {}
        for s in schools.values():
            c = s['code']
            if c in unique_schools:
                # Keep the one with better metadata
                old = unique_schools[c]
                if s['is_985'] or s['is_211'] or s['is_double_first']:
                    unique_schools[c] = s
                elif s['attribute'] and not old['attribute']:
                    unique_schools[c] = s
            else:
                unique_schools[c] = s
        school_list = list(unique_schools.values())
        print(f"  Inserting {len(school_list)} unique schools...")
        db.session.bulk_save_objects([School(**s) for s in school_list])
        db.session.commit()
        print(f"  -> {len(school_list)} schools")
        name_to_code = {s['name']: s['code'] for s in school_list}

        # ====== ADMISSION RECORDS ======
        print("\n--- Admission Records ---")
        all_records = []
        seen = set()

        def add(df, year, subj_map=None):
            nonlocal all_records
            count = 0
            cols = {c: c for c in df.columns}

            name_c = next((c for c in cols if '院校名称' in str(c) or '学校' == str(c)), None)
            major_c = next((c for c in cols if '专业名称' in str(c) or '专业' == str(c)), None)
            score_c = next((c for c in cols if '最低分' in str(c) or '投档' in str(c)), None)
            rank_c = next((c for c in cols if '位次' in str(c)), None)
            subj_c = next((c for c in cols if '科类' in str(c)), None)
            batch_c = next((c for c in cols if '层次' in str(c) or '批次' in str(c)), None)
            req_c = next((c for c in cols if '选科' in str(c)), None)
            mcode_c = next((c for c in cols if '专业代码' in str(c)), None)

            if not all([name_c, major_c, score_c]):
                print(f"    SKIP: missing columns (name={name_c}, major={major_c}, score={score_c})")
                return

            for _, row in df.iterrows():
                try:
                    score = int(float(row[score_c]))
                except (ValueError, TypeError):
                    continue
                if score < 100 or score > 750: continue

                name = str(row[name_c]).strip() if pd.notna(row[name_c]) else ''
                major = str(row[major_c]).strip() if pd.notna(row[major_c]) else ''
                if not name: continue

                # Determine subject
                if subj_c and pd.notna(row.get(subj_c)):
                    subj = '物理类' if '物理' in str(row[subj_c]) else '历史类'
                elif subj_map:
                    subj = subj_map
                else:
                    subj = ''

                # Determine batch
                batch = ''
                if batch_c and pd.notna(row.get(batch_c)):
                    b = str(row[batch_c])
                    if '本科' in b: batch = '本科批'
                    elif '专科' in b or '高职' in b: batch = '专科批'
                    else: batch = b

                try:
                    rank = int(float(row[rank_c])) if rank_c and pd.notna(row.get(rank_c)) else None
                except: rank = None

                key = (year, subj, score, name[:20], major[:20])
                if key in seen: continue
                seen.add(key)

                code = name_to_code.get(name, str(abs(hash(name)) % 9000 + 1000).zfill(4))
                all_records.append({
                    'year': year, 'subject': subj, 'batch': batch,
                    'school_code': code, 'school_name': name,
                    'major_code': str(row[mcode_c]).strip() if mcode_c and pd.notna(row.get(mcode_c)) else '',
                    'major_name': major, 'min_score': score, 'min_rank': rank,
                    'subject_req': str(row[req_c]).strip()[:50] if req_c and pd.notna(row.get(req_c)) else '',
                })
                count += 1
            return count

        # 2023 major
        f = os.path.join(DSK, [f for f in os.listdir(DSK) if '2023' in f and '专业' in f][0])
        print(f"  Loading 2023...")
        df = pd.read_excel(f, header=0)
        n = add(df, 2023)
        print(f"    -> {n} records (total {len(all_records)})")

        # 2024 undergrad + vocational
        for fname in os.listdir(DSK):
            if '专业录取数据' not in fname or '2024' not in fname: continue
            track = '物理类' if '物理' in fname else '历史类'
            batch = '本科批' if '本科' in fname else '专科批'
            print(f"  Loading 2024 {track} ({batch})...")
            # Determine header row
            path = os.path.join(DSK, fname)
            first_cell = pd.read_excel(path, nrows=0).columns[0]
            hr = 0 if first_cell in ('学校', '院校名称') else 1
            df = pd.read_excel(path, header=hr)
            # Override batch since 2024 file col might not have it
            old_records = len(all_records)
            n = add(df, 2024, subj_map=track)
            # Set batch
            for r in all_records[old_records:]:
                r['batch'] = batch
            print(f"    -> {n} records (total {len(all_records)})")

        # 2025 major (48K)
        print(f"  Loading 2025 major...")
        df25 = pd.read_excel(f25, header=0)
        n = add(df25, 2025)
        print(f"    -> {n} records (total {len(all_records)})")

        # 2025 vocational from D:
        for fname in os.listdir(DDRV):
            if '2025' not in fname or not fname.endswith('.xlsx'): continue
            if '物理' not in fname and '历史' not in fname: continue
            track = '物理类' if '物理' in fname else '历史类'
            print(f"  Loading 2025 {track} vocational...")
            path = os.path.join(DDRV, fname)
            df = pd.read_excel(path, header=0)
            old = len(all_records)
            n = add(df, 2025, subj_map=track)
            for r in all_records[old:]:
                r['batch'] = '专科批'
            print(f"    -> {n} records (total {len(all_records)})")

        # Bulk insert
        print(f"\n  Inserting {len(all_records)} records...")
        for i in range(0, len(all_records), 5000):
            db.session.bulk_insert_mappings(AdmissionRecord, all_records[i:i+5000])
            db.session.commit()
            print(f"    {i}/{len(all_records)}")
        db.session.commit()

        # ====== SCORE DISTRIBUTION ======
        print("\n--- Score Distribution ---")
        sd = []
        path = os.path.join(DSK, [f for f in os.listdir(DSK) if '一分一段' in f][0])
        wb = pd.ExcelFile(path)
        for sname in wb.sheet_names:
            if '对比' in sname: continue
            year = 2024 if '2024' in sname else 2025
            subject = '物理类' if '物理' in sname else '历史类'
            df = wb.parse(sname, header=None)
            for _, row in df.iterrows():
                try:
                    score = int(float(row.iloc[0])) if pd.notna(row.iloc[0]) else 0
                    cnt = int(float(row.iloc[1])) if len(row) > 1 and pd.notna(row.iloc[1]) else 0
                    cum = int(float(row.iloc[2])) if len(row) > 2 and pd.notna(row.iloc[2]) else 0
                    if 100 <= score <= 750 and cum > 0:
                        sd.append({'year': year, 'subject': subject, 'score': score, 'count': cnt, 'cumulative': cum})
                except: pass
        # 2023 from D:
        path23 = os.path.join(DDRV, '2023-2025河北高考投档线大全.xlsx')
        if os.path.exists(path23):
            wb23 = pd.ExcelFile(path23)
            for sname in wb23.sheet_names:
                if '2023一分一段' not in sname: continue
                subject = '物理类' if '物理' in sname else '历史类'
                df = wb23.parse(sname, header=None)
                for _, row in df.iterrows():
                    try:
                        score = int(float(row.iloc[0])) if pd.notna(row.iloc[0]) else 0
                        cnt = int(float(row.iloc[2])) if len(row) > 2 and pd.notna(row.iloc[2]) else 0
                        cum = int(float(row.iloc[3])) if len(row) > 3 and pd.notna(row.iloc[3]) else 0
                        if score and cum:
                            sd.append({'year': 2023, 'subject': subject, 'score': score, 'count': cnt, 'cumulative': cum})
                    except: pass

        db.session.bulk_insert_mappings(ScoreDistribution, sd)
        db.session.commit()
        print(f"  -> {len(sd)} rows")

        # ====== SUMMARY ======
        print("\n" + "=" * 50)
        print(f"Schools:     {School.query.count()}")
        print(f"Admissions:  {AdmissionRecord.query.count()}")
        print(f"Score Dist:  {ScoreDistribution.query.count()}")
        for y in [2023, 2024, 2025]:
            for s in ['物理类', '历史类']:
                c = AdmissionRecord.query.filter_by(year=y, subject=s).count()
                if c: print(f"  {y} {s}: {c}")
        print("=" * 50)
        print("DONE.")


if __name__ == '__main__':
    main()
