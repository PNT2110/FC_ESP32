> Cập nhật tiếp theo cùng ngày: vấn đề antenna nêu trong báo cáo này đã được sửa. Xem [báo cáo mới](../antenna_fix/BAO_CAO.md). Bộ ZIP DFM_RECHECK đã được xuất lại từ bản sửa antenna.

# Sửa PCB theo ảnh JLCDFM — 15/09/2026

## Kết quả đã kiểm tra

- KiCad 10.0.6: ERC 0, DRC 0, cảnh báo 0, kết nối hở 0, sai khác schematic/PCB 0 (`FC_ESP32/validation_summary.json`).
- Mặt sau chỉ còn **PNT**, đọc đúng chiều từ mặt dưới. Đã xem ảnh render hai mặt.
- Bộ `FC_ESP32/FC_ESP32_DFM_RECHECK.zip` có 8 lớp Gerber cần thiết và 2 file khoan riêng PTH/NPTH. Bộ `machin.zip` cũ thiếu file khoan; không dùng nó để đánh giá bản sửa.
- File khoan mới có 175 lỗ/slot mạ (163 via, 4 slot USB, 8 chân header) và 6 lỗ không mạ (4 motor Ø8,6 mm, 2 chốt USB Ø0,65 mm).
- Tất cả segment và phần đồng của via giữ nguyên. Không đổi vị trí linh kiện, số chân, net, đường kính lỗ motor, khoảng cách motor 66,8 mm hay độ dày 0,8 mm.

## Các thay đổi

1. Xóa các chữ `USB`, `1S ONLY`, `BAT+ BAT-` khỏi lớp in mặt sau; chuyển sang lớp tài liệu Dwgs.User. PNT là chữ duy nhất ở B.Silkscreen.
2. Đổi solder-mask expansion của pad từ +0,04 mm sang 0: cửa sổ mask bằng pad đồng. Bật tenting hai mặt của via và tùy chọn trừ cửa sổ mask khỏi silkscreen khi xuất Gerber.
3. Nét silkscreen tối thiểu 0,15 mm. Chuyển nét không đủ chỗ quanh linh kiện 0402 và một số dấu tròn sát pad sang F.Fab. Cắt đoạn silkscreen xâm lấn khoảng cách 0,15 mm quanh pad. Dấu định hướng trên lớp lắp ráp vẫn được giữ; cần dùng bản vẽ lắp ráp khi hàn.
4. Đặt clearance cục bộ 0,25 mm quanh lỗ motor, refill vùng GND và lưu lại PCB. Các vùng đồng trước đó chỉ cách lỗ khoảng 0,1505 mm.
5. Hai pad GND vật lý ngoài cùng USB-C (A1/B12 và A12/B1) giữ nguyên tâm và kích thước bao 0,6 × 1,15 mm, tăng bán kính góc bo từ 0,15 lên 0,24 mm. Clearance đến lỗ định vị tăng từ 0,1944 lên 0,2161 mm. Diện tích pad giảm khoảng 4,5%; đây là điều chỉnh footprint cục bộ, không phải land pattern nguyên bản của hãng.
6. Quy tắc hole-clearance chung vẫn là 0,25 mm qua `.kicad_dru`; riêng cặp đối tượng nằm trong J1 dùng 0,20 mm. Giới hạn cứng trong project là 0,20 mm để ngoại lệ có hiệu lực. Không tắt kiểm tra DRC và không giảm bề rộng đường pin/motor.
7. Các thay đổi được lưu trong `tools/build_fc.py` và thư viện FC_Local. Dùng `--finish-artwork` để áp dụng lên PCB đã đi dây mà không tái tạo và làm mất đường mạch.

## Đối chiếu với ảnh JLCDFM

| Nhóm trong ảnh | Đã xử lý/giới hạn xác nhận |
|---|---|
| Silkscreen to pad: 50 đỏ | Đã sửa hình học và cấu hình xuất; KiCad không còn lỗi silk. Chưa có số đếm JLC mới. |
| Silkscreen line width: 49 cam | Nét trên lớp in đã nâng lên ít nhất 0,15 mm. |
| Soldermask bridge: 20 đỏ, 12 cam | Đã thu expansion về 0. Audit pad danh định không tìm thấy khe mask dưới 0,10 mm; phép audit này không thay thế thuật toán JLC. |
| Mask opening exposing trace / multiple segments / negative expansion | Đã bỏ expansion pad và tent via; cần kiểm tra lại bộ Gerber mới ở JLC để đối chiếu từng marker. |
| Trace spacing / pad spacing | KiCad kiểm tra theo clearance 0,15 mm và không báo vi phạm; cảnh báo JLC có thể dùng mức mục tiêu khác. Không giảm rule để che lỗi. |
| Drill: Unanalyzed | Đã bổ sung cả PTH/NPTH, kể cả slot USB. |

Trang JLCDFM trong ảnh đã được mở thử nhưng chỉ hiện trang trắng trong trình duyệt của agent. Vì vậy **chưa chạy được DFM phía JLC trên bộ mới**, không khẳng định đã hết toàn bộ lỗi trong ảnh. Hai audit mask trước/sau cùng không có khe dưới 0,10 mm; không thể dùng số này để tuyên bố đã giải quyết 20 marker đỏ của JLC khi chưa đọc được chi tiết của chúng.

## Các điểm chưa đủ để đặt sản xuất hoặc cam kết bay

Bộ ZIP là bản **để kiểm tra DFM lại**, chưa phải phê duyệt sản xuất. Review điện trước đó còn ghi nhận đường VBAT/PWM1 trên B.Cu đi vào vùng antenna ESP32 (23 đoạn/via giao vùng; DRC hiện tại không bắt toàn bộ điều kiện antenna). Đợt sửa này giữ nguyên segment/via nên điểm đó chưa được giải quyết. L2 chưa chốt mã đặt hàng, dòng motor thực tế và thử nguồn/tải chưa có bằng chứng. Xem `BAO_CAO_KIEM_TRA_MACH.md` và `validation/datasheet_audit/antenna_audit.json`.

Không thể kết luận mạch chắc chắn hoạt động hay bay ổn định chỉ từ DRC/3D. Cần chạy lại JLCDFM, giải quyết vùng antenna và các mục điện tồn đọng, rồi kiểm tra board thật trước khi lắp cánh.

## Nguồn

- [JLCPCB: năng lực gia công PCB](https://jlcpcb.com/capabilities/pcb-capabilities): khoảng cách đồng, lỗ và kích thước nét.
- [JLCPCB: thiết kế NPTH](https://jlcpcb.com/blog/npth-design-guide): clearance đồng 0,2–0,3 mm quanh NPTH.
- [JLCPCB: solder mask và LDI](https://jlcpcb.com/blog/basic-design-of-solder-mask): cửa sổ 1:1 với pad.
- [GCT USB4105 — bản vẽ hãng](https://gct.co/files/drawings/usb4105.pdf): vị trí chân, pad và lỗ định vị. Thay đổi góc bo được mô tả ở trên.

## Tái chạy và bằng chứng

```sh
PYTHONPATH=/home/pnt/miniconda3/lib/python3.14/site-packages /usr/bin/python3 tools/build_fc.py --finish-artwork
python3 tools/export_dfm.py
PYTHONPATH=/home/pnt/miniconda3/lib/python3.14/site-packages /usr/bin/python3 tools/audit_dfm.py FC_ESP32/FC_ESP32.kicad_pcb
```

`before.kicad_pcb`/`before.kicad_pro`: bản sao trước khi sửa. `before_drc.json`: 15 vi phạm (bao gồm zone chưa refill đúng). `after_drc.json`: sạch. `copper_comparison.json`: segment/via đồng không đổi. `geometry_after.json`: mask và chữ sau. `package_manifest.json`: SHA-256 của PCB và từng file xuất. `bottom.png`/`top.png`: ảnh kiểm tra hai mặt.
