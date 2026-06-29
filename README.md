# Day 08 Lab - LangGraph Agentic Orchestration

Repo này là bài lab xây dựng workflow agent bằng LangGraph cho bài toán xử lý support ticket. Thay vì chạy một chuỗi xử lý tuyến tính, agent dùng state chung, node chuyên trách và conditional routing để quyết định ticket nên được trả lời ngay, gọi tool, hỏi thêm thông tin, xin phê duyệt thao tác rủi ro, retry khi lỗi, hoặc đưa vào dead-letter khi hết số lần thử.

## Mình đã làm gì

- Khai báo state schema trong `src/langgraph_agent_lab/state.py`, gồm thông tin scenario, route, mức rủi ro, số lần retry, kết quả tool, lỗi, câu trả lời cuối, câu hỏi làm rõ, hành động rủi ro, approval và audit events.
- Implement các node chính trong `src/langgraph_agent_lab/nodes.py`:
  - `intake_node`: chuẩn hóa query đầu vào.
  - `classify_node`: dùng LLM structured output để phân loại route, có fallback heuristic khi LLM lỗi hoặc bị rate limit.
  - `tool_node`: mô phỏng tool lookup/action và mô phỏng lỗi transient cho route `error`.
  - `evaluate_node`: đánh giá kết quả tool để quyết định retry hay trả lời.
  - `answer_node`: dùng LLM tạo câu trả lời dựa trên query và tool context, có fallback khi LLM lỗi.
  - `ask_clarification_node`: tạo câu hỏi làm rõ khi query thiếu thông tin.
  - `risky_action_node`: chuẩn bị mô tả hành động rủi ro cần duyệt.
  - `approval_node`: mô phỏng human-in-the-loop approval để test chạy được offline/CI.
  - `retry_or_fallback_node`: tăng attempt và ghi nhận lỗi retry.
  - `dead_letter_node`: kết thúc các request không khôi phục được sau khi hết retry.
  - `finalize_node`: ghi audit event cuối cùng cho mọi route.
- Implement conditional routing trong `src/langgraph_agent_lab/routing.py`.
- Wire toàn bộ graph trong `src/langgraph_agent_lab/graph.py`:
  - `START -> intake -> classify`
  - `simple -> answer -> finalize -> END`
  - `tool -> tool -> evaluate -> answer/retry`
  - `missing_info -> clarify -> finalize -> END`
  - `risky -> risky_action -> approval -> tool/clarify`
  - `error -> retry -> tool/dead_letter`
- Thêm CLI trong `src/langgraph_agent_lab/cli.py` để chạy toàn bộ scenario, xuất metrics và sinh report.
- Viết test cho state, routing, metrics và graph smoke test trong thư mục `tests/`.
- Tạo output hiện tại:
  - `outputs/metrics.json`: kết quả chạy 7 sample scenarios.
  - `reports/lab_report.md`: báo cáo tổng hợp từ metrics.

## Cấu trúc thư mục quan trọng

| Path | Vai trò |
|---|---|
| `src/langgraph_agent_lab/state.py` | Định nghĩa `AgentState`, `Scenario`, route enum và helper tạo audit event. |
| `src/langgraph_agent_lab/nodes.py` | Chứa toàn bộ logic xử lý của từng node trong graph. |
| `src/langgraph_agent_lab/routing.py` | Chứa các hàm quyết định node tiếp theo sau classify, evaluate, retry và approval. |
| `src/langgraph_agent_lab/graph.py` | Build và compile LangGraph `StateGraph`. |
| `src/langgraph_agent_lab/llm.py` | Helper khởi tạo model LLM từ biến môi trường. |
| `src/langgraph_agent_lab/scenarios.py` | Load file JSONL scenario đầu vào. |
| `src/langgraph_agent_lab/metrics.py` | Tạo metric cho từng scenario và tổng hợp kết quả. |
| `src/langgraph_agent_lab/report.py` | Sinh file báo cáo markdown từ metrics. |
| `src/langgraph_agent_lab/persistence.py` | Adapter checkpointer. Hiện đang hỗ trợ memory checkpointer; SQLite/Postgres là extension. |
| `data/sample/scenarios.jsonl` | 7 scenario mẫu dùng để kiểm tra route. |
| `configs/lab.yaml` | Cấu hình path scenario, checkpointer và report output. |
| `outputs/metrics.json` | File output dạng JSON sau khi chạy scenario. |
| `reports/lab_report.md` | Báo cáo lab dạng markdown. |
| `tests/` | Unit test và smoke test cho graph. |
| `Makefile` | Lệnh chạy trên macOS/Linux/Git Bash. |
| `make.bat` | Lệnh tương đương cho Windows Command Prompt/PowerShell. |

## Luồng xử lý chính

```text
START
  -> intake
  -> classify
      simple       -> answer -> finalize -> END
      tool         -> tool -> evaluate -> answer hoặc retry
      missing_info -> clarify -> finalize -> END
      risky        -> risky_action -> approval -> tool hoặc clarify
      error        -> retry -> tool hoặc dead_letter
```

Retry được giới hạn bằng `attempt` và `max_attempts`. Khi tool vẫn lỗi sau số lần thử cho phép, graph đi tới `dead_letter` rồi `finalize`.

## Chuẩn bị môi trường

Yêu cầu Python 3.11 trở lên.

### Cài dependency

Trên Windows:

```bat
make.bat install
```

Hoặc chạy trực tiếp:

```bash
pip install -e ".[dev]"
```

Nếu muốn dùng provider cụ thể cho LLM:

```bash
pip install -e ".[openai]"
pip install -e ".[anthropic]"
pip install -e ".[google]"
```

### Cấu hình API key

Tạo file `.env` ở thư mục gốc repo và khai báo một API key phù hợp với helper LLM:

```env
OPENAI_API_KEY=your_key_here
# hoặc
ANTHROPIC_API_KEY=your_key_here
# hoặc
GEMINI_API_KEY=your_key_here
```

Nếu LLM bị lỗi hoặc rate limit, một số node đã có fallback để bài lab vẫn chạy được trong môi trường test.

## Cách chạy

### Chạy test

Windows:

```bat
make.bat test
```

macOS/Linux/Git Bash:

```bash
make test
```

Hoặc:

```bash
pytest
```

### Chạy toàn bộ scenario và sinh output

Windows:

```bat
make.bat run-scenarios
```

macOS/Linux/Git Bash:

```bash
make run-scenarios
```

Lệnh này đọc `data/sample/scenarios.jsonl`, chạy từng scenario qua graph, sau đó ghi:

- `outputs/metrics.json`
- `reports/lab_report.md`

### Validate metrics local

Windows:

```bat
make.bat grade-local
```

macOS/Linux/Git Bash:

```bash
make grade-local
```

Lệnh này kiểm tra schema của `outputs/metrics.json` và in success rate.

## Các file output

### `outputs/metrics.json`

Đây là output máy chấm hoặc người review có thể đọc tự động. File gồm:

| Field | Ý nghĩa |
|---|---|
| `total_scenarios` | Tổng số scenario đã chạy. |
| `success_rate` | Tỷ lệ scenario pass theo route kỳ vọng và điều kiện output. |
| `avg_nodes_visited` | Số node trung bình mỗi scenario đi qua. |
| `total_retries` | Tổng số lần graph đi qua retry node. |
| `total_interrupts` | Tổng số lần graph đi qua approval node. |
| `resume_success` | Cờ dành cho extension persistence/resume. Hiện là `false`. |
| `scenario_metrics` | Danh sách metric chi tiết cho từng scenario. |

Mỗi item trong `scenario_metrics` có route kỳ vọng, route thực tế, số node đã đi qua, số retry, approval observed và lỗi nếu có.

### `reports/lab_report.md`

Đây là báo cáo đọc bởi người chấm hoặc người demo. Report giải thích:

- kết quả metrics tổng quan;
- kết quả từng scenario;
- kiến trúc LangGraph và state schema;
- cách xử lý từng route;
- failure modes;
- hạn chế hiện tại và hướng cải thiện.

File này được sinh lại mỗi lần chạy `run-scenarios`, nên muốn đổi nội dung report bền vững thì cần sửa `src/langgraph_agent_lab/report.py`.

## Scenario mẫu

| Scenario | Query rút gọn | Route kỳ vọng | Ý nghĩa |
|---|---|---|---|
| `S01_simple` | Reset password | `simple` | Trả lời trực tiếp. |
| `S02_tool` | Lookup order status | `tool` | Gọi tool rồi trả lời dựa trên kết quả. |
| `S03_missing` | Can you fix it? | `missing_info` | Hỏi thêm thông tin thay vì đoán. |
| `S04_risky` | Refund và gửi email | `risky` | Cần approval trước khi thực hiện. |
| `S05_error` | Timeout failure | `error` | Đi qua retry loop rồi phục hồi. |
| `S06_delete` | Delete customer account | `risky` | Hành động phá hủy, cần approval. |
| `S07_dead_letter` | System failure cannot recover | `error` | `max_attempts=1`, đi tới dead-letter. |

## Ghi chú về persistence

`configs/lab.yaml` đang dùng:

```yaml
checkpointer: memory
```

Điều này giúp graph có checkpointer khi chạy, nhưng dữ liệu không tồn tại sau khi process kết thúc. `src/langgraph_agent_lab/persistence.py` có chỗ mở rộng cho SQLite/Postgres, hiện chưa implement persistence bền vững.

## Lệnh hữu ích

| Lệnh | Tác dụng |
|---|---|
| `make.bat install` hoặc `make install` | Cài package và dev dependencies. |
| `make.bat test` hoặc `make test` | Chạy pytest. |
| `make.bat run-scenarios` hoặc `make run-scenarios` | Chạy scenario, xuất metrics và report. |
| `make.bat grade-local` hoặc `make grade-local` | Validate schema metrics. |
| `make.bat lint` hoặc `make lint` | Chạy Ruff. |
| `make.bat typecheck` hoặc `make typecheck` | Chạy mypy. |
| `make.bat clean` hoặc `make clean` | Xóa cache và output sinh ra. |
