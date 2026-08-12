# Công thức nháp — Đồ án Chess AI

Tài liệu tổng hợp **mọi công thức số** dùng trong codebase, kèm ví dụ tính tay
để đối chiếu kết quả với code. Đọc cùng [src/evaluation/evaluator.py](../src/evaluation/evaluator.py),
[src/search/](../src/search/) và [src/rl/](../src/rl/).

Mọi giá trị hằng số dưới đây đều **khớp đúng** với code hiện tại.

---

## 1. Hàm đánh giá vị trí — `evaluate(board, perspective)`

Tổng quát:

$$\boxed{\;\text{Score}_{\text{WHITE}} = M + 0.8 \cdot \text{Mob} + KS + CC + PS + Dev + Th + Chk\;}$$

Nếu `perspective = BLACK`: trả $-\text{Score}_{\text{WHITE}}$.

### 1.1 Giá trị quân (Material) $M$

| Quân | Giá trị |
|---|---|
| Tốt (Pawn) | 100 |
| Mã (Knight) | 320 |
| Tượng (Bishop) | 330 |
| Xe (Rook) | 500 |
| Hậu (Queen) | 900 |
| Vua (King) | 20 000 |

Với mỗi ô có quân:

$$M = \sum_{p \in \text{Trắng}} \bigl(V(p) + \text{PST}(p)\bigr) - \sum_{p \in \text{Đen}} \bigl(V(p) + \text{PST}(p)\bigr)$$

Trong đó $\text{PST}(p)$ là **piece-square bonus** lấy từ [src/evaluation/piece_tables.py](../src/evaluation/piece_tables.py).

> ⚠️ **Quy ước index PST** (code dùng): với quân **trắng** ta tra cứu `table[square]` thẳng (square = `file + rank*8`, A1 = 0, H8 = 63). Với quân **đen**, dùng `table[square ^ 56]`. Bảng được viết theo dạng 8 hàng × 8 cột; với cùng `square`, **trắng và đen được tra cùng giá trị** nhờ đối xứng `square_mirror`.

### 1.2 Cơ động (Mobility) $\text{Mob}$

$$\text{Mob} = 0.8 \cdot \bigl(|\text{legal}_W| - |\text{legal}_B|\bigr)$$

`|legal_C|` = số nước đi hợp lệ khi cho lượt giả định = C (tính bằng cách clone board rồi set `turn = C`).

### 1.3 An toàn vua (King Safety) $KS$

Với mỗi màu $c \in \{W,B\}$, ký hiệu $k_c$ là ô vua, $a_c$ = số quân **đối phương** tấn công ô $k_c$, $d_c$ = số quân **cùng phe** bảo vệ ô $k_c$. Dấu $\sigma_W = +1,\; \sigma_B = -1$.

$$KS = \sigma_W \cdot (4 d_W - 12 a_W) + \sigma_B \cdot (4 d_B - 12 a_B)$$

### 1.4 Kiểm soát trung tâm (Center Control) $CC$

Gọi $C_0 = \{D4, E4, D5, E5\}$ (4 ô trung tâm) và $C_1$ = 12 ô vành đai trung tâm. Với mỗi ô $s$:

$$\Delta(s) = |\text{attackers}_W(s)| - |\text{attackers}_B(s)|$$

$$CC = 8 \sum_{s \in C_0} \Delta(s) + 2 \sum_{s \in C_1} \Delta(s)$$

### 1.5 Cấu trúc tốt (Pawn Structure) $PS$

Với mỗi màu $c$, đếm:
- $P$ = số tốt
- `doubled` = $\displaystyle\sum_{f \in \text{files có tốt}} \max(\text{count}(f) - 1,\; 0)$
- `isolated` = số tốt mà **không có tốt cùng phe** ở 2 file kề (file ± 1)
- `passed` = số tốt thông qua (không có tốt đối phương trên cùng file hoặc 2 file kề ở phía trước)

$$PS_c = 12 \cdot \text{passed}_c - 8 \cdot \text{doubled}_c - 6 \cdot \text{isolated}_c$$

$$PS = PS_W - PS_B$$

### 1.6 Phát triển (Development) $Dev$

Với mỗi màu $c$, ký hiệu:
- $u_c$ = số quân **mã/tượng** vẫn còn ở ô khởi đầu (b1, g1, c1, f1 cho trắng — và mirror cho đen).
- $\text{castled}_c$ = 1 nếu vua đã nhập thành (mất quyền nhập thành VÀ vua đứng ở g1/c1/g8/c8), ngược lại 0.

$$Dev_c = -7 u_c + 18 \cdot \text{castled}_c$$

$$Dev = Dev_W - Dev_B$$

### 1.7 Đe doạ (Threats) $Th$

Với mỗi quân $p$ ở ô $s$ bị tấn công nhưng **không có quân cùng phe bảo vệ** ($\text{def}=0,\,\text{att}>0$):

$$Th_p = -\sigma(\text{color}(p)) \cdot 0.08 \cdot V(p)$$

$$Th = \sum_{p \text{ hanging}} Th_p$$

### 1.8 Phạt khi đang bị chiếu

$$Chk = \begin{cases} -35 & \text{nếu trắng đang bị chiếu (board.turn = W)} \\ +35 & \text{nếu đen đang bị chiếu} \\ 0 & \text{không bị chiếu} \end{cases}$$

### 1.9 Trường hợp kết thúc

Trả về trước khi cộng các thành phần trên:

| Tình huống | Giá trị (từ WHITE) |
|---|---|
| Trắng chiếu hết đen | $+99\,999$ |
| Đen chiếu hết trắng | $-99\,999$ |
| Hoà (stalemate / insufficient / claim_draw) | $0$ |

---

## 2. Minimax (Mô hình 1)

Đệ quy:

$$
\text{minimax}(s, d, \text{max}, \text{persp}) =
\begin{cases}
\text{evaluate}(s, \text{persp}) & d = 0 \text{ hoặc terminal} \\[4pt]
\displaystyle\max_{m \in \mathcal{M}(s)} \text{minimax}(s', d-1, \text{False}, \text{persp}) & \text{max} = \text{True} \\[4pt]
\displaystyle\min_{m \in \mathcal{M}(s)} \text{minimax}(s', d-1, \text{True},\, \text{persp}) & \text{max} = \text{False}
\end{cases}
$$

Trong đó $s' = \text{push}(s, m)$ và $\mathcal{M}(s)$ là tập nước hợp lệ.

Độ phức tạp: $O(b^d)$ với $b$ là branching factor (≈ 35 ở giữa ván).

---

## 3. Alpha-Beta Pruning (Mô hình 2)

$$\text{alphabeta}(s, d, \alpha, \beta, \text{max}, \text{persp})$$

**Điều kiện cắt tỉa:**
- Nhánh MAX cắt khi $\alpha \geq \beta$ (đã có $\alpha = $ giá trị tốt nhất tới giờ; nếu vượt $\beta$ → phía MIN sẽ không cho ta vào đây).
- Nhánh MIN cắt khi $\beta \leq \alpha$.

Cập nhật trong nhánh MAX:
$$
\text{value} \leftarrow \max(\text{value},\; \text{child}), \qquad
\alpha \leftarrow \max(\alpha,\; \text{value})
$$

Cập nhật trong nhánh MIN:
$$
\text{value} \leftarrow \min(\text{value},\; \text{child}), \qquad
\beta \leftarrow \min(\beta,\; \text{value})
$$

**Độ phức tạp lý tưởng** (move ordering hoàn hảo): $O(b^{d/2})$ — tương đương "tăng gấp đôi độ sâu so với Minimax thuần".

---

## 4. Quiescence Search

Khi đến leaf ($d \leq 0$), thay vì gọi `evaluate` ngay, ta gọi:

$$\text{quiescence}(s, \alpha, \beta, \text{persp}, \text{ply}, Q_{\max})$$

Stand-pat:
$$\text{sp} = \text{evaluate}(s, \text{persp})$$

Xác định $\text{maxim} = (s.\text{turn} = \text{persp})$.

**Nhánh MAX (`maxim = True`):**
- Nếu $\text{sp} \geq \beta$ → trả $\text{sp}$ (β-cutoff stand-pat).
- $\alpha \leftarrow \max(\alpha,\; \text{sp})$.
- Duyệt **chỉ** các nước "ồn" (capture, promotion, check ở ply 0). Đệ quy như alpha-beta thường.

**Nhánh MIN (`maxim = False`):**
- Nếu $\text{sp} \leq \alpha$ → trả $\text{sp}$.
- $\beta \leftarrow \min(\beta,\; \text{sp})$.

Cap độ sâu: `ply ≥ Q_max ⇒` trả $\text{sp}$ ngay. Default $Q_{\max} = 6$.

---

## 5. Move Ordering (chi tiết điểm số)

Điểm ưu tiên của mỗi nước $m$:

$$
\text{score}(m) = 0
+ \underbrace{\bigl(10\,000 + 10 V_v - V_a\bigr)}_{\text{capture (MVV-LVA)}}
+ \underbrace{(8\,000 + V_{\text{prom}})}_{\text{phong cấp}}
+ \underbrace{2\,000}_{\text{chiếu}}
+ \underbrace{500}_{\text{nhập thành}}
+ \underbrace{1\,500}_{\text{killer (quiet)}}
+ \underbrace{\min(H(m),\,1\,000)}_{\text{history (quiet)}}
$$

Mỗi thành phần chỉ cộng vào nếu áp dụng được (ví dụ: bonus killer/history **chỉ áp dụng cho quiet move**, không cộng khi `m` là capture).

- $V_v$ = giá trị quân bị bắt (victim), $V_a$ = giá trị quân tấn công (attacker).
- $V_{\text{prom}}$ = giá trị quân phong cấp (thường là 900 cho hậu).
- $H(m)$ = history score của $(piece\_type, to\_square)$.

---

## 6. Transposition Table — quy tắc tra cứu

Mỗi entry lưu: `(depth, score, flag ∈ {EXACT, LOWER, UPPER}, best_move)`.

**Probe** với (key, $d_q$, $\alpha$, $\beta$):

Nếu entry tồn tại và $\text{entry.depth} \geq d_q$:
- `flag = EXACT` → trả `entry.score` (dùng được trong mọi cửa sổ).
- `flag = LOWER` (giá trị thực $\geq$ score): trả nếu $\text{score} \geq \beta$.
- `flag = UPPER` (giá trị thực $\leq$ score): trả nếu $\text{score} \leq \alpha$.

Nếu `entry.depth < d_q`: **không** cutoff, nhưng vẫn lấy `best_move` cho ordering.

**Store** sau khi search xong với kết quả `value`, biết $\alpha_{\text{orig}}$ và $\beta$ ban đầu:

$$
\text{flag} = \begin{cases}
\text{UPPER} & \text{value} \leq \alpha_{\text{orig}} \\
\text{LOWER} & \text{value} \geq \beta \\
\text{EXACT} & \alpha_{\text{orig}} < \text{value} < \beta
\end{cases}
$$

---

## 7. Iterative Deepening

Lặp $d = 1, 2, \dots, d_{\max}$. Sau mỗi iteration:
- TT giữ nguyên (chia sẻ giữa các iteration).
- PV move của root iteration trước được đẩy lên đầu danh sách ordering.

Điều kiện dừng:
- Đã đạt $d_{\max}$.
- Đến hạn `time_limit_s` (kiểm tra ở đầu mỗi iteration, không cắt nửa iteration).
- Tìm thấy nước mate forcing: $|\text{value}| > 90\,000$.

---

## 8. Q-Learning — công thức Bellman

$$\boxed{\;Q(s,a) \leftarrow Q(s,a) + \alpha\Bigl[\,r + \gamma \cdot \max_{a'} Q(s', a') - Q(s,a)\,\Bigr]\;}$$

Hằng số mặc định trong config:

| Tham số | Giá trị |
|---|---|
| $\alpha$ (learning rate) | 0.1 |
| $\gamma$ (discount factor) | 0.95 |
| $\varepsilon_0$ (exploration ban đầu) | 0.2 |
| $\varepsilon_{\min}$ | 0.02 |
| decay rate | 0.999 |

### 8.1 Epsilon-greedy

$$
a = \begin{cases}
\text{random}(\mathcal{A}(s)) & \text{với xác suất } \varepsilon \\
\arg\max_{a \in \mathcal{A}(s)} Q(s,a) & \text{ngược lại}
\end{cases}
$$

(Khi có nhiều $a$ cùng đạt $\max Q$, lấy ngẫu nhiên trong tập đó.)

### 8.2 Epsilon decay (sau mỗi ván self-play)

$$\varepsilon \leftarrow \max(\varepsilon_{\min},\; \varepsilon \cdot \text{decay})$$

Với decay = 0.999, $\varepsilon_0 = 0.2$, $\varepsilon_{\min} = 0.02$:
$$\varepsilon_g = \max\bigl(0.02,\; 0.2 \cdot 0.999^g\bigr)$$
Đạt sàn 0.02 khi $0.999^g = 0.1 \Rightarrow g = \log(0.1)/\log(0.999) \approx 2302$ ván.

### 8.3 Quantized Q-value (biến thể kiểm tra research gap)

Sau Bellman update, nếu bật lượng tử hoá, Q-value được clip rồi làm tròn về
bội số gần nhất của bước $\Delta_Q$:

$$Q_{\text{raw}} = Q(s,a) + \alpha\Bigl[r + \gamma \max_{a'}Q(s',a') - Q(s,a)\Bigr]$$

Nếu `q_value_clip = C`:

$$Q_{\text{clip}} = \min(C,\; \max(-C,\; Q_{\text{raw}}))$$

Nếu `q_value_step = \Delta_Q`:

$$Q_{\text{quant}} = \Delta_Q \cdot \operatorname{round}\left(\dfrac{Q_{\text{clip}}}{\Delta_Q}\right)$$

Nếu `q_value_step = null`, giữ nguyên giá trị float:

$$Q_{\text{new}} = Q_{\text{clip}}$$

Mặc định trong config là `q_value_step: null`, `q_value_clip: null`, nên hành vi
cũ không đổi. Ví dụ với $\Delta_Q = 0.05$, $Q_{\text{raw}} = 0.333$:

$$Q_{\text{quant}} = 0.05 \cdot \operatorname{round}(6.66) = 0.35$$

---

## 9. Reward shaping

Sau khi quân màu $c$ đi nước $m$ từ board $B_0$ → $B_1$:

$$r = r_{\text{terminal}} + r_{\text{shaping}} + r_{\text{move}}$$

| Thành phần | Công thức |
|---|---|
| $r_{\text{terminal}}$ | $+1$ nếu $c$ chiếu hết, $-1$ nếu $c$ bị chiếu hết, ngược lại $0$ |
| $r_{\text{shaping}}$ | $0.01 \cdot \bigl(\text{evaluate}(B_1, c) - \text{evaluate}(B_0, c)\bigr)$ |
| $r_{\text{move}}$ | $+0.05$ (capture) + $0.10$ (promotion) + $0.03$ (gives check) |

Các bonus của $r_{\text{move}}$ **cộng dồn** nếu có nhiều điều kiện cùng đúng.

---

## 10. Mô hình lai (Hybrid) — Mô hình 3

Tại root, với mỗi nước $m \in \mathcal{M}(s)$:

$$\boxed{\;\text{FinalScore}(m) = \text{MinimaxScore}(m) + \lambda \cdot Q(s, m)\;}$$

- $\text{MinimaxScore}(m)$ = giá trị trả về của alpha-beta sau khi push $m$ (độ sâu $d-1$).
- $Q(s, m)$ = Q-value lưu trong table với key $(s, m.\text{uci})$.
- $\lambda$ = 0.5 (default).

### 10.1 Confidence-Aware Hybrid Q

Biến thể novelty của đồ án điều chỉnh ảnh hưởng Q-value theo số lần học:

$$\text{conf}(s,m) = \frac{N(s,m)}{N(s,m) + k}$$

$$\boxed{\;\text{FinalScore}(m) =
\text{AlphaBetaScore}(m) + \lambda \cdot \text{conf}(s,m) \cdot Q(s,m)\;}$$

- $N(s,m)$ = số lần Q-table cập nhật cặp state-action này.
- $k$ = hệ số làm mượt, mặc định `confidence_k = 10`.
- Nếu tắt `use_confidence`, code dùng $\text{conf}(s,m)=1$ để tái lập Hybrid cũ.

Ví dụ $N=5$, $k=10$, $Q=0.6$, $\lambda=0.5$:

$$\text{conf} = \frac{5}{5+10} = 0.333$$
$$\text{QBonus} = 0.5 \cdot 0.333 \cdot 0.6 \approx 0.10$$

---

## 11. ELO rating

### 11.1 Kỳ vọng

$$E_A = \dfrac{1}{1 + 10^{(R_B - R_A)/400}}, \qquad E_B = 1 - E_A$$

### 11.2 Cập nhật

$$R_A' = R_A + K \cdot (S_A - E_A), \qquad R_B' = R_B + K \cdot (S_B - E_B)$$

Với $S_A \in \{1,\; 0.5,\; 0\}$ tương ứng A thắng/hoà/thua, $S_B = 1 - S_A$.

Hằng số mặc định: $R_0 = 1500$, $K = 32$.

**Ví dụ tính tay**: A=1600, B=1500, A thắng:
$$E_A = \dfrac{1}{1 + 10^{-100/400}} = \dfrac{1}{1 + 10^{-0.25}} = \dfrac{1}{1 + 0.5623} \approx 0.640$$
$$R_A' = 1600 + 32 \cdot (1 - 0.640) = 1600 + 11.5 = 1611.5$$
$$R_B' = 1500 + 32 \cdot (0 - 0.360) = 1500 - 11.5 = 1488.5$$

---

## 12. History heuristic — luỹ kế

Khi quiet move $m$ (không phải capture) gây $\beta$-cutoff ở độ sâu $d$:

$$H\bigl(\text{piece\_type}(m),\; \text{to\_square}(m)\bigr) \mathrel{+}= d^2$$

Killer table (per ply): giữ tối đa 2 quiet move gây cutoff gần nhất; trùng → không thêm.

---

## 13. Compact state binning (nâng cấp)

`feature_vector(board)` trả vector 12 chiều (thực). Mỗi chiều được "bucket" qua tập biên (edges):

$$\text{bucket}(v, \mathbf{e}) = \min\{\, i : v < e_i \,\} \text{ hoặc } |\mathbf{e}| \text{ nếu không tồn tại}$$

Sau đó mã hoá thành ký tự: `chr(ord('A') + bucket)`. Nối lại → key độ dài 12.

| Feature | Edges |
|---|---|
| 5 chênh lệch quân (P/N/B/R/Q) | $(-2.5, -0.5, 0.5, 2.5)$ |
| center_control | $(-4, -1, 1, 4)$ |
| turn | $(0,)$ |
| castling | $(-0.5, 0.5)$ |
| check | $(0.5,)$ |
| mobility | $(-15, -3, 3, 15)$ |
| king_safety | $(-2, 0, 2)$ |
| pawn_structure | $(-3, 0, 3)$ |

---

## 14. Ví dụ tính tay end-to-end

### 14.1 Q-update đơn giản

Trạng thái: $Q(s, a) = 0$. Sau khi đi $a$ thu được $r = 0.05$ (capture), chuyển sang $s'$ với $\max_{a'} Q(s', a') = 0.3$. $\alpha = 0.1,\; \gamma = 0.95$.

$$\text{target} = 0.05 + 0.95 \cdot 0.3 = 0.335$$
$$Q(s,a) \leftarrow 0 + 0.1 \cdot (0.335 - 0) = 0.0335$$

### 14.2 Reward shaping cụ thể

Trắng đi $m$ ăn tốt đen.
- $\text{eval}(B_0, W) = +50$, $\text{eval}(B_1, W) = +160$ (gain ~110 do bắt tốt + thay đổi vị trí).
- $r_{\text{terminal}} = 0$ (chưa hết ván).
- $r_{\text{shaping}} = 0.01 \cdot (160 - 50) = 1.10$.
- $r_{\text{move}} = 0.05$ (capture) $+ 0$ (no promote) $+ 0$ (no check, giả sử) $= 0.05$.
- **Total** $r = 0 + 1.10 + 0.05 = 1.15$.

### 14.3 Hybrid score tại root

Giả sử ở vị trí $s$ có 3 nước root: $\{a, b, c\}$. $\lambda = 0.5$.

| Nước | MinimaxScore | $Q(s, \cdot)$ | FinalScore |
|---|---:|---:|---:|
| $a$ | $+30$ | $+1.2$ | $30 + 0.5 \cdot 1.2 = 30.6$ |
| $b$ | $+28$ | $+4.0$ | $28 + 0.5 \cdot 4.0 = 30.0$ |
| $c$ | $+35$ | $-2.0$ | $35 + 0.5 \cdot (-2.0) = 34.0$ |

→ Chọn $c$.

### 14.4 Alpha-beta cutoff thủ công

Cây gốc MAX, depth 2, branching factor 2, giá trị leaf đã biết:
```
                root (MAX)
            /             \
       n1 (MIN)        n2 (MIN)
       /    \           /    \
      3      5         6      9
```

- Vào $n_1$ (MIN), $\alpha = -\infty,\; \beta = +\infty$.
  - leaf 3 → $\text{value} = 3,\; \beta = 3$. Vẫn $\alpha < \beta$.
  - leaf 5 → $\text{value} = \min(3, 5) = 3$. Trả $3$.
- root: child = $3$, $\alpha \leftarrow \max(-\infty, 3) = 3$.
- Vào $n_2$ (MIN), $\alpha = 3,\; \beta = +\infty$.
  - leaf 6 → $\text{value} = 6,\; \beta = 6$. Vẫn $\beta > \alpha$.
  - **Quan trọng**: leaf tiếp theo là 9 (chưa duyệt) — nhưng vì MIN không bao giờ cho phép > 6, root chỉ có thể có giá trị tối đa từ $n_2$ là $\min(6, 9) = 6$. Mà root MAX hiện có $\alpha = 3 < 6$, ta phải duyệt tiếp:
  - leaf 9 → $\text{value} = \min(6, 9) = 6$.
- root: child = $6$, $\alpha \leftarrow 6$.

Trường hợp **có** cutoff: nếu thay đổi sang `3, 5, 2, 9`:
- $n_2$ leaf 2 → $\text{value} = 2,\; \beta = 2$. Kiểm tra $\beta \leq \alpha$ (2 ≤ 3)? **Đúng → cắt nhánh.** Leaf 9 không cần duyệt.

---

## 15. Ghi chú thực nghiệm

- Khi muốn so sánh nodes/move của bản nâng cấp với bản gốc, cần **tắt iterative deepening + time limit** (set `time_limit_s: null`, `use_iterative_deepening: false`) để số liệu ổn định giữa các máy.
- Quiescence khiến tổng số node tăng nhưng `evaluate` chỉ được gọi tại các vị trí "yên" → chất lượng nước đi tốt hơn ở cùng `max_depth`.
- Với mỗi cải tiến, có thể tạo cặp config legacy/upgraded và chạy `scripts/evaluate.py` 2 lần để có cột so sánh trong báo cáo (mục 4.4.5).
