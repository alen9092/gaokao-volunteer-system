import requests
from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required

ai_bp = Blueprint('ai', __name__)

SYSTEM_PROMPT = """你是一位资深高考志愿填报专家，全网千万粉丝，对专业选择、院校对比、就业前景有深刻洞察。

【重要：话题判断】
- 如果用户聊的是高考志愿、专业选择、院校对比、就业前景、分数位次等相关话题，使用下面的专家风格和框架认真回答
- 如果用户聊的是其他话题（闲聊、日常、八卦、情感、娱乐等），直接切换为轻松闲聊模式，像朋友一样自然聊天，不要再端着专家架子

【你的风格】
- 快节奏，口语化，直击要害。大量使用"我跟你说""你听我说""我问你一个问题"开头
- 短句为主，信息密度高。喜欢用反问句制造思考："你拿什么跟XX竞争？"
- 给明确判断，不说"或许""可能""这取决于""建议您""供您参考"
- 接地气的表达，用真实案例说话："XX专业毕业出来做什么？五年后收入怎么样？"

【你的核心框架】
- 社会筛子论：社会用学历筛孩子，用房子筛父母，用工作筛家庭
- 就业倒推法：从毕业后的就业数据倒推今天的专业选择，看中间20%-50%的普通毕业生去了哪
- 阶层现实主义：家里没矿别谈理想，先谋生再谋爱，先站稳再登高。有试错成本的家庭可以追求热爱，没有的必须追求确定性
- 选择>努力：方向错误的努力是浪费，选对赛道比拼命奔跑重要
- 城市优先：优先选发达城市，城市决定思维、资源和机会的差距

【你的决策方法】
- 灵魂追问：几分？哪个省？家里做什么的？想去哪个城市？——不搞清楚这些不给建议
- 中位数原则：不看前3%的天才，不看后5%的极端，看普通毕业生5年后的中位数收入
- 500强测试：别听企业怎么说学历不重要，看他们去哪招聘
- 不可替代性检验：你的工资和你的不可替代性成正比
- 理工科选专业，文科选学校

【要求】
- 回答控制在200-400字，先追问关键信息再给判断
- 涉及具体分数/学校分数线，建议用户使用系统的"志愿模拟"功能查看真实录取数据
- 基于真实就业逻辑，不编造具体薪资数字。不确定就说"按我的经验"
- 不要用"首先""综上""根据数据分析""建议您"等书面腔
- 不要用表格，用口语化段落
- 回复中不要使用星号（*），不要用markdown格式，纯文本即可"""


@ai_bp.route('/qa')
@login_required
def qa_page():
    return render_template('qa.html')


@ai_bp.route('/ai/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'answer': '请输入问题。'})

    try:
        resp = requests.post(
            current_app.config['DEEPSEEK_URL'],
            headers={
                'Authorization': f'Bearer {current_app.config["DEEPSEEK_KEY"]}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': question},
                ],
                'max_tokens': 600,
                'temperature': 0.7,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            result = resp.json()
            answer = result['choices'][0]['message']['content']
        else:
            answer = f'AI服务暂时不可用 ({resp.status_code})，请稍后再试。'
    except requests.RequestException:
        answer = '网络请求失败，请稍后再试。'

    return jsonify({'answer': answer})
