import json
import time
from pathlib import Path

JOBS_PATH = Path(r"C:\Users\ADMIN\.openclaw\cron\jobs.json")

NEW_MSG = r"""Mỗi lần chạy (06:00 và 18:00, Asia/Bangkok):

A) Check Moodle (HCMUS)
- Dùng OpenClaw managed Edge (profile openclaw). Nếu bị logout thì đăng nhập bằng Microsoft 365 (account 24280018) nếu có thể; nếu không thể thì báo rõ.
- Check 2 môn để lấy item actionable (assignment/quiz) + due date + submission status:
  1) https://courses.hcmus.edu.vn/course/view.php?id=16068
  2) https://courses.hcmus.edu.vn/course/view.php?id=15982
- Ưu tiên các trang overview/index nếu có: /mod/assign/index.php?id=... và /mod/quiz/index.php?id=..., hoặc /course/overview.php?... (activity overview).

B) Sync vào Notion (English)
- Notion database_id: 31e4c265832d8011bc64e832d0cff957 (To do).
- Tạo/Update task cho mỗi item tìm được (upsert theo title).
- Properties cần set (đúng key trong DB):
  - Task (title)
  - Description (rich_text)
  - Deadline (date)
  - Status (status)
  - Priority (select) [optional]
  - Category (select)  <-- LƯU Ý: property name trong DB đang là " Category" (có khoảng trắng đầu dòng).
- Set Category = Class.
- Title format (English): <COURSE_CODE> - <Homework/Quiz> <#>
  (giữ tên gốc kiểu "BTVN#3" trong Description)
- Description phải có: course name, Moodle URL, due date text gốc, submission status gốc.

C) Gửi 1 bản Notion digest (Vietnamese)
- Query Notion và gửi tóm tắt:
  - Overdue (Status != Done)
  - Due in next 7 days (Status != Done)
- Group theo Category (Class, Peganyx, ...).
- Đây là message DUY NHẤT cần gửi (không báo riêng từng bài Moodle nữa).
- Nếu không có task nào trong 2 nhóm trên, vẫn gửi:
  "Không có deadline ở 2 môn này. Notion: không có việc sắp tới."
"""


def main():
    data = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    now = int(time.time() * 1000)
    updated = False
    for j in data.get("jobs", []):
        if j.get("name") == "HCMUS courses deadline check":
            j.setdefault("payload", {})["message"] = NEW_MSG
            j["payload"]["timeoutSeconds"] = 420
            j["payload"]["thinking"] = "low"
            j["updatedAtMs"] = now
            updated = True

    if not updated:
        raise SystemExit("NOT_FOUND")

    JOBS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("UPDATED")


if __name__ == "__main__":
    main()
