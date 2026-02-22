# evaluate.py
# این فایل را بعد از دریافت سوالات از استاد اجرا کنید
import json
from chatbot import answer  # import توابع از chatbot.py

QUESTIONS = [
    # سوالات استاد را اینجا paste کنید یا از فایل بخوانید
    {"id": 1, "question": "حداکثر سنوات مجاز تحصیل چقدر است؟"},
    {"id": 2, "question": "شرایط مرخصی تحصیلی چیست؟"},
    # ...
]

# یا از فایل JSON:
# with open("questions.json", 'r', encoding='utf-8') as f:
#     QUESTIONS = json.load(f)

results = []
for i, q in enumerate(QUESTIONS):
    print(f"[{i+1}/{len(QUESTIONS)}] {q['question'][:60]}")
    ans, _ = answer(q['question'])
    results.append({
        "id": q['id'],
        "question": q['question'],
        "answer": ans,
    })
    print(f"  ✅ {ans[:80]}...")

with open("team_answers.json", 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n💾 team_answers.json ذخیره شد!")
