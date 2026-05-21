#include <stdint.h>
#include <string.h>
#include "core.h"
#include "system.h"
#include "uart.h"
#include "printf.h"
#include "timer.h"
#include "fpioa.h"
#include "templates.h" // 模板库头文件

// ==========================================
// 1. 宏定义与 DDR 内存池映射 
// ==========================================
// 图像物理参数
#define BIN_IMG_W           1226        // 二值图真实物理跨度
#define RAW_IMG_W           1280        // 原图全宽
#define IMG_H               720
#define RAW_X_OFFSET        27          // 坐标映射到原图的偏移补偿

#define TARGET_W            440
#define TARGET_H            140

#define FIXED_SHIFT         8
#define FIXED_SCALE         (1 << FIXED_SHIFT)
#define MAX_CHAR_SEGMENTS   20   

// 模板宽高
#define TPL_W               16
#define TPL_H               32

//  DDR 安全内存映射 
#define DDR_BIN_FRAME0      0xA0000000  // 二值图
#define DDR_RAW_FRAME0      0xA4000000  // 原始全彩图
#define MEM_Q_X             ((uint16_t*)0xA1000000) // BFS 队列X
#define MEM_Q_Y             ((uint16_t*)0xA1100000) // BFS 队列Y
#define MEM_ROI_BUF         ((uint16_t*)0xA1200000) // 原图抠取缓存区
#define MEM_DST_IMG         ((uint16_t*)0xA1900000) // 透视变换后的校正图
#define MEM_BW_IMG          ((uint32_t*)0xA1A00000) // 最终识别用的黑底白字二值图
#define MEM_TEST_IMAGE      ((uint8_t*)0xA1B00000)  // 字符缩放匹配缓存区

// ROI 定位加速参数
#define ROI_MARGIN_X        200         
#define ROI_MARGIN_Y        150         

extern void set_led5_status(int on);
extern void set_led6_status(int on);

// ==========================================
// 2. 基础安全工具函数
// ==========================================
int get_max(int a, int b) { return a > b ? a : b; }
int get_min(int a, int b) { return a < b ? a : b; }

// 纯软件除法
int safe_div(int num, int den) {
    if (den == 0) return 0;
    int res = 0;
    while (num >= den) {
        int temp = den;
        int multiple = 1;
        while (num >= (temp << 1) && (temp << 1) > temp) {
            temp <<= 1;
            multiple <<= 1;
        }
        num -= temp;
        res += multiple;
    }
    return res;
}

// 宽度中位数滤波器
int get_median_width(int* w_arr, int count) {
    if (count <= 0) return 0;
    int widths[MAX_CHAR_SEGMENTS];
    for (int i = 0; i < count; i++) widths[i] = w_arr[i];
    for (int i = 0; i < count - 1; i++) {
        for (int j = i + 1; j < count; j++) {
            if (widths[i] > widths[j]) {
                int temp = widths[i];
                widths[i] = widths[j];
                widths[j] = temp;
            }
        }
    }
    return widths[count >> 1];
}


// 发送坐标到 上位机的专用协议函数
// 协议格式：[0xAA, 0x55, TL_X_H, TL_X_L, TL_Y_H, TL_Y_L, ... 共16字节数据]
void send_coordinates_to_matlab(int tl_x, int tl_y, int tr_x, int tr_y, int bl_x, int bl_y, int br_x, int br_y) {
    // 1. 发送帧头
    uart_send_date(UART0, 0xAA);
    uart_send_date(UART0, 0x55);

    // 2. 依次发送 8 个坐标值（每个值 16 位，先发高 8 位，再发低 8 位）
    int coords[8] = {tl_x, tl_y, tr_x, tr_y, bl_x, bl_y, br_x, br_y};
    
    for(int i = 0; i < 8; i++) {
        uart_send_date(UART0, (coords[i] >> 8) & 0xFF);
        uart_send_date(UART0, coords[i] & 0xFF);
        // 加入极小延时，防止软核发送过快导致硬件 FIFO 溢出
        for(volatile int nop=0; nop<50; nop++); 
    }
    
    printf("\r\n[串口] 已同步坐标数据至上位机。\r\n");
}

// 模板匹配打分核心
int process_and_match_mem(volatile uint32_t* bw_word, int target_w, int char_x, int char_y, int char_w, int char_h, int expected_pos) {
    if (char_h == 0) return 0;
    if (char_w < 4 || (char_w * 1000 < char_h * 150) || (char_w * 1000 > char_h * 1500)) return 0;

    volatile uint8_t* test_image = (volatile uint8_t*)MEM_TEST_IMAGE;

    for (int y = 0; y < TPL_H; y++) {
        for (int x = 0; x < TPL_W; x++) {
            int src_x = char_x + safe_div(x * char_w, TPL_W);
            int src_y = char_y + safe_div(y * char_h, TPL_H);
            
            if (y < 1 || y > TPL_H - 2) {
                test_image[y * TPL_W + x] = 0;
            } else {
                int base_idx = src_y * (target_w >> 2) + (src_x >> 2);
                int k = src_x & 3;
                uint32_t word = bw_word[base_idx];
                for(volatile int nop=0; nop<1; nop++); 
                uint8_t p = (word >> (k * 8)) & 0xFF;
                test_image[y * TPL_W + x] = (p > 128) ? 1 : 0;
            }
        }
    }

    long max_score = -10000;
    int best_id = -1;

    for (int i = 0; i < num_templates; i++) {
        int name_len = 0;
        while (template_lib[i].name[name_len] != '\0') name_len++;

        if (expected_pos == 1) {
            if (name_len <= 1) continue; 
        } else {
            if (name_len > 1) continue;  
        }

        long current_score = 0;
        for (int j = 0; j < TPL_W * TPL_H; j++) {
            for(volatile int nop=0; nop<2; nop++); 
            if (test_image[j] == template_lib[i].data[j]) {
                if (test_image[j] == 1) current_score += 10;
                else current_score += 1;
            } else {
                if (template_lib[i].data[j] == 1) current_score -= 5;
                else current_score -= 10;
            }
        }

        if (current_score > max_score) {
            max_score = current_score;
            best_id = i;
        }
    }
    
    if (max_score < 100) return 0; 
    
    // 识别成功，串口打印字符！
    printf(" [%s] ", template_lib[best_id].name);
    return 1;
}

// ==========================================
// 3.车牌识别全流水线
// ==========================================
void car_plate_recognize_pipeline() {
    set_led5_status(1); 
    set_led6_status(0);

    volatile uint16_t* bin_img = (volatile uint16_t*)DDR_BIN_FRAME0;
    volatile uint16_t* raw_img = (volatile uint16_t*)DDR_RAW_FRAME0;
    
    printf("\r\n\033[2J\033[H"); 
    printf("=========================================================\r\n");
    printf(">>> MRS 全自动车牌识别流水线启动 <<<\r\n");
    printf("=========================================================\r\n");

    // ==========================================================
    // 【阶段一】：纯粹投影定位 + 极值逼近角点
    // ==========================================================
    printf("\r\n[阶段 1/6] 执行 ROI 投影定位 (零内存安全版)...\r\n");

    // 1. Y轴投影找上下界
    int y_min = -1, y_max = -1, max_h = 0, cur_y_min = -1;
    for(int y = ROI_MARGIN_Y; y < IMG_H - ROI_MARGIN_Y; y++) {
        int row_count = 0; int row_offset = y * BIN_IMG_W;
        for(int x = ROI_MARGIN_X; x < BIN_IMG_W - ROI_MARGIN_X; x++) {
            if(bin_img[row_offset + x] > 0x8000) row_count++;
        }
        if(row_count > 15) { if(cur_y_min == -1) cur_y_min = y; } 
        else if(cur_y_min != -1) {
            int cur_h = y - cur_y_min;
            if(cur_h > max_h && cur_h > 20 && cur_h < 300) {
                max_h = cur_h; y_min = cur_y_min; y_max = y - 1;
            }
            cur_y_min = -1;
        }
    }
    if(y_min == -1) { printf(" >> [失败] 未检测到车牌高度\r\n"); set_led5_status(0); return; }

    // 2. X轴投影找左右界
    int x_min = -1, x_max = -1, max_w = 0, cur_x_min = -1, gap_count = 0;
    for(int x = ROI_MARGIN_X; x < BIN_IMG_W - ROI_MARGIN_X; x++) {
        int col_count = 0;
        for(int y = y_min; y <= y_max; y++) if(bin_img[y * BIN_IMG_W + x] > 0x8000) col_count++;
        
        if(col_count > 2) {
            if(cur_x_min == -1) cur_x_min = x; gap_count = 0; 
        } else if(cur_x_min != -1) {
            gap_count++;
            if(gap_count > 60) { 
                int cur_w = (x - 60) - cur_x_min; 
                if(cur_w > max_w && cur_w > 50 && cur_w < 800) {
                    max_w = cur_w; x_min = cur_x_min; x_max = x - 60;
                }
                cur_x_min = -1;
            }
        }
    }
    if(cur_x_min != -1) {
        int cur_w = (BIN_IMG_W - ROI_MARGIN_X - gap_count) - cur_x_min;
        if(cur_w > max_w && cur_w > 50 && cur_w < 800) { x_min = cur_x_min; x_max = BIN_IMG_W - ROI_MARGIN_X - gap_count; }
    }
    if(x_min == -1) { printf(" >> [失败] 未检测到车牌宽度\r\n"); set_led5_status(0); return; }

    // 3. OBB 极值逼近找四个倾斜角 (只在刚刚框出的 x_min~x_max, y_min~y_max 范围内)
    int min_sum = 9999999, max_sum = -9999999, min_diff = 9999999, max_diff = -9999999;
    int tl_x = x_min, tl_y = y_min, br_x = x_max, br_y = y_max;
    int tr_x = x_max, tr_y = y_min, bl_x = x_min, bl_y = y_max;

    for(int y = y_min; y <= y_max; y++) {
        int row_offset = y * BIN_IMG_W;
        for(int x = x_min; x <= x_max; x++) {
            if(bin_img[row_offset + x] > 0x8000) {
                int sum = x + y;
                int diff = x - y;
                if(sum < min_sum)   { min_sum = sum;   tl_x = x; tl_y = y; }
                if(sum > max_sum)   { max_sum = sum;   br_x = x; br_y = y; }
                if(diff > max_diff) { max_diff = diff; tr_x = x; tr_y = y; }
                if(diff < min_diff) { min_diff = diff; bl_x = x; bl_y = y; }
            }
        }
    }
    
    printf(" >> 定位成功！计算原图映射偏移 (+27像素)\r\n");
    int best_tl_x = tl_x + RAW_X_OFFSET, best_tl_y = tl_y;
    int best_tr_x = tr_x + RAW_X_OFFSET, best_tr_y = tr_y;
    int best_bl_x = bl_x + RAW_X_OFFSET, best_bl_y = bl_y;
    int best_br_x = br_x + RAW_X_OFFSET, best_br_y = br_y;

    // 将坐标同步给 上位机
    send_coordinates_to_matlab(best_tl_x, best_tl_y, best_tr_x, best_tr_y, 
                               best_bl_x, best_bl_y, best_br_x, best_br_y);

    printf("【真实车牌原图映射四角坐标】:\r\n");
    printf(" 左上角: (%4d , %4d)     右上角: (%4d , %4d)\r\n", best_tl_x, best_tl_y, best_tr_x, best_tr_y);
    printf(" 左下角: (%4d , %4d)     右下角: (%4d , %4d)\r\n\r\n", best_bl_x, best_bl_y, best_br_x, best_br_y);

    set_led5_status(1); set_led6_status(1);

    // ==========================================================
    // 【阶段 1.5】：平滑抠取 RAW 原始高彩图
    // ==========================================================
    printf("[阶段 2/6] 从 DDR 中拷贝真实原图 ROI...\r\n");
    volatile uint16_t* roi_buf = MEM_ROI_BUF;
    int best_x_left = get_min(best_tl_x, best_bl_x), best_x_right = get_max(best_tr_x, best_br_x);
    int best_y_top = get_min(best_tl_y, best_tr_y), best_y_bot = get_max(best_bl_y, best_br_y);

    int start_x = get_max(0, best_x_left - 5);
    int start_y = get_max(0, best_y_top - 5);
    int end_x = get_min(RAW_IMG_W - 1, best_x_right + 5);
    int end_y = get_min(IMG_H - 1, best_y_bot + 5);
    int src_roi_w = end_x - start_x + 1;
    int src_roi_h = end_y - start_y + 1;

    for (int y = 0; y < src_roi_h; y++) {
        int src_y = start_y + y;
        int raw_row_offset = src_y * RAW_IMG_W;
        for (int x = 0; x < src_roi_w; x++) {
            int src_x = start_x + x;
            roi_buf[y * src_roi_w + x] = raw_img[raw_row_offset + src_x];
            for(volatile int nop=0; nop<2; nop++); 
        }
    }

    // ==========================================================
    // 【阶段二】：执行原图畸变校正
    // ==========================================================
    printf("[阶段 3/6] 正在拉伸像素，执行 OBB 透视畸变校正...\r\n");
    volatile uint16_t* dst_img = MEM_DST_IMG;
    for (int y = 0; y < TARGET_H; y++) {
        int fy = safe_div(y * FIXED_SCALE, TARGET_H - 1), inv_fy = FIXED_SCALE - fy;
        for (int x = 0; x < TARGET_W; x++) {
            int fx = safe_div(x * FIXED_SCALE, TARGET_W - 1), inv_fx = FIXED_SCALE - fx;

            int src_x = (((inv_fx * inv_fy) >> FIXED_SHIFT) * best_tl_x + ((fx * inv_fy) >> FIXED_SHIFT) * best_tr_x +
                         ((fx * fy) >> FIXED_SHIFT) * best_br_x + ((inv_fx * fy) >> FIXED_SHIFT) * best_bl_x) >> FIXED_SHIFT;
            int src_y = (((inv_fx * inv_fy) >> FIXED_SHIFT) * best_tl_y + ((fx * inv_fy) >> FIXED_SHIFT) * best_tr_y +
                         ((fx * fy) >> FIXED_SHIFT) * best_br_y + ((inv_fx * fy) >> FIXED_SHIFT) * best_bl_y) >> FIXED_SHIFT;

            if (src_x >= start_x && src_x <= end_x && src_y >= start_y && src_y <= end_y) {
                dst_img[y * TARGET_W + x] = roi_buf[(src_y - start_y) * src_roi_w + (src_x - start_x)];
            } else {
                dst_img[y * TARGET_W + x] = 0;
            }
            for(volatile int nop=0; nop<2; nop++); 
        }
    }

    // ==========================================================
    // 【阶段三】：通道二值化 (黑底白字)
    // ==========================================================
    printf("[阶段 4/6] 提取蓝牌白字 (R通道二值化映射)...\r\n");
    volatile uint32_t* bw_word = MEM_BW_IMG;
    for (int y = 0; y < TARGET_H; y++) {
        for (int x = 0; x < TARGET_W; x += 4) {
            uint32_t out_bw = 0;
            for (int k = 0; k < 4; k++) {
                uint16_t px = dst_img[y * TARGET_W + x + k];
                int r = (px >> 11) & 0x1F; r = (r << 3) | (r >> 2);
                if (r > 120) out_bw |= (255 << (k * 8)); 
            }
            bw_word[(y * TARGET_W + x) >> 2] = out_bw;
            for(volatile int nop=0; nop<2; nop++); 
        }
    }

// ==========================================================
    // 【阶段四】：校正后字符的垂直投影分割 
    // ==========================================
    printf("[阶段 5/6] 正在执行字符切割 (垂直投影)...\r\n");
    
    volatile uint16_t* s_h_proj_s4 = (volatile uint16_t*)0xA1C00000;
    volatile uint16_t* s_v_proj_s4 = (volatile uint16_t*)0xA1C01000;
    
    // 初始化 DDR，加入刹车防堵死
    for (int i = 0; i < TARGET_H; i++) { s_h_proj_s4[i] = 0; for(volatile int nop=0; nop<2; nop++); }
    for (int i = 0; i < TARGET_W; i++) { s_v_proj_s4[i] = 0; for(volatile int nop=0; nop<2; nop++); }

    int max_h_val = 0; int words_per_line = TARGET_W >> 2; 

    // ----------------------------------------------------
    printf("   - [5.1] 正在进行水平投影降噪扫描...\r\n");
    // ----------------------------------------------------
    for (int y = 0; y < TARGET_H; y++) {
        int base_idx = y * words_per_line;
        int current_row_count = 0; 
        for (int w = 0; w < words_per_line; w++) {
            uint32_t word = bw_word[base_idx + w];
            for(volatile int nop=0; nop<4; nop++); // AXI 刹车
            if (word == 0) continue;
            for (int k = 0; k < 4; k++) {
                if ((word >> (k * 8)) & 0xFF) current_row_count++; 
            }
        }
        s_h_proj_s4[y] = current_row_count; 
        for(volatile int nop=0; nop<2; nop++); // 写 DDR 刹车
        if (current_row_count > max_h_val) max_h_val = current_row_count;
    }

    int h_thresh_s4 = (max_h_val * 153) >> 10; 
    int y_top = 0, y_bot = TARGET_H - 1, max_y_len = 0;
    int cur_start_s4 = -1; 
    
    for (int y = 0; y < TARGET_H; y++) {
        uint16_t h_val = s_h_proj_s4[y];
        for(volatile int nop=0; nop<2; nop++); // 读 DDR 刹车
        if (h_val > h_thresh_s4) { if (cur_start_s4 == -1) cur_start_s4 = y; }
        else if (cur_start_s4 != -1) {
            if (y - cur_start_s4 > max_y_len) { max_y_len = y - cur_start_s4; y_top = cur_start_s4; y_bot = y - 1; }
            cur_start_s4 = -1;
        }
    }
    int margin_y = ((y_bot - y_top) * 51) >> 10; 
    y_top = get_max(0, y_top - margin_y);
    y_bot = get_min(TARGET_H - 1, y_bot + margin_y);

    int max_v_val = 0;
    
    // ----------------------------------------------------
    printf("   - [5.2] 正在进行垂直投影字符切片...\r\n");
    // ----------------------------------------------------
    for (int w = 0; w < words_per_line; w++) {
        int col_count[4] = {0, 0, 0, 0}; 

        for (int y = y_top; y <= y_bot; y++) {
            uint32_t word = bw_word[y * words_per_line + w];
            for(volatile int nop=0; nop<4; nop++); // AXI 刹车

            if (word == 0) continue;
            if ((word >> 0)  & 0xFF) col_count[0]++;
            if ((word >> 8)  & 0xFF) col_count[1]++;
            if ((word >> 16) & 0xFF) col_count[2]++;
            if ((word >> 24) & 0xFF) col_count[3]++;
        }

        s_v_proj_s4[w * 4 + 0] = col_count[0];
        s_v_proj_s4[w * 4 + 1] = col_count[1];
        s_v_proj_s4[w * 4 + 2] = col_count[2];
        s_v_proj_s4[w * 4 + 3] = col_count[3];
        for(volatile int nop=0; nop<4; nop++); // 写 DDR 刹车

        if (col_count[0] > max_v_val) max_v_val = col_count[0];
        if (col_count[1] > max_v_val) max_v_val = col_count[1];
        if (col_count[2] > max_v_val) max_v_val = col_count[2];
        if (col_count[3] > max_v_val) max_v_val = col_count[3];
    }

    // ----------------------------------------------------
    printf("   - [5.3] 正在合并离散连通域 (绝对免疫栈溢出)...\r\n");
    // ----------------------------------------------------
    int v_thresh_s4 = (max_v_val * 102) >> 10; 
    int raw_count = 0, in_char = 0;
    
    // 将所有切割缓存区全部映射到 DDR 安全区
    volatile int* raw_x1    = (volatile int*)0xA1E00000;
    volatile int* raw_x2    = (volatile int*)0xA1E01000;
    volatile int* raw_w     = (volatile int*)0xA1E02000;
    volatile int* merged_x1 = (volatile int*)0xA1E03000;
    volatile int* merged_x2 = (volatile int*)0xA1E04000;
    volatile int* merged_w  = (volatile int*)0xA1E05000;
    volatile int* sort_buf  = (volatile int*)0xA1E06000; // 替代函数里的排序缓存

    for (int x = 0; x < TARGET_W; x++) {
        uint16_t cur_v_val = s_v_proj_s4[x]; // 单次读 DDR
        for(volatile int nop=0; nop<2; nop++);

        if (cur_v_val >= v_thresh_s4) {
            if (!in_char && raw_count < 50) { // 强行限制容量，杜绝越界
                raw_x1[raw_count] = x; 
                in_char = 1; 
            }
        } else if (in_char) {
            raw_x2[raw_count] = x - 1;
            raw_w[raw_count]  = x - raw_x1[raw_count];
            if (raw_w[raw_count] >= 4) raw_count++; 
            in_char = 0;
        }
    }
    if (in_char && raw_count < 50) {
        raw_x2[raw_count] = TARGET_W - 1; raw_w[raw_count] = TARGET_W - 1 - raw_x1[raw_count];
        if (raw_w[raw_count] >= 4) raw_count++;
    }

    // 直接在本地对 DDR 数据进行内联冒泡排序求中位数！彻底消灭栈消耗！
    int median_w = 0;
    if (raw_count > 0) {
        for(int i = 0; i < raw_count; i++) sort_buf[i] = raw_w[i];
        for(int i = 0; i < raw_count - 1; i++) {
            for(int j = i + 1; j < raw_count; j++) {
                if(sort_buf[i] > sort_buf[j]) {
                    int tmp = sort_buf[i];
                    sort_buf[i] = sort_buf[j];
                    sort_buf[j] = tmp;
                }
            }
        }
        median_w = sort_buf[raw_count >> 1];
    }

    int m_count = 0;
    if (raw_count > 0) {
        int curr_x1 = raw_x1[0], curr_x2 = raw_x2[0], curr_w = raw_w[0];
        for (int i = 1; i < raw_count; i++) {
            int nxt_x1 = raw_x1[i], nxt_x2 = raw_x2[i], nxt_w = raw_w[i];
            int gap = nxt_x1 - curr_x2, comb_w = nxt_x2 - curr_x1 + 1;
            if (((curr_w < ((median_w * 717) >> 10)) && (gap < ((median_w * 256) >> 10))) ||
                ((curr_x1 < (TARGET_W >> 2)) && (gap < ((median_w * 461) >> 10)) && (comb_w < ((median_w * 1434) >> 10)))) {
                curr_x2 = nxt_x2; curr_w = curr_x2 - curr_x1 + 1;
            } else {
                if (m_count < 50) {
                    merged_x1[m_count] = curr_x1; merged_x2[m_count] = curr_x2; merged_w[m_count] = curr_w;
                    m_count++; 
                }
                curr_x1 = nxt_x1; curr_x2 = nxt_x2; curr_w = nxt_w;
            }
        }
        if (m_count < 50) {
            merged_x1[m_count] = curr_x1; merged_x2[m_count] = curr_x2; merged_w[m_count] = curr_w;
            m_count++; 
        }
    }
    
    printf(" >> 切割完成！共切出候选字符模块数量: %d\r\n", m_count);

    // ==========================================================
    // 【阶段五】：最终字模匹配打分
    // ==========================================================
    printf("[阶段 6/6] 送入模板匹配识别！\r\n识别结果: ");
    int valid_char_count = 0;
    int match_roi_h = y_bot - y_top + 1;

    for (int i = 0; i < m_count; i++) {
        int x1 = merged_x1[i], cw = merged_w[i];
        int expected_pos = valid_char_count + 1;
        
        int status = process_and_match_mem(bw_word, TARGET_W, x1, y_top, cw, match_roi_h, expected_pos);
        if (status == 1) {
            valid_char_count++;
        }
    }
    printf("\r\n"); 
    
    set_led5_status(0);
    set_led6_status(0);

    // ==========================================================
    // LED 最终播报
    // ==========================================================
    if (valid_char_count > 0) {
        printf("\r\n识别出 %d 个有效字符，LED 闪烁播报中...\r\n", valid_char_count);
        for (int k = 0; k < 3; k++) {
            set_led6_status(1); for(volatile int j = 0; j < 800000; j++);
            set_led6_status(0); for(volatile int j = 0; j < 800000; j++);
        }
        for(volatile int j = 0; j < 3000000; j++); 
        for(int k = 0; k < valid_char_count; k++) {
            set_led6_status(1); for(volatile int j = 0; j < 1500000; j++);
            set_led6_status(0); for(volatile int j = 0; j < 1500000; j++);
        }
        for(volatile int j = 0; j < 10000000; j++); 
    } else {
        printf("\r\n[!] 模板匹配未达到阈值，判定为无效噪点框。\r\n");
    }
}

// ==========================================
// 4. 外设控制与 Main 框架
// ==========================================
void init_fpioa_custom() {
    fpioa_nio_mode_write(NIO_15, NIO_MODE_HIGHZ);
    fpioa_nio_mode_write(NIO_14 | NIO_16, NIO_MODE_OE_PP);
}

void set_led6_status(int on) {
    uint32_t dout = fpioa_nio_dout_read(); 
    if (on) dout |= NIO_14; else dout &= ~NIO_14;
    fpioa_nio_dout_write(dout); 
}

void set_led5_status(int on) {
    uint32_t dout = fpioa_nio_dout_read(); 
    if (on) dout |= NIO_16; else dout &= ~NIO_16; 
    fpioa_nio_dout_write(dout); 
}

int last_btn_state = 1;
volatile int current_plate_type = 1;

void check_button() {
    uint32_t din = fpioa_nio_din_read();
    int current_btn_state = (din & NIO_15) ? 1 : 0;
    if (last_btn_state == 1 && current_btn_state == 0) {
        for(volatile int i=0; i<10000; i++); 
        din = fpioa_nio_din_read();
        if ((din & NIO_15) == 0) {
            if (current_plate_type == 1) current_plate_type = 2;
            else current_plate_type = 1;
            
            int timeout = 0;
            while((fpioa_nio_din_read() & NIO_15) == 0) {
                if (timeout++ > 50000) break; 
            }
        }
    }
    last_btn_state = current_btn_state;
}

int main() {
    // 启动缓冲延时
    for(volatile int i = 0; i < 10000000; i++);
    init_uart0_printf(115200, 0);
    init_fpioa_custom();
    
    printf("\r\n===============================================\r\n");
    printf("   FPGA RISC-V 车牌识别系统初始化完成！\r\n");
    printf("===============================================\r\n");

    while(1) {
        check_button();
        car_plate_recognize_pipeline();
        
        // 降低循环扫描频率，防止 AXI 总线崩溃
        for(volatile uint32_t i = 0; i < 20000000; i++) {
            if ((i & 0x1FFFF) == 0) { check_button(); }
        }
    }
    return 0;
}