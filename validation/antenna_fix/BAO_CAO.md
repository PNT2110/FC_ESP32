# Sửa vùng antenna ESP32 — 15/09/2026

Đã sửa phần copper xâm lấn envelope antenna của U1: X=91–109 mm, Y=77,75–84,05 mm.

## Thay đổi

- Gỡ 21 segment VBAT và 2 segment PWM1 xâm lấn vùng antenna; giữ các đoạn còn lại.
- Nối lại VBAT bằng đường 1,2 mm ngoài vùng antenna, không giảm bề rộng nguồn. Router thêm 34 segment.
- Nối lại PWM1 bằng đường 0,18 mm ngoài vùng antenna. Router thêm 103 segment; mỗi net trở lại một nhóm đồng liên thông.
- Thêm rule area `ESP32_ANTENNA_ALL_COPPER` trên cả F.Cu và B.Cu: cấm track, via, pad và zone fill. Module U1 được phép nằm trên vùng này vì antenna là một phần module.
- Refill GND để loại bỏ đồng đổ trong antenna. Audit mở rộng phát hiện bản trước còn 1 vùng đồng xâm lấn ngoài 23 segment đã biết.
- Cập nhật generator `build_fc.py` để tạo lại keepout; cập nhật router để tính cả nửa bề rộng track và bán kính via khi né vùng này.
- Thêm `audit_antenna.py` kiểm tra độc lập track/via, pad, đồng đổ đã fill và các cờ cấm trên hai lớp. Export Gerber bị chặn nếu audit không đạt hoặc SHA-256 không khớp PCB hiện tại.

## Kết quả kiểm tra

| Kiểm tra | Kết quả |
|---|---|
| Audit bản trước khi sửa | Không đạt: 23 track/via và 1 zone xâm lấn; chưa có keepout bảo vệ đủ hai lớp |
| Audit bản đã sửa | Đạt: 0 đối tượng đồng xâm lấn, keepout đủ hai lớp |
| ERC | 0 vi phạm |
| DRC | 0 lỗi, 0 cảnh báo |
| Kết nối hở / schematic parity | 0 / 0 |
| Kiểm tra pin theo datasheet và yêu cầu đang lưu | Đạt |
| Kiểm tra kích thước, J2, pad motor và bề rộng đường nguồn | Đạt |
| Kiểm tra ảnh render mặt dưới | PNT đọc đúng chiều; không còn đường ngang đi xuyên phần antenna |

Không thay đổi vị trí linh kiện, số chân, cổng J2, khoảng cách motor 66,8 mm, lỗ motor Ø8,6 mm hoặc board dày 0,8 mm. Bộ Gerber và hai file khoan được xuất lại sau sửa tại `FC_ESP32/FC_ESP32_DFM_RECHECK.zip`.

Các file chứng cứ trong thư mục này: `before.kicad_pcb`, `removed.json`, `route_vbat.log`, `route_pwm1.log`, `regression_before.json`, `antenna_geometry.json`, `invariants.json`, `erc_drc.log`, `package_manifest.json`, `bottom.png`.

## Tái kiểm tra và xuất

Chạy từ thư mục gốc dự án:

```sh
PYTHONPATH=/home/pnt/miniconda3/lib/python3.14/site-packages /usr/bin/python3 tools/audit_antenna.py > validation/antenna_fix/antenna_geometry.json
python3 tools/export_dfm.py
```

`prepare_antenna_fix.py` chỉ dùng khi thực sự cần gỡ và đi lại đoạn vi phạm; không cần chạy lại trên bản đã sạch.

Đây là xác nhận hình học và kết nối trong phạm vi antenna đã định nghĩa, không phải đo kiểm tầm xa ESP-NOW, hiệu suất RF, nhiễu khi motor chạy hoặc bảo đảm bay ổn định. JLCDFM phía dịch vụ chưa được chạy lại do trang tải trắng trong phiên trước. Các mục kiểm chứng phần cứng như dòng motor, nguồn và lựa chọn MPN L2 vẫn nằm trong báo cáo điện; không được coi là đã đo hoặc đã xác nhận chỉ vì DRC sạch.
