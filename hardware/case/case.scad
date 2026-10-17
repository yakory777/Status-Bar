// Корпус для LilyGO T-Display-S3 AMOLED (1,91″) — тот же, что генерирует case.py.
// Откройте в OpenSCAD, выберите part и экспортируйте STL (F6 → F7).
// Размеры в мм; сверьте с вашей платой перед печатью.

part = "all";          // "tray" | "bezel" | "stand" | "all"

board_l = 60.0;  board_w = 25.5;  board_t = 10.0;
clear = 0.35;    wall = 2.0;      floor_t = 1.6;
battery_h = 6.0; ledge = 1.6;
usb_w = 9.6;  usb_h = 4.0;  usb_z = 2.6;
btn_from = 4.0;  btn_len = 16.0;  btn_h = 3.2;  btn_z = 3.0;
win_l = 45.0;  win_w = 21.0;  win_dx = 1.5;  win_dy = 0.0;
bezel_t = 1.6;  lip_h = 2.2;  lip_t = 1.2;  lip_gap = 0.2;
stand_angle = 22;  stand_depth = 34;  stand_lip = 4;

il = board_l + 2*clear;   iw = board_w + 2*clear;
ol = il + 2*wall;         ow = iw + 2*wall;
board_z0 = floor_t + battery_h;
oh = board_z0 + board_t;

module box(a, b) translate(a) cube([b[0]-a[0], b[1]-a[1], b[2]-a[2]]);

module tray() difference() {
    union() {
        difference() {
            cube([ol, ow, oh]);
            box([wall, wall, floor_t], [wall+il, wall+iw, oh+1]);
        }
        if (battery_h > 0) {
            box([wall, wall, floor_t], [wall+il, wall+ledge, board_z0]);
            box([wall, wall+iw-ledge, floor_t], [wall+il, wall+iw, board_z0]);
        }
    }
    uz = board_z0 + usb_z;
    box([-1, ow/2-usb_w/2, uz-usb_h/2], [wall+0.5, ow/2+usb_w/2, uz+usb_h/2]);
    bz = board_z0 + btn_z;
    box([wall+btn_from, -1, bz-btn_h/2], [wall+btn_from+btn_len, wall+0.5, bz+btn_h/2]);
}

module bezel() {        // печатать лицом вниз
    cx = ol/2 + win_dx;  cy = ow/2 + win_dy;
    x0 = wall+lip_gap; y0 = wall+lip_gap; x1 = wall+il-lip_gap; y1 = wall+iw-lip_gap;
    lh = bezel_t + lip_h;
    difference() {
        union() {
            cube([ol, ow, bezel_t]);
            box([x0, y0, bezel_t], [x1, y0+lip_t, lh]);
            box([x0, y1-lip_t, bezel_t], [x1, y1, lh]);
            box([x0, y0, bezel_t], [x0+lip_t, y1, lh]);
            box([x1-lip_t, y0, bezel_t], [x1, y1, lh]);
        }
        box([cx-win_l/2, cy-win_w/2, -1], [cx+win_l/2, cy+win_w/2, bezel_t+1]);
        box([-1, ow/2-usb_w/2-1, bezel_t], [wall+lip_t+lip_gap+1, ow/2+usb_w/2+1, lh+1]);
    }
}

module stand() {
    h = stand_depth * tan(stand_angle);
    rotate([90, 0, 90]) linear_extrude(ol)
        polygon([[0, 0], [stand_depth, 0], [stand_depth, h+2], [0, 2+stand_lip]]);
}

if (part == "tray")  tray();
if (part == "bezel") bezel();
if (part == "stand") stand();
if (part == "all") {
    tray();
    translate([0, ow + 8, 0]) bezel();
    translate([0, 2*ow + 16, 0]) stand();
}
