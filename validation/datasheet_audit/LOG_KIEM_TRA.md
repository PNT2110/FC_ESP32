# Log kiểm tra thiết kế theo datasheet

Thực hiện ngày 14/09/2026 trên `/home/pnt/FC_ESP32`. Timestamp UTC và hash nằm trong `review_manifest.json`/`audit.json`. Báo cáo giải thích: `../../BAO_CAO_KIEM_TRA_MACH.md`.

## Các bước đã thực hiện

| Bước | Thao tác / dữ liệu | Kết quả |
|---|---|---|
| 01 | Đọc AGENTS.md, BOM 72 linh kiện, generator, main.c và toàn bộ module MPU/command/radio/controller/PID/Kconfig | Hoàn tất đọc và rà soát; không sửa schematic/PCB/firmware |
| 02 | `pdftotext -layout` cho PDF trong data_sheet | Text local được lưu tại thư mục log này |
| 03 | Xem hình pinout AO3400, MMBT3904 và USB4105 bằng render PDF | Các PNG `ao3400.png`, `mmbt3904.png`, `usb4105.png`; có cảnh báo font cache của môi trường nhưng ảnh tạo thành công và đã xem |
| 04 | Tra nguồn chính thức ST USBLC6, Espressif ESP32 + PCB guide, MicoAir MTF-01P, GCT USB4105 | Dẫn nguồn trong báo cáo; không dùng trang bán hàng để xác nhận chân IC |
| 05 | Xuất netlist mới bằng `kicad-cli sch export netlist ... --format kicadxml` | `fresh.net`, exit 0 |
| 06 | `tools/review_design.py`, mapping độc lập từ datasheet/yêu cầu | 135 pad instances khớp expected; 279 pad instances ghi CSV; `connectivity_pass=true` |
| 07 | So các chân NC/reserved/flash và macro GPIO firmware | Không thấy sai trong tập kiểm tra; U2 exposed pad 25 được ghi là chưa đủ chứng cứ |
| 08 | Đo segment/width và vị trí cụm nguồn từ PCB | `geometry.json`; phát hiện routing feedback/nguồn cần tối ưu, netclass không bảo đảm chiều rộng tất cả đoạn |
| 09 | Đọc rule area anten và kiểm tra đồng độc lập theo vùng U1 thực tế | **FAIL**: 23 đoạn giao vùng, VBAT/PWM1 B.Cu, diện tích hợp giao 2.822775 mm²; `antenna_audit.json` chứa UUID |
| 10 | `python3 tools/validate_fc.py` | exit 0; ERC=0, DRC=0, unconnected=0, parity=0; `erc_drc.log` và các JSON snapshot |
| 11 | `tools/audit_board.py --output .../invariants.json` | exit 0; motor pitch/pad inward/J2/thickness/netclass đạt |
| 12 | `bash firmware/tests/run.sh` | exit 0; MPU6500, ESP-NOW logic, controller tests đạt với ASan/UBSan; `firmware_tests.log` |
| 13 | Kiểm tra vị trí SDK ESP-IDF trước đây và thư mục dự án | Không thấy SDK/toolchain hiện hành ở các vị trí đã dùng; không chạy full ESP-IDF build, không nạp ESP32 |
| 14 | `kicad-cli pcb render` cho top/bottom, 1800×1800, quality high | exit 0 cả hai; `render_top.log`, `render_bottom.log`; đã xem trực tiếp PNG mới |
| 15 | Hoàn thiện báo cáo, bảng chân, sơ đồ khối, feature matrix và việc cần đo trên mạch thật | `BAO_CAO_KIEM_TRA_MACH.md`; chưa có phép đo vật lý |
| 16 | Chạy lại script review sau khi thêm gate anten | exit 1 **có chủ đích do phát hiện thiết kế**, không phải exception; pin mapping PASS, anten FAIL |

## Diễn giải pass/fail

DRC hiện tại không cấm track B.Cu ở anten; vì thế DRC PASS và anten FAIL không mâu thuẫn. Không vô hiệu hóa thêm rule hoặc thêm exclusion để làm báo cáo sạch. Script audit cũ chưa kiểm tra anten đầy đủ; kết quả pass của nó cũng không chứng minh RF đúng.

Script `review_design.py` không tự sửa phần cứng. Mapping chân/net được kiểm tra bằng expected độc lập cho các chân trọng yếu, còn những kết nối linh kiện thụ động được đối chiếu giữa design.json, netlist mới và PCB. Kiểm tra này không chứng minh mọi giá trị linh kiện đáp ứng mọi tải. Các pin/đặc tính chưa xác nhận và các giới hạn đo được ghi rõ trong báo cáo.

Không thực hiện: thay linh kiện, đi lại PCB, sửa firmware, build ESP-IDF toàn bộ, flash, bật motor, mô phỏng SPICE/transient, thermal/EMC test, đo RF, kiểm tra collision bằng assembly đủ motor/cánh/pin/cáp hoặc đặt hàng sản xuất.

## File cần dùng tiếp

- `audit.json`: trạng thái pin/anten và hash nguồn.
- `pin_audit.csv`: bảng toàn bộ pad schematic–PCB, tọa độ và hướng.
- `antenna_audit.json`: lỗi anten có UUID để định vị trong PCB.
- `geometry.json`: chiều dài/chiều rộng thực và tọa độ linh kiện.
- `erc_current.json`, `drc_current.json`, `validation_summary.json`: snapshot kiểm tra KiCad lần này.
- `firmware_tests.log`: các nhóm host test đã chạy.
- `top_3d.png`, `bottom_3d.png`: hai ảnh 3D đã kiểm tra.
- `review_manifest.json`: kết luận chưa phê duyệt phần cứng và hash artifact.

Đầu việc tiếp theo: RF-01, PWR-01, CFG-01 và BOM/assembly trong báo cáo chính. Không bắt đầu bằng việc bật `CONFIG_FC_ENABLE_MOTORS` để thử bay.
