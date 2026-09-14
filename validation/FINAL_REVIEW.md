# Kiểm tra PCB cuối — 2026-09-14

## Kết quả

PCB chính: `../FC_ESP32/FC_ESP32.kicad_pcb`. Bản dự phòng: `final_routed.kicad_pcb`.

- J4–J7 dịch 1.5 mm theo hướng tâm; tâm motor và khoảng cách 66.8 mm giữ nguyên.
- J2 góc 90°, đầu cắm hướng ra cạnh phải; pin 1 GND, 2 +5V_FLOW, 3 FLOW_TX, 4 FLOW_RX.
- Đã nối mass C3 bằng hai via và điều chỉnh cục bộ VBAT B.Cu, giữ chiều rộng 1.2 mm; đã dọn ba via thừa.
- ERC, DRC, unconnected và schematic parity đều bằng 0 trên KiCad 10.0.6. Báo cáo gốc: `../FC_ESP32/validation_summary.json`.
- Audit pad motor, bề dày 0.8 mm, pin/net và chiều rộng công suất đạt: `../FC_ESP32/invariant_audit.json`.
- Đối chiếu BOM, design.json và PCB: 72 linh kiện khớp (`bom_design_audit.json`).
- Generator chạy thành công trong bản sao độc lập; vị trí, hướng, footprint, giá trị và nets khớp (`rebuild_comparison.json`, `rebuild.log`). Đã sửa nhận diện đuôi `.STEP`/`.step` trên Linux.
- Đã xem render `final_3d.png`: J2 quay ra ngoài; các model ESP32, IC, diode, MOSFET và header chính nằm đúng trên footprint. Cuộn cảm vẫn dùng model hình bao, chưa xác nhận mã đặt hàng chính xác.
- `bash firmware/tests/run.sh` đạt cả ba nhóm kiểm tra host: MPU6500, ESP-NOW/arming/failsafe, controller/fault/output limits. Chưa build lại ESP-IDF hoặc thử bay trong lượt kiểm tra này.

## Đường cấp 5 V

Netclass LogicPower vẫn 0.4 mm. +5V_FLOW có tổng 8.448 mm đường 0.18 mm tại vùng hẹp, phần còn lại 0.4 mm. Theo [nhà sản xuất MTF-01P](https://micoair.com/optical_range_sensor_mtf-01p/), cảm biến dùng 5 V và 500 mW, tương đương dòng trung bình 100 mA.

Với giả thiết đồng hoàn thiện 35 µm, cộng điện trở tất cả các đoạn của net (kể cả nhánh) cho khoảng 0.114 Ω: sụt 11.4 mV, tổn hao 1.14 mW ở 100 mA. Chi tiết trong `flow_power_review.json`. Đây là phép tính điện trở ở 20°C; không thay thế mô phỏng nhiệt, không tính via/connector/đường hồi, và không xác nhận dòng đỉnh hay khả năng nguồn boost. Cần xác nhận độ dày đồng và đo tải khi cấp nguồn thực tế.

## Giới hạn và sử dụng file

Phần dịch pad, đi dây và kiểm tra PCB đã hoàn tất. Đây chưa phải xác nhận đủ điều kiện sản xuất hoặc bay: dòng motor thực tế, nhiệt đường công suất, mã cuộn cảm, pin/cáp cảm biến và firmware điều khiển vẫn cần kiểm chứng phần cứng.

Không dùng Gerber cũ trong `../gerbers/` để đặt hàng. Chưa xuất bộ sản xuất mới trong lượt này.

Generator tạo lại bố trí và sẽ xóa routing của PCB đích. Luôn sao lưu trước khi chạy. SES hiện tại cũ hơn các sửa cuối, không import lên bản PCB đã kiểm tra. Script `../tools/repair_c3_ground.py` tái hiện sửa cuối từ snapshot trước sửa; mọi tái sinh hoặc import tiếp theo phải chạy lại ERC/DRC.
