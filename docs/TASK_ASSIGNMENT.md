# Tài liệu cố định module, hàm và phân công công việc

Tài liệu này dùng để giao task cho các thành viên trong nhóm. Mỗi file bên dưới được cố định vai trò, kỹ thuật AI phụ trách, các hàm/lớp chính và phạm vi được phép chỉnh sửa. Khi một người nhận task, chỉ nên sửa trong đúng nhóm file được giao để tránh chồng chéo.

## Rule làm việc

### Rule chung

- Luôn đọc `docs/STRUCTURE.md` và phần file liên quan trong tài liệu này trước khi sửa code.
- Không đổi tên file, class, hàm public khi chưa thống nhất với nhóm.
- Không viết lại luật cờ thủ công; mọi xử lý luật cờ đi qua `python-chess` và `ChessEnv`.
- Không đặt thuật toán AI trong UI hoặc script CLI. UI chỉ nhận input, hiển thị bàn cờ và gọi agent.
- Không đặt logic giao diện vào `src/agents`, `src/search`, `src/rl`, `src/evaluation`.
- Mọi thuật toán chọn nước đi phải đi qua class agent trong `src/agents`.
- Q-learning chỉ cập nhật trong `src/rl` hoặc `src/training`, không cập nhật trong lúc agent đang chọn nước để đánh giá.
- Kết quả chạy thử được lưu trong `data/` hoặc `experiments/`; không commit file runtime như `.pkl`, `.csv`, `.json`, `.png` nếu đó chỉ là kết quả tạm.
- Mỗi lần sửa code phải chạy kiểm tra tối thiểu:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src scripts
```

### Rule khi chia task

- Mỗi task phải ghi rõ: người phụ trách, file được sửa, đầu ra cần bàn giao, test cần chạy.
- Một người chỉ sửa ngoài phạm vi task khi có lý do rõ ràng và báo lại cho nhóm.
- Nếu sửa public API, phải cập nhật README, tài liệu module và test liên quan.
- Nếu tạo kết quả thực nghiệm để đưa vào báo cáo, phải ghi lại config, lệnh chạy, ngày chạy và đường dẫn file kết quả.
- Nếu task bị lỗi hoặc chưa xong, ghi trạng thái là "đang làm" hoặc "cần hỗ trợ", không đánh dấu hoàn thành.

## Skill cần có

| Mảng | Skill kỹ thuật | Skill báo cáo/demo | File liên quan |
|---|---|---|---|
| Bàn cờ và trạng thái | `python-chess`, FEN, legal move, luật nhập thành/phong cấp/en passant | Giải thích biểu diễn trạng thái và vì sao không tự viết luật cờ | `src/board/*`, `tests/test_board.py` |
| Hàm đánh giá | Material, piece-square table, mobility, king safety, center control | Giải thích từng heuristic và ví dụ thế cờ trước/sau | `src/evaluation/*` |
| Minimax/Alpha-Beta | Game tree, depth-limited search, pruning, move ordering | Vẽ cây tìm kiếm, so sánh node visited/pruned | `src/search/*`, `src/agents/minimax_agent.py`, `src/agents/alphabeta_agent.py` |
| Q-learning | Q-table, epsilon-greedy, Bellman update, reward shaping, Q-value quantization | Trình bày công thức Q, self-play và research gap state-action explosion | `src/rl/*`, `src/training/self_play.py` |
| Hybrid model | Kết hợp Alpha-Beta với Q-value, confidence-aware bonus, chỉnh `lambda` | Giải thích `FinalScore = AB + lambda * confidence * QValue` | `src/agents/hybrid_agent.py` |
| Thực nghiệm | YAML config, đo thời gian, CSV/JSON, biểu đồ | Làm bảng so sánh 3 model và nhận xét kết quả | `scripts/evaluate.py`, `experiments/`, `notebooks/` |
| Demo | CLI, input UCI/SAN, xử lý lỗi người dùng | Demo chơi được và giải thích nước đi AI | `src/ui/app.py`, `scripts/play.py` |
| Kiểm thử | `pytest`, test luật cờ, test thuật toán, test lưu/load | Ghi checklist test vào báo cáo hoặc phụ lục | `tests/*` |

## Task theo thành viên

Nhóm đồ án có 2 thành viên chính, chia theo vai trò chính/phụ để tránh bỏ sót module.

| Thành viên | Vai trò chính | File phụ trách chính | Đầu ra cần bàn giao |
|---|---|---|---|
| Nguyễn Thành Phong | Luật cờ, tìm kiếm, demo chạy chương trình | `src/board/*`, `src/search/*`, `src/agents/minimax_agent.py`, `src/agents/alphabeta_agent.py`, `src/ui/app.py`, `scripts/play.py` | Board sinh nước hợp lệ, Minimax/Alpha-Beta chọn nước hợp lệ, demo chơi được |
| Trần An Kỳ | Hàm đánh giá, Q-learning, hybrid, thực nghiệm | `src/evaluation/*`, `src/rl/*`, `src/training/self_play.py`, `src/agents/hybrid_agent.py`, `scripts/train.py`, `scripts/evaluate.py` | Self-play tạo Q-table, Hybrid chạy được, kết quả so sánh 3 model |
| Cả hai | Test, báo cáo, kiểm tra cuối | `tests/*`, `README.md`, `docs/*`, `experiments/`, `notebooks/analysis.ipynb` | Test pass, tài liệu khớp code, bảng/biểu đồ đủ đưa vào báo cáo |

### Checklist task của Nguyễn Thành Phong

- Hoàn thiện `ChessEnv`: tạo/reset/copy bàn cờ, push/pop nước đi, trả FEN/result/outcome.
- Viết test luật đặc biệt: nhập thành, phong cấp, bắt tốt qua đường.
- Hoàn thiện Minimax và Alpha-Beta: đúng perspective, có thống kê node, có move ordering.
- Đảm bảo `MinimaxAgent` và `AlphaBetaAgent` luôn trả `chess.Move` hợp lệ hoặc `None` khi không còn nước.
- Hoàn thiện demo CLI: nhập UCI/SAN, chọn agent, chọn độ sâu, thông báo lỗi rõ ràng.

### Checklist task của Trần An Kỳ

- Hoàn thiện `evaluate`: material, piece-square, mobility, king safety, center, threat, terminal state.
- Hoàn thiện `QLearning`: epsilon-greedy, update Q-value, save/load Q-table, seed để tái lập.
- Hoàn thiện quantized Q-learning: `q_value_step`, `q_value_clip`, metric `unique_states`, `actions_per_state`.
- Hoàn thiện reward shaping: terminal reward, thưởng/phạt theo cải thiện vị trí, bắt quân, chiếu, phong cấp nếu có.
- Hoàn thiện `self_play`: chơi nhiều ván, log kết quả, lưu Q-table định kỳ.
- Hoàn thiện `HybridAgent`: dùng Alpha-Beta cộng Q-value theo hệ số `lambda`.
- Hoàn thiện Confidence-Aware Hybrid: Q bonus nhân với `N(s,a)/(N(s,a)+k)`.
- Hoàn thiện evaluate script: round-robin 3 model, xuất CSV/JSON, thống kê win/loss/draw, thời gian, node.

### Checklist chung trước khi nộp

- README có lệnh cài đặt, train, evaluate, play.
- `docs/STRUCTURE.md` khớp với cấu trúc repo thật.
- `docs/TASK_ASSIGNMENT.md` ghi rõ rule, skill, task và Definition of Done.
- Chạy được:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src scripts
.venv/bin/python scripts/train.py --config config/config.yaml --games 2 --max-moves 20 --save-every 1
.venv/bin/python scripts/evaluate.py --config config/config.yaml --games 1 --depth 1 --max-moves 10
```

- Kết quả thực nghiệm cuối được đặt trong `experiments/results`.

## Nguyên tắc chung

- Không đổi tên file, class, hàm public khi chưa thống nhất với cả nhóm.
- Không đưa logic tìm kiếm vào module giao diện hoặc script chạy lệnh.
- Không đưa logic giao diện vào `src/agents`, `src/search`, `src/rl`, `src/evaluation`.
- Mọi thuật toán chọn nước đi phải đi qua class agent trong `src/agents`.
- Mọi xử lý luật cờ phải đi qua `python-chess` và lớp `ChessEnv`.
- Mọi kết quả huấn luyện/thực nghiệm sinh ra được lưu trong `data/` hoặc `experiments/`, không commit file `.pkl`, `.csv`, `.json`, `.png` kết quả chạy thử.
- Sau khi sửa code, chạy tối thiểu:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src scripts
```

## Luồng xử lý chính

1. `scripts/train.py` đọc `config/config.yaml`.
2. `src/training/self_play.py` tạo ván tự chơi và cập nhật Q-table.
3. `src/rl/q_learning.py` lưu công thức Q-learning và chọn hành động epsilon-greedy.
4. `src/agents/hybrid_agent.py` dùng Q-table kết hợp Alpha-Beta để chọn nước.
5. `scripts/evaluate.py` cho ba mô hình đấu vòng tròn và xuất kết quả.
6. `scripts/play.py` mở giao diện console để người dùng chơi với AI.

## Bảng phân công nhanh

| Mảng việc | File chính | Người phù hợp | Đầu ra cần bàn giao |
|---|---|---|---|
| Bàn cờ và trạng thái | `src/board/chess_env.py`, `src/board/state.py` | Thành viên nắm luật cờ | Sinh nước hợp lệ, mã hóa trạng thái ổn định |
| Hàm đánh giá | `src/evaluation/evaluator.py`, `src/evaluation/piece_tables.py` | Thành viên phụ trách heuristic | Điểm vị trí hợp lý, test tình huống mẫu |
| Tìm kiếm | `src/search/minimax.py`, `src/search/alphabeta.py`, `src/search/move_ordering.py` | Thành viên phụ trách thuật toán | Minimax/Alpha-Beta đúng, có thống kê node |
| Agent | `src/agents/*.py` | Thành viên tích hợp mô hình | Ba model chọn nước hợp lệ |
| Q-learning | `src/rl/*.py`, `src/training/self_play.py` | Thành viên học tăng cường | Self-play tạo Q-table, reward có giải thích |
| Đánh giá thực nghiệm | `scripts/evaluate.py`, `experiments/` | Thành viên làm báo cáo kết quả | CSV/JSON/biểu đồ so sánh ba mô hình |
| Giao diện | `src/ui/app.py`, `scripts/play.py` | Thành viên demo | Chơi được với AI, thông báo lỗi rõ ràng |
| Kiểm thử | `tests/*.py` | Thành viên QA | Test cho luật cờ, tìm kiếm, Q-learning |

## Chi tiết từng file

### `src/board/chess_env.py`

Vai trò: lớp bao quanh `python-chess` để các module khác không thao tác trực tiếp quá nhiều với board.

Kỹ thuật liên quan:

- Biểu diễn bàn cờ bằng FEN.
- Sinh nước đi hợp lệ bằng `python-chess`.
- Kiểm tra kết thúc ván, chiếu hết, hòa, luật đặc biệt.

Hàm/lớp cố định:

- `ChessEnv.__init__(fen=None)`: tạo bàn cờ mới hoặc từ FEN.
- `reset(fen=None)`: đưa bàn cờ về trạng thái ban đầu hoặc FEN mới.
- `copy()`: tạo bản sao môi trường, giữ cả lịch sử nước đi.
- `legal_moves()`: trả danh sách nước đi hợp lệ.
- `push(move)`: thực hiện một nước.
- `push_uci(move_uci)`: kiểm tra và thực hiện nước đi dạng UCI.
- `pop()`: hoàn tác một nước.
- `is_terminal()`: kiểm tra ván đã kết thúc.
- `outcome()`: trả `chess.Outcome` nếu ván đã có kết quả.
- `result()`: trả kết quả ván theo chuẩn `1-0`, `0-1`, `1/2-1/2`, `*`.
- `fen()`: trả FEN hiện tại.
- `san(move)`: trả ký hiệu SAN cho nước đi.

Task nên giao:

- Thêm helper reset bàn cờ nếu cần.
- Thêm test cho nhập thành, phong cấp, bắt tốt qua đường.

Không nên làm:

- Không viết lại luật cờ thủ công.
- Không đặt logic Minimax/Q-learning vào file này.

### `src/board/state.py`

Vai trò: mã hóa trạng thái bàn cờ cho Q-learning.

Kỹ thuật liên quan:

- State abstraction.
- Rút gọn FEN để giảm số lượng key trong Q-table.
- Vector đặc trưng cho hướng mở rộng dùng hàm xấp xỉ.

Hàm cố định:

- `state_key(board)`: trả key gồm vị trí quân, lượt đi, quyền nhập thành, en passant.
- `feature_vector(board)`: trả vector đặc trưng gồm chênh lệch quân, kiểm soát trung tâm, lượt đi, quyền nhập thành, trạng thái chiếu, mobility, an toàn vua, cấu trúc tốt.
- `resolve_state_key_fn(name)`: chọn state representation `full` hoặc `compact` cho train/evaluate/play.

Task nên giao:

- So sánh hiệu quả giữa `state_key` và `feature_vector`.
- Thêm đặc trưng an toàn vua, mobility, pawn structure.

Không nên làm:

- Không lưu Q-table tại đây.
- Không chọn nước đi tại đây.

### `src/evaluation/piece_tables.py`

Vai trò: chứa giá trị quân và bảng điểm vị trí.

Kỹ thuật liên quan:

- Material evaluation.
- Piece-square table.
- Khuyến khích quân phát triển và kiểm soát trung tâm.

Hàm/biến cố định:

- `PIECE_VALUES`: giá trị quân cờ.
- `position_bonus(piece, square)`: điểm vị trí theo màu quân.

Task nên giao:

- Tinh chỉnh bảng điểm vị trí theo khai cuộc/trung cuộc/tàn cuộc.
- Viết test kiểm tra quân đen được mirror đúng.

Không nên làm:

- Không kiểm tra chiếu hết tại đây.
- Không đọc/ghi file tại đây.

### `src/evaluation/evaluator.py`

Vai trò: hàm đánh giá tổng hợp trạng thái bàn cờ.

Kỹ thuật liên quan:

- Material score.
- Piece-square table.
- Mobility.
- King safety.
- Center control.
- Threat/hanging piece score.
- Check/checkmate/stalemate handling.

Hàm cố định:

- `evaluate(board, perspective=chess.WHITE)`: trả điểm dương nếu tốt cho `perspective`.

Hàm nội bộ:

- `_terminal_score(board)`: xử lý chiếu hết/hòa.
- `_mobility_score(board)`: chênh lệch số nước hợp lệ.
- `_king_safety(board)`: điểm an toàn vua.
- `_center_control(board)`: điểm kiểm soát trung tâm.
- `_pawn_structure_score(board)`: điểm tốt thông, tốt cô lập, tốt chồng.
- `_development_score(board)`: điểm phát triển mã/tượng và nhập thành.
- `_threat_score(board)`: phạt quân bị tấn công mà không được bảo vệ.

Task nên giao:

- Cân chỉnh trọng số heuristic.
- Thêm test cho mate, stalemate, ăn quân, kiểm soát trung tâm.

Không nên làm:

- Không đổi dấu theo `board.turn`; phải dùng `perspective`.
- Không chọn nước đi trong evaluator.

### `src/search/minimax.py`

Vai trò: triển khai Minimax thuần cho Mô hình 1.

Kỹ thuật liên quan:

- Game tree.
- MAX-MIN.
- Tìm kiếm theo độ sâu hữu hạn.

Hàm cố định:

- `minimax(env, depth, maximizing, evaluate, perspective)`: trả điểm tốt nhất theo góc nhìn người chơi gốc.

Task nên giao:

- Thêm thống kê số node nếu cần so sánh sâu hơn.
- Test depth 1, 2 với vị trí có nước ăn quân rõ ràng.

Không nên làm:

- Không thêm Alpha-Beta vào file này.
- Không thêm Q-learning vào file này.

### `src/search/alphabeta.py`

Vai trò: triển khai Alpha-Beta Pruning cho Mô hình 2 và Mô hình 3.

Kỹ thuật liên quan:

- Alpha-Beta Pruning.
- Cắt tỉa cây trò chơi.
- Đếm node duyệt và node bị cắt.

Class/hàm cố định:

- `SearchStats`: lưu `visited`, `pruned`, `cache_hits`.
- `alphabeta(env, depth, alpha, beta, maximizing, evaluate, stats, perspective, transposition=None)`: trả điểm tìm kiếm có cắt tỉa, có thể dùng transposition table.

Task nên giao:

- Kiểm tra số node giữa Minimax và Alpha-Beta.
- Thêm transposition table nếu nhóm muốn mở rộng.

Không nên làm:

- Không đọc Q-table tại đây.
- Không xử lý giao diện tại đây.

### `src/search/move_ordering.py`

Vai trò: sắp xếp nước đi để Alpha-Beta cắt tỉa hiệu quả hơn.

Kỹ thuật liên quan:

- Move Ordering.
- Ưu tiên capture, promotion, check.

Hàm cố định:

- `order_moves(board, moves)`: trả danh sách nước đi đã sắp xếp.

Task nên giao:

- Cải tiến MVV-LVA: quân ăn có giá trị thấp ăn quân bị ăn có giá trị cao.
- Thêm killer move/history heuristic nếu có thời gian.

Không nên làm:

- Không tự chọn nước đi cuối cùng tại đây.

### `src/agents/base_agent.py`

Vai trò: interface chung cho mọi agent.

Kỹ thuật liên quan:

- Abstraction.
- Polymorphism.

Class cố định:

- `BaseAgent.choose_move(env)`: mọi agent phải implement và trả `chess.Move`.

Task nên giao:

- Thêm type hint hoặc metadata agent nếu cần.

Không nên làm:

- Không đặt thuật toán cụ thể vào base class.

### `src/agents/minimax_agent.py`

Vai trò: Mô hình 1, chọn nước bằng Minimax thuần.

Kỹ thuật liên quan:

- Root move selection.
- Minimax.
- Evaluation theo `perspective`.

Class cố định:

- `MinimaxAgent(depth=3)`.
- `choose_move(env)`.

Task nên giao:

- Thử nghiệm các độ sâu khác nhau.
- Đo thời gian chọn nước so với Alpha-Beta.

Không nên làm:

- Không thêm Q-value vào model này.

### `src/agents/alphabeta_agent.py`

Vai trò: Mô hình 2, chọn nước bằng Alpha-Beta.

Kỹ thuật liên quan:

- Alpha-Beta.
- Move Ordering.
- Search statistics.

Class cố định:

- `AlphaBetaAgent(depth=4, use_transposition=True)`.
- `choose_move(env)`.
- `last_stats`: lưu thống kê lần chọn nước gần nhất.

Task nên giao:

- So sánh `visited/pruned` với Minimax.
- Tối ưu thứ tự nước đi.

Không nên làm:

- Không phụ thuộc Q-table.

### `src/agents/hybrid_agent.py`

Vai trò: Mô hình 3, kết hợp Alpha-Beta và Q-learning.

Kỹ thuật liên quan:

- Hybrid evaluation.
- Alpha-Beta root search.
- Q-value bias.
- Confidence-aware Q bias.
- Công thức: `FinalScore = AlphaBetaScore + λ × confidence × QValue`.

Class cố định:

- `HybridAgent(q_table, depth=4, lam=0.5, use_transposition=True)`.
- `choose_move(env)`.
- `last_stats`: thống kê Alpha-Beta.

Task nên giao:

- Thử nhiều giá trị `lambda`.
- Thử bật/tắt `use_confidence` và các giá trị `confidence_k`.
- So sánh hybrid trước và sau self-play.
- Kiểm tra Q-table có làm model chọn nước khác Alpha-Beta hay không.

Không nên làm:

- Không cập nhật Q-table trong lúc chọn nước.
- Không huấn luyện self-play tại đây.

### `src/rl/q_learning.py`

Vai trò: triển khai Q-learning và lưu Q-table.

Kỹ thuật liên quan:

- Q-table.
- Epsilon-greedy.
- Exploration vs Exploitation.
- Bellman update.
- Epsilon decay.
- Optional Q-value quantization để kiểm tra research gap.

Class/hàm cố định:

- `QLearning.__init__`.
- `get(s, a)`.
- `best_value(s, actions)`.
- `select(s, actions)`.
- `update(s, a, r, s_next, next_actions)`.
- `decay_epsilon()`.
- `save(path)`.
- `load(path)`.
- `mean_abs_q()`: thống kê độ lớn trung bình của Q-value để theo dõi hội tụ.
- `unique_states()`: số state riêng biệt trong Q-table.
- `actions_per_state()`: số action trung bình trên mỗi state.

Task nên giao:

- Dùng `seed` để tái lập kết quả.
- So sánh `full`, `compact`, `compact + quantized` bằng `q_value_step` và `q_value_clip`.
- Ghi log diễn biến trung bình Q-value.
- Thử tham số `alpha`, `gamma`, `epsilon`.

Không nên làm:

- Không gọi Alpha-Beta từ file này.
- Không xử lý luật cờ tại đây.

### `src/rl/reward.py`

Vai trò: định nghĩa reward cho self-play.

Kỹ thuật liên quan:

- Terminal reward.
- Reward shaping.
- Chênh lệch điểm đánh giá trước/sau nước đi.

Hàm cố định:

- `terminal_reward(board, color)`: thưởng thắng/thua theo màu người vừa đi.
- `shaping_reward(eval_before, eval_after, scale=0.01)`: thưởng nhỏ khi thế cờ cải thiện.
- `move_reward(board_before, move, board_after)`: thưởng nhỏ cho bắt quân, chiếu, phong cấp.

Task nên giao:

- Cân chỉnh hệ số shaping.
- Thêm reward cho chiếu, bắt quân, phong cấp.

Không nên làm:

- Không cập nhật Q-table tại đây.

### `src/rl/replay.py`

Vai trò: lưu kinh nghiệm self-play.

Kỹ thuật liên quan:

- Replay buffer.
- Giới hạn bộ nhớ bằng `deque(maxlen=...)`.

Class cố định:

- `ReplayBuffer(capacity=100_000)`.
- `add(transition)`.
- `sample(batch_size)`.
- `stats()`.
- `__len__()`.

Task nên giao:

- Thêm hàm sample minibatch nếu mở rộng sang Deep Q-learning.
- Xuất thống kê số transition.

Không nên làm:

- Không tự train trong buffer.

### `src/training/self_play.py`

Vai trò: vòng huấn luyện tự chơi cho Q-learning.

Kỹ thuật liên quan:

- Self-play.
- Epsilon-greedy action selection.
- Transition `(s, a, r, s_next, next_actions)`.
- Reward shaping.
- Lưu Q-table theo chu kỳ.

Hàm cố định:

- `self_play_game(q, env, max_moves, replay=None)`.
- `train(q, num_games, max_moves, save_every, q_table_path, history_path=None)`.

Task nên giao:

- Thêm progress bar bằng `tqdm`.
- Ghi log `epsilon`, số trạng thái Q, kết quả thắng/hòa/thua.
- Xuất lịch sử train dạng CSV để đưa vào phần thực nghiệm.
- Chạy thí nghiệm nhiều cấu hình trong `config/config.yaml`.

Không nên làm:

- Không chọn nước bằng Alpha-Beta trong self-play hiện tại, trừ khi mở rộng rõ thành self-play hybrid.

### `src/ui/app.py`

Vai trò: giao diện console để demo chơi với AI.

Kỹ thuật liên quan:

- Input UCI/SAN.
- Hiển thị bàn cờ Unicode.
- Người chơi cầm trắng, AI cầm đen.

Hàm cố định:

- `run(agent)`.

Task nên giao:

- Nâng cấp lên pygame nếu cần giao diện đồ họa.
- Thêm lựa chọn người chơi cầm trắng/đen.
- Thêm hiển thị nước đi cuối, thời gian AI suy nghĩ.

Không nên làm:

- Không viết thuật toán tìm kiếm trong UI.

### `scripts/train.py`

Vai trò: command line để huấn luyện Q-learning.

Kỹ thuật liên quan:

- Đọc YAML config.
- Override nhanh số ván, max moves, save every.

Lệnh mẫu:

```bash
python scripts/train.py --config config/config.yaml
python scripts/train.py --config config/config.yaml --games 10 --max-moves 40 --save-every 5
python scripts/train.py --config config/config.yaml --resume --seed 7
python scripts/train.py --config config/config.yaml --state-representation compact --q-value-step 0.05 --q-value-clip 5.0
```

Task nên giao:

- Kiểm tra option `--seed`, `--resume`, `--q-table`, `--history`, `--state-representation`, `--q-value-step`, `--q-value-clip`.
- Đưa file history CSV vào phân tích kết quả.

Không nên làm:

- Không đặt thuật toán Q-learning trực tiếp trong script.

### `scripts/evaluate.py`

Vai trò: chạy thực nghiệm so sánh ba mô hình.

Kỹ thuật liên quan:

- Round-robin tournament.
- Opening robustness benchmark.
- Đổi màu trắng/đen.
- Đo thời gian chọn nước.
- Ghi node visited/pruned.
- Ghi cache hit nếu bật transposition table.
- Xuất CSV/JSON.

Lệnh mẫu:

```bash
python scripts/evaluate.py --config config/config.yaml
python scripts/evaluate.py --config config/config.yaml --games 2 --depth 2 --max-moves 40
python scripts/evaluate.py --config config/config.yaml --q-table data/q_tables/q_quantized.pkl --state-representation compact
python scripts/evaluate.py --config config/config.yaml --q-table data/q_tables/q_quantized.pkl --state-representation compact --openings suite
```

File xuất:

- `experiments/results/games.csv`.
- `experiments/results/summary.json`.

Task nên giao:

- Vẽ biểu đồ từ CSV/JSON.
- Thêm Elo đơn giản hoặc bảng xếp hạng.
- So sánh thời gian trung bình theo độ sâu.
- So sánh Hybrid dùng Q-table `full`, `compact`, `quantized`.
- So sánh robustness trên nhiều khai cuộc.

Không nên làm:

- Không huấn luyện Q-table tại đây.

### `scripts/play.py`

Vai trò: command line để chơi với một agent.

Kỹ thuật liên quan:

- Agent factory.
- Load Q-table nếu chơi với hybrid.
- Fallback Q-table rỗng nếu chưa huấn luyện.

Lệnh mẫu:

```bash
python scripts/play.py --agent minimax
python scripts/play.py --agent alphabeta --depth 3
python scripts/play.py --agent hybrid --q-table data/q_tables/q_table.pkl --human-color black
python scripts/play.py --agent hybrid --q-table data/q_tables/q_quantized.pkl --state-representation compact
```

Task nên giao:

- Kiểm tra option `--depth`.
- Kiểm tra option `--q-table`.
- Kiểm tra option `--human-color`.

Không nên làm:

- Không đặt vòng lặp UI trong script; vòng lặp thuộc `src/ui/app.py`.

### `config/config.yaml`

Vai trò: cấu hình tham số hệ thống.

Nhóm tham số:

- `search`: độ sâu tìm kiếm, bật/tắt move ordering.
- `q_learning`: `alpha`, `gamma`, `epsilon`, decay.
- `q_learning.q_value_step`, `q_learning.q_value_clip`: bật/tắt lượng tử Q-value.
- `hybrid`: hệ số `lambda`.
- `training`: số ván, max moves, đường dẫn Q-table.
- `training.history_path`: đường dẫn CSV ghi lịch sử self-play.
- `evaluation`: số ván mỗi cặp, thư mục kết quả.

Task nên giao:

- Tạo nhiều preset cấu hình cho demo nhanh và chạy thật.
- Ghi lại cấu hình nào dùng cho báo cáo.

### `tests/test_board.py`

Vai trò: test module bàn cờ.

Hiện có:

- Kiểm tra vị trí ban đầu có 20 nước hợp lệ.
- Kiểm tra reset bàn cờ.
- Kiểm tra nhập thành, phong cấp, en passant.

Task nên giao:

- Test nhập thành, phong cấp, en passant.
- Test FEN tùy chỉnh.

### `tests/test_search.py`

Vai trò: test tìm kiếm và hàm đánh giá.

Hiện có:

- Alpha-Beta trả nước hợp lệ.
- Evaluation đổi perspective đúng.
- Minimax dùng góc nhìn root để chọn nước ăn quân.
- Move ordering ưu tiên nước ăn quân giá trị cao.
- Alpha-Beta có thống kê node/cache.

Task nên giao:

- Test Alpha-Beta và Minimax chọn cùng nước ở depth nhỏ.
- Test node pruning lớn hơn 0 trong vị trí phù hợp.

### `tests/test_rl.py`

Vai trò: test Q-learning.

Hiện có:

- Kiểm tra công thức cập nhật Q-value.
- Kiểm tra exploitation khi `epsilon=0`.
- Kiểm tra save/load Q-table.
- Kiểm tra replay sample.

Task nên giao:

- Test epsilon-greedy khi epsilon bằng 0 và 1.
- Test save/load Q-table.

## Gợi ý chia người

### Thành viên 1: Luật cờ và biểu diễn trạng thái

Phụ trách:

- `src/board/chess_env.py`
- `src/board/state.py`
- `tests/test_board.py`

Checklist:

- Đảm bảo mọi nước đi hợp lệ do `python-chess` sinh.
- Viết thêm test luật đặc biệt.
- Tài liệu hóa cách đọc FEN và state key.

### Thành viên 2: Hàm đánh giá

Phụ trách:

- `src/evaluation/evaluator.py`
- `src/evaluation/piece_tables.py`

Checklist:

- Giải thích từng thành phần điểm trong báo cáo.
- Cân chỉnh trọng số.
- Tạo ví dụ trước/sau cho material, center, king safety.

### Thành viên 3: Minimax và Alpha-Beta

Phụ trách:

- `src/search/minimax.py`
- `src/search/alphabeta.py`
- `src/search/move_ordering.py`
- `src/agents/minimax_agent.py`
- `src/agents/alphabeta_agent.py`

Checklist:

- Mô tả cây trò chơi.
- So sánh số node giữa Minimax và Alpha-Beta.
- Giải thích vai trò move ordering.

### Thành viên 4: Q-learning và Hybrid

Phụ trách:

- `src/rl/q_learning.py`
- `src/rl/reward.py`
- `src/rl/replay.py`
- `src/training/self_play.py`
- `src/agents/hybrid_agent.py`

Checklist:

- Giải thích công thức Q-learning.
- Chạy self-play để tạo Q-table.
- So sánh Hybrid trước/sau huấn luyện.

### Thành viên 5: Demo, đánh giá và báo cáo

Phụ trách:

- `src/ui/app.py`
- `scripts/play.py`
- `scripts/train.py`
- `scripts/evaluate.py`
- `experiments/`
- `notebooks/analysis.ipynb`

Checklist:

- Demo chơi với AI được.
- Xuất kết quả thực nghiệm.
- Vẽ biểu đồ win/loss/draw, thời gian trung bình, node visited/pruned.

## Definition of Done

Một task được xem là xong khi:

- Code chạy được bằng lệnh mẫu trong README.
- Không còn lỗi import khi chạy script trực tiếp.
- Có test hoặc ví dụ chạy nhanh.
- Không tạo artifact runtime trong repo ngoài thư mục cho phép.
- Người nhận task cập nhật phần báo cáo tương ứng với module đã sửa.
