# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `develop/app.py`
Sau khi đọc file `app.py` trong thư mục `01-localhost-vs-production/develop`, ta phát hiện các anti-patterns (vấn đề) sau:
1. **Hardcoded Secrets (Lộ khóa bảo mật):** API Key (`OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"`) và Database URL (`DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"`) được ghi trực tiếp vào mã nguồn. Nếu đẩy code này lên GitHub, thông tin bảo mật sẽ bị lộ ngay lập tức.
2. **Cấu hình trực tiếp trong code (No Config Management):** Các tham số như `DEBUG = True` hay `MAX_TOKENS = 500` bị gán cứng thay vì quản lý tập trung từ biến môi trường.
3. **Ghi log bằng `print()` và lộ thông tin nhạy cảm:** Ứng dụng dùng hàm `print()` thông thường thay vì thư viện logging chuyên dụng. Hơn nữa, dòng log `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` in trực tiếp API key bảo mật ra stdout, rất nguy hiểm.
4. **Không có Health Check Endpoints:** Thiếu endpoint như `/health` hay `/ready` để giám sát trạng thái của ứng dụng. Khi chạy trên Cloud, nếu ứng dụng bị crash hay treo, hệ thống không thể tự động phát hiện để khởi động lại (restart) container.
5. **Cố định địa chỉ IP và Port chạy ứng dụng (Hardcoded Bind Port & Host):** Ứng dụng gán cứng `host="localhost"` và `port=8000`. Trong Docker hoặc Cloud (như Railway/Render), ứng dụng bắt buộc phải lắng nghe trên `0.0.0.0` để nhận kết nối từ ngoài container, và port phải được đọc động từ biến môi trường `PORT`.
6. **Bật chế độ Debug/Reload mặc định:** Dòng `reload=True` chỉ phù hợp cho quá trình phát triển (development), khi chạy trên production sẽ làm giảm đáng kể hiệu năng ứng dụng và tạo ra lỗ hổng bảo mật nếu xảy ra lỗi và hiển thị stack trace chi tiết.
7. **Không xử lý Graceful Shutdown (Tắt ứng dụng đột ngột):** Không có bộ xử lý tín hiệu (signal handler) để đón nhận tín hiệu `SIGTERM`. Khi container hoặc server bị tắt, ứng dụng sẽ dừng đột ngột khiến các request đang xử lý dở dang bị mất mát hoặc làm hỏng dữ liệu.

---

### Exercise 1.2: Chạy basic version
Basic version đã được chạy thử nghiệm trên local.
- Kết quả phản hồi:
  ```json
  {"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
  ```
- **Nhận xét:** Ứng dụng chạy thành công nhưng không đủ điều kiện để deploy lên production vì tất cả các anti-patterns được chỉ ra ở Exercise 1.1 vẫn tồn tại.

---

### Exercise 1.3: Bảng so sánh giữa Basic (Develop) và Advanced (Production)

Dưới đây là bảng so sánh chi tiết các tính năng giữa phiên bản phát triển cục bộ và phiên bản production-ready:

| Feature | Basic (Develop) | Advanced (Production) | Tại sao quan trọng? |
| :--- | :--- | :--- | :--- |
| **Config** | Gán cứng (Hardcoded) trong code. | Quản lý tập trung từ biến môi trường qua `Settings` (`config.py`). | Giúp tách cấu hình khỏi mã nguồn. Dễ dàng chuyển đổi cấu hình (port, host, environment) giữa các môi trường (dev, staging, prod) mà không cần sửa code. |
| **Secrets** | Hardcode trực tiếp trong code. | Đọc thông qua biến môi trường (`os.getenv("OPENAI_API_KEY")`). | Tránh rò rỉ các API key quan trọng và mật khẩu cơ sở dữ liệu lên Git repo hoặc các hệ thống quản lý mã nguồn công cộng. |
| **Port** | Gán cứng `8000`. | Đọc động từ biến môi trường `PORT` (`os.getenv("PORT")`). | Các dịch vụ Cloud (Railway, Render, AWS, v.v.) tự động gán cổng ngẫu nhiên cho container thông qua biến môi trường `PORT`. Nếu gán cứng sẽ lỗi khởi động. |
| **Host** | Gán cứng `localhost`. | Đặt là `0.0.0.0`. | Cho phép uvicorn chấp nhận các kết nối từ bên ngoài container Docker hoặc internet (thay vì chỉ từ máy nội bộ). |
| **Health check** | Không có. | Cung cấp endpoint `/health` (Liveness) và `/ready` (Readiness). | Giúp Cloud Platform tự động phát hiện ứng dụng bị lỗi/crash để tự khởi động lại, và biết khi nào ứng dụng đã tải xong dữ liệu để route traffic vào. |
| **Logging** | Dùng hàm `print()` thông thường, in cả API key bảo mật. | Sử dụng `logging` định dạng JSON cấu trúc, loại bỏ secrets. | JSON format giúp các hệ thống log aggregator (Datadog, Loki, ELK) dễ dàng parse, tìm kiếm và phân tích log. Không in các secret key ra log tránh rò rỉ. |
| **Shutdown** | Dừng đột ngột. | Hỗ trợ Graceful Shutdown bằng cách xử lý tín hiệu `SIGTERM`. | Đảm bảo ứng dụng hoàn thành nốt các request đang xử lý (in-flight requests) và đóng kết nối database sạch sẽ trước khi tắt, giảm lỗi cho người dùng. |
| **Debug/Reload** | Luôn luôn bật `reload=True`. | Tắt debug reload ở production (`reload=settings.debug`). | Tránh rò rỉ stack trace chi tiết ra ngoài (nguy cơ bảo mật) và tối ưu hóa hiệu năng/tốc độ xử lý của server. |

---

### Checkpoint 1
- [x] Hiểu tại sao hardcode secrets là nguy hiểm.
- [x] Biết cách dùng environment variables.
- [x] Hiểu vai trò của health check endpoint.
- [x] Biết graceful shutdown là gì.

---

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile cơ bản
1. **Base image là gì?**
   - Trong `develop/Dockerfile`: Sử dụng `python:3.11` (là bản phân phối Python đầy đủ, dung lượng lớn ~1 GB).
   - Trong `production/Dockerfile`: Sử dụng `python:3.11-slim` cho cả hai stages (`builder` và `runtime`). Slim base image là phiên bản tối giản của Python (~120-150 MB), giúp tối ưu hóa dung lượng lưu trữ và thời gian tải/download image.
2. **Working directory là gì?**
   - Thư mục làm việc mặc định trong container là `/app` (thiết lập qua lệnh `WORKDIR /app`). Tất cả các lệnh tiếp theo (`COPY`, `RUN`, `CMD`) sẽ được thực thi tại thư mục này.
3. **Tại sao COPY requirements.txt trước?**
   - Nhằm tối ưu hóa cơ chế **Docker layer caching**. Docker xây dựng các layer từ trên xuống dưới. Nếu `requirements.txt` không thay đổi giữa các lần build, Docker sẽ tái sử dụng cache cho các layer cài đặt thư viện (`RUN pip install...`) mà không cần chạy lại, giúp việc build lại image khi thay đổi mã nguồn diễn ra cực kỳ nhanh chóng (chỉ mất vài giây thay vì vài phút).
4. **CMD vs ENTRYPOINT khác nhau thế nào?**
   - **ENTRYPOINT**: Thiết lập lệnh mặc định cố định cho container khi chạy. Lệnh này không dễ bị ghi đè khi chạy lệnh `docker run`. Mọi tham số truyền vào sau tên image ở lệnh `docker run` sẽ được xem là đối số truyền vào cho lệnh trong `ENTRYPOINT`.
   - **CMD**: Định nghĩa lệnh khởi chạy mặc định hoặc các tham số cho `ENTRYPOINT`. `CMD` có thể bị ghi đè hoàn toàn dễ dàng nếu ta cung cấp một câu lệnh khác ở cuối lệnh `docker run`.

### Exercise 2.2: Build và run
- **Quan sát:** 1.67GB

# Exercise 2.3: Multi-stage Build Solution
### 1. Stage 1 (Builder) làm nhiệm vụ gì?
- **Nhiệm vụ:**
  - Khởi đầu từ base image `python:3.11-slim` để làm sạch môi trường.
  - Cài đặt các thư viện hệ thống cần thiết cho quá trình biên dịch (compile) dependencies, cụ thể là `gcc` và `libpq-dev`.
  - Copy file `requirements.txt` vào container.
  - Chạy lệnh cài đặt các package Python (`pip install`) với cờ `--user` để cài đặt trực tiếp vào thư mục `/root/.local`. Cờ `--no-cache-dir` được sử dụng để tránh sinh ra dữ liệu cache tải về không cần thiết.
- **Mục đích:** Đóng vai trò là một "môi trường dựng" (assembly line) chứa đầy đủ các tool nặng để build dependencies, nhưng môi trường này sẽ bị vứt bỏ sau khi build xong và không dùng để chạy production.
### 2. Stage 2 (Runtime) làm nhiệm vụ gì?
- **Nhiệm vụ:**
  - Xuất phát từ một base image slim sạch hoàn toàn (`python:3.11-slim`).
  - Tạo một group và user non-root (`appuser`) nhằm đảm bảo bảo mật cho ứng dụng (chạy ứng dụng dưới quyền non-root là security best practice).
  - Copy toàn bộ các package Python đã được biên dịch hoàn thiện từ Stage 1 sang Stage 2: `COPY --from=builder /root/.local /home/appuser/.local`.
  - Copy mã nguồn ứng dụng (`main.py`) và Mock LLM (`utils/mock_llm.py`).
  - Đặt quyền sở hữu thư mục `/app` cho `appuser` và thiết lập biến môi trường `PATH`, `PYTHONPATH`.
  - Cấu hình lệnh kiểm tra sức khỏe container (`HEALTHCHECK`).
  - Thiết lập lệnh chạy mặc định uvicorn.
- **Mục đích:** Là container chạy thực tế trong môi trường production (final container image), chỉ chứa các tệp tin thực thi tối giản nhất và mã nguồn để chạy ứng dụng.
### 3. Tại sao final image lại nhỏ hơn đáng kể?
Kích thước image của phiên bản Advanced (`my-agent:advanced`) giảm tới **86.6%** so với phiên bản Develop (`my-agent:develop`).
- **Develop (my-agent:develop):** **424 MB** (DISK USAGE hiển thị 1.66GB do cache và các layer lưu trên disk).
- **Production (my-agent:advanced):** **56.6 MB** (DISK USAGE hiển thị 236MB).
- **Lý do kích thước nhỏ hơn:**
  1. **Tách biệt Compiler & Build Tools:** Final image ở Stage 2 hoàn toàn không chứa các tool biên dịch nặng như `gcc`, `libpq-dev` hay bộ quản lý gói hệ thống (apt cache). Các tool này chỉ nằm lại ở Stage 1 (builder) và bị vứt bỏ.
  2. **Loại bỏ pip cache và files trung gian:** Khi cài đặt package bằng pip, rất nhiều file cache và file trung gian được tạo ra. Bằng cách chỉ copy thư mục package đầu ra `/root/.local` sang Stage 2, ta loại bỏ hoàn toàn các file rác này.
  3. **Tận dụng tối đa Slim Base Image:** Cả 2 stage đều dùng `python:3.11-slim` làm xuất phát điểm thay vì phiên bản `python:3.11` đầy đủ, giúp giảm dung lượng gốc ban đầu của base OS từ ~1GB xuống còn ~120MB.

### Exercise 2.4: Docker Compose stack

- **Kiến trúc dịch vụ (Architecture Diagram):**
  ```mermaid
  graph TD
      Client[Client / Browser] -->|Cổng 80| Nginx[Nginx Reverse Proxy & Load Balancer]
      Nginx -->|Mạng bridge 'internal'| Agent[FastAPI AI Agent Container]
      Agent -->|Lưu session / Rate limit| Redis[Redis Container]
      Agent -->|Tìm kiếm ngữ cảnh RAG| Qdrant[Qdrant Container]
  ```

- **Các Services được khởi tạo:**
  1. `agent`: FastAPI AI Agent (chạy trên cổng `8000` nội bộ).
  2. `redis`: Lưu trữ dữ liệu session, lịch sử chat và hỗ trợ rate limiting.
  3. `qdrant`: Vector Database phục vụ cho các tác vụ RAG của agent.
  4. `nginx`: Reverse proxy & Load balancer lắng nghe trên cổng `80` (và `443`), tiếp nhận request từ client và phân phối đến agent backend.

- **Phương thức giao tiếp giữa các services:**
  - Tất cả các container đều tham gia vào mạng ảo bridge `internal` do Docker Compose tạo ra.
  - Chúng phân giải DNS nội bộ dựa trên **Service Name** (ví dụ: `redis`, `qdrant`, `agent`).
  - Chỉ có `nginx` là expose cổng `80` và `443` ra máy host để tiếp nhận traffic từ ngoài internet. Các service còn lại (`agent`, `redis`, `qdrant`) hoàn toàn bị cô lập và bảo mật bên trong mạng nội bộ.

---
### Exercise 3.1: Deploy Railway
**Health check**
```bash
curl https://batch02-day12cloudinfrasanddeployment-production-e3a9.up.railway.app/health

"status":"ok","uptime_seconds":5021.5,"platform":"Railway","timestamp":"2026-06-12T10:26:41.512064+00:00"
```
**Agent endpoint**

```bash
curl https://batch02-day12cloudinfrasanddeployment-production-e3a9.up.railway.app/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'

"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","platform":"Railway"
```

### Exercise 3.2: Deploy Render (So sánh `render.yaml` và `railway.toml`)
Dưới đây là bảng so sánh chi tiết giữa file cấu hình Infrastructure as Code (IaC) của Render (`render.yaml`) và file cấu hình dịch vụ của Railway (`railway.toml`):
|
 Tiêu chí 
|
`railway.toml`
 (Railway) 
|
`render.yaml`
 (Render) 
|
|
:---
|
:---
|
:---
|
|
**
Định dạng (Format)
**
|
 TOML 
|
 YAML 
|
|
**
Phạm vi cấu hình (Scope)
**
|
**
Single Service:
**
 Chỉ cấu hình cho một dịch vụ cụ thể chứa tệp này. 
|
**
Multi-Service (IaC / Blueprint):
**
 Cấu hình toàn bộ hạ tầng (nhiều web service, database, redis, worker, cron...) trong một file duy nhất. 
|
|
**
Khởi tạo Database/Redis
**
|
 Không hỗ trợ khai báo. Phải khởi tạo thủ công trên Dashboard của Railway. 
|
 Hỗ trợ khai báo trực tiếp (ví dụ: 
`type: keyvalue`
 cho Redis, 
`type: database`
 cho Postgres). 
|
|
**
Biến môi trường (Env Vars)
**
|
 Không cấu hình trong file. Phải set qua CLI hoặc Dashboard. 
|
 Cho phép khai báo trực tiếp danh sách 
`envVars`
, hỗ trợ sinh giá trị ngẫu nhiên (
`generateValue: true`
) hoặc yêu cầu nhập tay (
`sync: false`
). 
|
|
**
Command build & start
**
|
 Khai báo startCommand (
`startCommand`
), build tự động qua Nixpacks/Dockerfile. 
|
 Khai báo chi tiết cả 
`buildCommand`
 (ví dụ: cài pip requirements) và 
`startCommand`
. 
|
|
**
Bộ nhớ đệm & Ổ đĩa mount
**
|
 Cấu hình Volume phải thực hiện trên giao diện web của Railway. 
|
 Khai báo trực tiếp ổ cứng gắn ngoài (
`disk`
) cùng đường dẫn mount (
`mountPath`
) và dung lượng. 
|
#### Điểm khác biệt cốt lõi:
1. **Kiến trúc Blueprint (IaC):** `render.yaml` đóng vai trò là một tệp thiết kế hệ thống hoàn chỉnh (Blueprint). Chỉ cần 1 file này, Render có thể tự động dựng lên cả Web App, Database Postgres, Redis Cache và kết nối chúng lại. Trong khi đó, `railway.toml` chỉ tập trung cấu hình cách chạy và kiểm tra sức khỏe (health check) cho một service đơn lẻ.
2. **Quản lý Secrets & Biến môi trường:** `render.yaml` cung cấp cơ chế bảo mật tốt cho IaC bằng cách định nghĩa key nhưng không lưu value (set `sync: false` để nhập sau trên dashboard), hoặc tự sinh key ngẫu nhiên. Với Railway, các biến này được quản lý hoàn toàn bên ngoài file cấu hình để tránh rò rỉ.
3. **Cách thức Build:** Railway mặc định ưu tiên sử dụng Nixpacks (tự động phân tích code để build môi trường phù hợp), trong khi Render Blueprint yêu cầu chỉ định rõ Runtime (`runtime: python`) và các câu lệnh cài đặt thủ công.

## Part 4: API Security
###  Exercise 4.1: API Key authentication
- API key được check ở dependency `verify_api_key`
- client gửi key qua header `X-API-Key`
- thiếu hoặc sai key -> trả **401**
- rotate key bằng cách đổi giá trị key trong environment/config rồi restart hoặc redeploy

### Exercise 4.2 — JWT authentication
Flow:
- Gọi `POST /auth/token` với `username` và `password`
- Server tạo JWT chứa `sub`, `role`, `iat`, `exp`
- Client gọi `POST /ask` với header `Authorization: Bearer <token>`
- Dependency `verify_token` decode và verify chữ ký + expiry
- Token hết hạn -> **401**, token sai -> **403**

### Exercise 4.3: Rate limiting
- **Thuật toán:** Sliding Window (Sliding Window Log) sử dụng hàng đợi `deque` để lưu trữ và lọc timestamps của các request trong window 60 giây.
- **Giới hạn (Limit):**
  - User thường: 10 requests/phút (`rate_limiter_user`).
  - Admin: 100 requests/phút (`rate_limiter_admin`).
- **Cách bypass cho admin:** Hệ thống áp dụng Role-based Rate Limiting. Trong `app.py`, hệ thống kiểm tra `role` của user: nếu `role == "admin"`, hệ thống tự động sử dụng bộ giới hạn dành riêng cho admin (`rate_limiter_admin`) với cấu hình cao hơn (100 req/phút) để nới lỏng giới hạn thay vì bỏ qua hoàn toàn.

---

## Part 6: Final Project

**Project:** `06-lab-complete`  
**Tên agent:** Long Châu AI Triage Agent  
**Live deployment:** API `https://ai-agent-production-2q2r.onrender.com`, Static Shell `https://longchau-static.onrender.com`

### Functional Requirements
- **Agent works:** API trả lời được các route nghiệp vụ: `factual`, `advisory_gather`, `advisory_handoff`, `out_of_scope`, `crisis`.
- **Conversation history:** Lịch sử chat được lưu trữ tập trung trong Redis theo `session_id` để duy trì ngữ cảnh.
- **Error handling:** Trả về lỗi `401` nếu thiếu/sai API key, `429` nếu vượt rate limit, và `402` nếu vượt budget tháng.

### Docker & Configuration
- **Dockerfile:** Multi-stage Dockerfile tại `06-lab-complete/Dockerfile` sử dụng `python:3.12-slim`, chạy dưới quyền non-root `agent` và tích hợp `HEALTHCHECK`.
- **Docker Compose:** Tách biệt `nginx` (cổng 80) làm Load Balancer, `agent` (3 replicas), và `redis` làm cơ sở lưu trữ dữ liệu.
- **Config:** Quản lý cấu hình qua `app/config.py` đọc từ environment variables.

### Security
- **API Key auth:** Xác thực qua header `X-API-Key` so khớp với `AGENT_API_KEY`.
- **Rate limiting:** Thuật toán Sliding Window sử dụng Redis `ZSET` giới hạn 10 requests/phút.
- **Cost guard:** Quản lý ngân sách hàng tháng cho mỗi user sử dụng Redis keys.

### Reliability
- **Health check:** `GET /health` (liveness).
- **Readiness check:** `GET /ready` (readiness check kết nối Redis).
- **Graceful shutdown:** Xử lý tín hiệu `SIGTERM` để hoàn thành request đang xử lý trước khi dừng container.
- **Stateless design:** Không lưu state trong bộ nhớ RAM cục bộ của các container backend.

### Deployment
- **API URL:** `https://ai-agent-production-2q2r.onrender.com`
- **Static Shell:** `https://longchau-static.onrender.com`
- Cấu hình file Blueprint `render.yaml` tự động deploy cả 3 dịch vụ trên Render và tự động liên kết cơ sở dữ liệu Redis.

