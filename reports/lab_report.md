# Agent Lab Report

## 1. Tóm tắt

Bài thực hành này triển khai một LangGraph support-ticket agent với tính năng định tuyến theo trạng thái (stateful routing), giả lập thực thi công cụ (mock tool execution), thử lại có giới hạn (bounded retry), mô phỏng vòng kiểm duyệt của con người (human-in-the-loop approval simulation), xử lý thư chết (dead-letter handling), xuất số liệu và tự động tạo báo cáo markdown.

Kết quả chạy hiện tại: **Tỷ lệ thành công 100.00%** trên **7 kịch bản**. Tất cả các kịch bản mẫu đều đã vượt qua.

## 2. Tóm tắt Số liệu

| Số liệu | Giá trị |
|---|---:|
| Total scenarios | 7 |
| Success rate | 100.00% |
| Average nodes visited | 6.43 |
| Total retries | 3 |
| Total approval steps | 2 |
| Resume success | No |

## 3. Kết quả theo từng Kịch bản

| Scenario | Success | Expected route | Actual route | Nodes visited | Retries | Approval observed | Errors |
|---|---|---|---|---:|---:|---|---|
| S01_simple | Yes | simple | simple | 4 | 0 | No | - |
| S02_tool | Yes | tool | tool | 6 | 0 | No | - |
| S03_missing | Yes | missing_info | missing_info | 4 | 0 | No | - |
| S04_risky | Yes | risky | risky | 8 | 0 | Yes | - |
| S05_error | Yes | error | error | 10 | 2 | No | Attempt 1 failed, retrying...<br>Attempt 2 failed, retrying... |
| S06_delete | Yes | risky | risky | 8 | 0 | Yes | - |
| S07_dead_letter | Yes | error | error | 5 | 1 | No | Attempt 1 failed, retrying... |

## 4. Giải thích Kiến trúc

Đồ thị (graph) bắt đầu với `intake`, sau đó gửi truy vấn đã chuẩn hóa tới `classify`. `classify_node` yêu cầu một LLM để phân loại tuyến đường có cấu trúc và chỉ chuyển sang dùng heuristic cơ bản (fallback) khi lệnh gọi LLM thất bại, điều này giúp luồng công việc vẫn có thể chạy được trong quá trình kiểm thử cục bộ hoặc khi gặp giới hạn tốc độ API (API rate limits).

Sau khi phân loại, `route_after_classify` sẽ điều phối trạng thái tới một trong năm luồng:

- `simple`: trả lời trực tiếp bằng `answer_node`, sau đó đến `finalize`.
- `tool`: gọi `tool_node`, đánh giá bằng `evaluate_node`, sau đó trả lời hoặc thử lại.
- `missing_info`: gọi `ask_clarification_node` để tác tử (agent) yêu cầu thêm thông tin chi tiết thay vì bịa đặt thông tin (hallucinating).
- `risky`: chuẩn bị một hành động đề xuất, đi qua `approval_node`, sau đó chỉ tiếp tục thực thi công cụ khi được phê duyệt.
- `error`: đi vào nhánh thử lại (retry) trước tiên, sau đó thử lại việc thực thi công cụ hoặc đi đến `dead_letter`.

`AgentState` dùng chung giúp luồng công việc có thể tuần tự hóa (serializable) và có thể kiểm tra được. Các trường chỉ thêm vào (append-only) như `messages`, `tool_results`, `errors`, và `events` lưu giữ lịch sử thực thi. Các trường ghi đè (overwrite) như `route`, `risk_level`, `attempt`, `evaluation_result`, `pending_question`, `proposed_action`, `approval`, và `final_answer` nắm bắt quyết định hoặc đầu ra mới nhất.

Mọi nhánh đầu cuối đều đi qua `finalize`, nút này tạo ra một sự kiện kiểm toán cuối cùng trước khi đồ thị đạt đến `END`.

## 5. Hành vi của Tuyến

| Route | Main path | Purpose |
|---|---|---|
| `simple` | `classify -> answer -> finalize` | Handle general support questions without tools. |
| `tool` | `classify -> tool -> evaluate -> answer -> finalize` | Use tool context before generating the answer. |
| `missing_info` | `classify -> clarify -> finalize` | Ask the user for required details. |
| `risky` | `classify -> risky_action -> approval -> tool -> evaluate -> answer -> finalize` | Require approval before side-effecting actions. |
| `error` | `classify -> retry -> tool -> evaluate -> retry/dead_letter` | Recover transient failures with a bounded retry loop. |

## 6. Output Files

- `outputs/metrics.json`: kết quả chạy ở định dạng máy có thể đọc được, dùng cho xác thực cục bộ và chấm điểm. Nó lưu các số liệu tóm tắt cùng với một bản ghi chi tiết cho mỗi kịch bản.
- `reports/lab_report.md`: báo cáo định dạng con người có thể đọc được, được tạo từ `outputs/metrics.json`.
- `data/sample/scenarios.jsonl`: các đầu vào mẫu được dùng để chạy thử toàn bộ các tuyến của đồ thị.

## 7. Failure Analysis

1. **Lỗi API LLM hoặc giới hạn tốc độ**: `classify_node` và `answer_node` bắt các lỗi từ nhà cung cấp. Việc phân loại sẽ dự phòng (fallback) bằng các heuristic tất định, và việc trả lời sẽ trả về một thông báo dự phòng an toàn để đồ thị vẫn có thể kết thúc.
2. **Lỗi công cụ tạm thời**: `tool_node` có thể trả về kết quả lỗi đối với các kịch bản `error`. `evaluate_node` đánh dấu trạng thái là `needs_retry`, và `retry_or_fallback_node` tăng `attempt`.
3. **Rủi ro thử lại vô hạn**: `route_after_retry` so sánh `attempt` với `max_attempts`. Khi đạt đến giới hạn, đồ thị chuyển tuyến đến `dead_letter` thay vì lặp lại mãi mãi.
4. **Tác động phụ rủi ro**: hoàn tiền, xóa, gửi email, và các hành động tương tự được định tuyến qua `risky_action_node` và `approval_node` trước khi thực thi công cụ.
5. **Thiếu ngữ cảnh người dùng**: các yêu cầu mơ hồ được định tuyến tới `ask_clarification_node`, tránh việc đưa ra các giả định không được hỗ trợ.

## 8. Những hạn chế hiện tại

- `approval_node` hiện đang sử dụng mô phỏng phê duyệt (mock approval) để đảm bảo khả năng lặp lại trong CI/local; nó không tạm dừng cho một người đánh giá thực sự.
- Việc lưu trữ trạng thái (persistence) hiện đang sử dụng bộ nhớ (memory checkpointer) từ `configs/lab.yaml`; lưu trữ bằng SQLite/Postgres được để dành như một phần mở rộng.
- `evaluate_node` sử dụng một heuristic đơn giản thay vì dùng LLM-as-judge (LLM làm giám khảo).
- Việc thực thi công cụ được mô phỏng (mocked), do đó không có hệ thống đặt hàng, hoàn tiền, email hay tài khoản thực sự nào được gọi.

## 9. Improvement Plan

- Thêm lưu trữ trạng thái (checkpointing) bằng SQLite và trình diễn lịch sử trạng thái hoặc khôi phục sự cố.
- Thay thế mô phỏng phê duyệt bằng `interrupt()` của LangGraph cho một luồng đánh giá của người thật.
- Thêm đánh giá bằng LLM-as-judge để kiểm tra chất lượng kết quả công cụ phong phú hơn.
- Thêm đo độ trễ cho mỗi nút để `latency_ms` trở nên có ý nghĩa.
- Mở rộng các kịch bản kiểu ẩn để kiểm tra mức độ ưu tiên của tuyến, các yêu cầu mơ hồ, và các trường hợp thử lại ở biên (edge cases).
