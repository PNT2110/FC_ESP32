# Bàn giao dự án FC_ESP32 cho AI tiếp theo

Tiếp tục dự án KiCad 10 tại `/home/pnt/FC_ESP32`. Đọc `AGENTS.md` và kiểm tra trạng thái file thực tế trước khi sửa. Không xem dự án là hoàn tất khi còn lỗi kết nối.

Thông tin dưới đây ghi lại trạng thái khi dừng ngày 2026-09-14, không thay thế việc kiểm tra lại PCB hiện tại. Người dùng đã yêu cầu dừng công việc và viết tài liệu bàn giao; chỉ tiếp tục chỉnh sửa khi được yêu cầu.

## Yêu cầu đã chốt

- Flight controller ESP32-WROOM-32 cho quad brushed 1S.
- Motor coreless 8520, cánh Gemfan 40mm 1635 ba lá.
- Pin Tattu Rline 550mAh 1S 95C, danh định 3.8V.
- Điều khiển bằng tay ESP-NOW riêng.
- Giữ khoảng cách motor kề nhau 66.8mm, PCB dày 0.8mm và antenna keepout.
- Linh kiện lắp một mặt trên.
- J2 phải quay đầu cắm ra ngoài phía phải.
- Dịch các pad hàn dây motor vào trong một chút, hoàn thành đi dây, kiểm tra điện và hướng linh kiện trên bản 3D.

## Đã làm

- J4–J7 đã dịch 1.5mm theo hướng tâm; không dịch tâm motor.
- J2 ở `(113.95,106.8)`, góc 90°: pin 1 GND, 2 +5V_FLOW, 3 FLOW_TX, 4 FLOW_RX.
- J8 chuyển đến `(115,96.85)` để nhường đường đi dây.
- Đã sửa một số model 3D và artwork; vẫn phải kiểm tra lại bản render cuối.
- C3 hiện ở khoảng `(88.55,93.25)`, góc 180°.
- EN đã nối đủ sau khi đi lại một phần +5V_FLOW.
- Snapshot gần hoàn thiện: `validation/only_c3_ground_remaining.kicad_pcb`.

## Trạng thái khi dừng

PCB chính đã được khôi phục từ snapshot trên: `FC_ESP32/FC_ESP32.kicad_pcb`.

Kết quả kiểm tra tương ứng gần nhất:

- ERC: 0 lỗi.
- Schematic parity: 0 lỗi.
- Không có lỗi short/clearance.
- Còn 1 vùng GND cô lập quanh chân mass C3.
- Có 3 cảnh báo `via_dangling` trên +5V_FLOW, BOOST_FB và PWM4.

Hãy chạy lại kiểm tra để xác nhận trạng thái thực tế.

## Vấn đề cần giải quyết

Mass C3 bị bao bởi BOOST_FB ở F.Cu; VBAT rộng 1.2mm ở B.Cu chặn vị trí via.

Các thử nghiệm đã thất bại và đã hoàn tác:

- Bóc BOOST_FB, nối mass C3 đường ngắn rồi đi lại BOOST_FB: không tìm được đường.
- Xoay C3 90°/270° trong vùng ±4mm: không có vị trí đạt kiểm tra courtyard với bố trí hiện tại.

Đừng lặp vô hạn những thử nghiệm này. Hãy xem xét điều chỉnh cục bộ đường đồng hoặc bố trí linh kiện lân cận.

Cần lưu ý: đoạn +5V_FLOW mới nối dùng 0.18mm vì thử 0.4mm không đi được. Phải đánh giá lại đường cấp nguồn thực tế, không chỉ nhìn netclass.

## Công cụ và nguồn dữ liệu

- `tools/build_fc.py` là nguồn sinh phần cứng. Thay đổi bố trí/footprint phải cập nhật generator và kiểm tra tái sinh; không chạy generator trực tiếp làm mất bản đã route.
- `tools/route_remaining.py`: router phụ, có `--source-ref C3`, `--ignore-zones`, `--sense-branch`. DRC mới là kết luận.
- `tools/import_route.py` đã bổ sung kiểm tra góc và mặt linh kiện trước khi import.
- `FC_ESP32/FC_ESP32.ses` hiện cũ, C3 vẫn góc 0°: **không import vào PCB hiện tại**.
- `tools/validate_fc.py` chạy ERC/DRC/parity.
- `tools/audit_board.py` kiểm tra pad motor, J2, C3, pin/net và chiều rộng công suất.

Chạy công cụ pcbnew bằng môi trường đã dùng trong phiên trước; kiểm tra lại đường dẫn nếu môi trường thay đổi:

```bash
PYTHONPATH=/home/pnt/miniconda3/lib/python3.14/site-packages /usr/bin/python3 tools/<script>.py
```

## Giới hạn

- Giữ netclass Battery 1.2mm, MotorPower 0.8mm, LogicPower 0.4mm, Default 0.18mm.
- Không thu hẹp đường pin/motor để ép route.
- Nhánh đo VBAT 0.4mm có đánh giá riêng trong `FC_ESP32/adc_branch_review.json`; không mở rộng ngoại lệ này sang đường công suất.
- Không bỏ linh kiện bảo vệ/lọc.
- Một số model cuộn cảm chỉ là hình bao tham khảo; chưa được coi là xác nhận đúng linh kiện.
- Firmware chưa được coi là đã kiểm chứng bay. Giữ cấu hình vô hiệu hóa motor mặc định và kiểm tra riêng nếu tiếp tục phần firmware.

## Điều kiện hoàn tất

1. Nối mass C3 và xử lý via thừa.
2. ERC/DRC không còn lỗi hoặc unconnected; kiểm tra parity và audit.
3. Kiểm tra bản 3D cuối: J2 hướng ra ngoài, hướng/chân model đúng footprint.
4. Đối chiếu BOM, `design.json`, PCB và generator.
5. Lưu bản cuối cùng và báo rõ các giới hạn chưa kiểm chứng.

Gerber cũ có thể stale. Không đặt hàng hoặc tuyên bố đủ điều kiện bay chỉ vì DRC sạch.
