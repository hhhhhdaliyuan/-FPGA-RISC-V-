`timescale 1ns/1ps

module tb_image_process_steps;

    localparam integer MAX_PATH_LEN = 1024;
    localparam integer MAX_PIX = 1920 * 1080;
    localparam integer TARGET_FRAME_IDX = 2;

    reg clk;
    reg rst_n;

    reg in_vsync;
    reg in_hsync;
    reg in_de;
    reg [7:0] in_r;
    reg [7:0] in_g;
    reg [7:0] in_b;

    wire out_vsync;
    wire out_hsync;
    wire out_de;
    wire [7:0] out_bin;

    integer img_w_i;
    integer img_h_i;
    integer pix_total;

    integer x;
    integer y;
    integer f;
    integer idx;
    integer guard_cnt;
    integer fd;

    integer gray_valid_cnt;
    integer gauss_valid_cnt;
    integer hsv_valid_cnt;
    integer sobel_valid_cnt;
    integer otsu_valid_cnt;
    integer close_valid_cnt;

    integer gray_x;
    integer gray_y;
    integer gauss_x;
    integer gauss_y;
    integer hsv_x;
    integer hsv_y;
    integer sobel_x;
    integer sobel_y;
    integer otsu_x;
    integer otsu_y;
    integer close_x;
    integer close_y;

    reg gray_hs_d;
    reg gauss_hs_d;
    reg hsv_hs_d;
    reg sobel_hs_d;
    reg otsu_hs_d;
    reg close_hs_d;
    reg gray_vs_d;
    reg gauss_vs_d;
    reg hsv_vs_d;
    reg sobel_vs_d;
    reg otsu_vs_d;
    reg close_vs_d;

    integer gray_frame_idx;
    integer gauss_frame_idx;
    integer hsv_frame_idx;
    integer sobel_frame_idx;
    integer otsu_frame_idx;
    integer close_frame_idx;

    reg [8*MAX_PATH_LEN-1:0] in_mem_file;
    reg [8*MAX_PATH_LEN-1:0] out_gray_mem_file;
    reg [8*MAX_PATH_LEN-1:0] out_gaussian_mem_file;
    reg [8*MAX_PATH_LEN-1:0] out_hsv_mem_file;
    reg [8*MAX_PATH_LEN-1:0] out_sobel_mem_file;
    reg [8*MAX_PATH_LEN-1:0] out_otsu_mem_file;
    reg [8*MAX_PATH_LEN-1:0] out_close_mem_file;

    reg [15:0] in_mem [0:MAX_PIX-1];

    reg [7:0] gray_mem [0:MAX_PIX-1];
    reg [7:0] gauss_mem [0:MAX_PIX-1];
    reg [7:0] hsv_mem [0:MAX_PIX-1];
    reg [7:0] sobel_mem [0:MAX_PIX-1];
    reg [7:0] otsu_mem [0:MAX_PIX-1];
    reg [7:0] close_mem [0:MAX_PIX-1];

    image_process #(
        .IMG_WIDTH(1280),
        .IMG_HEIGHT(720)
    ) dut (
        .clk      (clk),
        .rst_n    (rst_n),
        .in_vsync (in_vsync),
        .in_hsync (in_hsync),
        .in_de    (in_de),
        .in_r     (in_r),
        .in_g     (in_g),
        .in_b     (in_b),
        .out_vsync(out_vsync),
        .out_hsync(out_hsync),
        .out_de   (out_de),
        .out_bin  (out_bin)
    );

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    always @(posedge clk) begin
        gray_hs_d  <= dut.gray_hsync;
        gauss_hs_d <= dut.gauss_hsync;
        hsv_hs_d   <= dut.color_hsync_d2;
        sobel_hs_d <= dut.sobel_hsync;
        otsu_hs_d  <= dut.otsu_hsync;
        close_hs_d <= dut.sobel_close_hsync;
        gray_vs_d  <= dut.gray_vsync;
        gauss_vs_d <= dut.gauss_vsync;
        hsv_vs_d   <= dut.color_vsync_d2;
        sobel_vs_d <= dut.sobel_vsync;
        otsu_vs_d  <= dut.otsu_vsync;
        close_vs_d <= dut.sobel_close_vsync;

        if (!rst_n) begin
            gray_x <= 0;
            gray_y <= 0;
            gauss_x <= 0;
            gauss_y <= 0;
            hsv_x <= 0;
            hsv_y <= 0;
            sobel_x <= 0;
            sobel_y <= 0;
            otsu_x <= 0;
            otsu_y <= 0;
            close_x <= 0;
            close_y <= 0;

            gray_hs_d <= 1'b0;
            gauss_hs_d <= 1'b0;
            hsv_hs_d <= 1'b0;
            sobel_hs_d <= 1'b0;
            otsu_hs_d <= 1'b0;
            close_hs_d <= 1'b0;
            gray_vs_d <= 1'b0;
            gauss_vs_d <= 1'b0;
            hsv_vs_d <= 1'b0;
            sobel_vs_d <= 1'b0;
            otsu_vs_d <= 1'b0;
            close_vs_d <= 1'b0;

            gray_frame_idx <= 0;
            gauss_frame_idx <= 0;
            hsv_frame_idx <= 0;
            sobel_frame_idx <= 0;
            otsu_frame_idx <= 0;
            close_frame_idx <= 0;
        end else begin
            if (dut.gray_vsync && !gray_vs_d) begin
                gray_frame_idx <= gray_frame_idx + 1;
                gray_x <= 0;
                gray_y <= 0;
            end
            if (dut.gray_hsync && !gray_hs_d) begin
                gray_x <= 0;
            end
            if (!dut.gray_hsync && gray_hs_d) begin
                gray_y <= gray_y + 1;
                gray_x <= 0;
            end
            if ((gray_frame_idx == TARGET_FRAME_IDX) && dut.gray_de && (gray_y < img_h_i) && (gray_x < img_w_i)) begin
                gray_mem[gray_y * img_w_i + gray_x] <= dut.gray_pix;
                gray_x <= gray_x + 1;
                gray_valid_cnt <= gray_valid_cnt + 1;
            end

            if (dut.gauss_vsync && !gauss_vs_d) begin
                gauss_frame_idx <= gauss_frame_idx + 1;
                gauss_x <= 0;
                gauss_y <= 0;
            end
            if (dut.gauss_hsync && !gauss_hs_d) begin
                gauss_x <= 0;
            end
            if (!dut.gauss_hsync && gauss_hs_d) begin
                gauss_y <= gauss_y + 1;
                gauss_x <= 0;
            end
            if ((gauss_frame_idx == TARGET_FRAME_IDX) && dut.gauss_de && (gauss_y < img_h_i) && (gauss_x < img_w_i)) begin
                gauss_mem[gauss_y * img_w_i + gauss_x] <= dut.gauss_pix;
                gauss_x <= gauss_x + 1;
                gauss_valid_cnt <= gauss_valid_cnt + 1;
            end

            if (dut.color_vsync_d2 && !hsv_vs_d) begin
                hsv_frame_idx <= hsv_frame_idx + 1;
                hsv_x <= 0;
                hsv_y <= 0;
            end
            if (dut.color_hsync_d2 && !hsv_hs_d) begin
                hsv_x <= 0;
            end
            if (!dut.color_hsync_d2 && hsv_hs_d) begin
                hsv_y <= hsv_y + 1;
                hsv_x <= 0;
            end
            if ((hsv_frame_idx == TARGET_FRAME_IDX) && dut.color_de_d2 && (hsv_y < img_h_i) && (hsv_x < img_w_i)) begin
                hsv_mem[hsv_y * img_w_i + hsv_x] <= dut.color_bin_d2 ? 8'hff : 8'h00;
                hsv_x <= hsv_x + 1;
                hsv_valid_cnt <= hsv_valid_cnt + 1;
            end

            if (dut.sobel_vsync && !sobel_vs_d) begin
                sobel_frame_idx <= sobel_frame_idx + 1;
                sobel_x <= 0;
                sobel_y <= 0;
            end
            if (dut.sobel_hsync && !sobel_hs_d) begin
                sobel_x <= 0;
            end
            if (!dut.sobel_hsync && sobel_hs_d) begin
                sobel_y <= sobel_y + 1;
                sobel_x <= 0;
            end
            if ((sobel_frame_idx == TARGET_FRAME_IDX) && dut.sobel_de && (sobel_y < img_h_i) && (sobel_x < img_w_i)) begin
                sobel_mem[sobel_y * img_w_i + sobel_x] <= dut.sobel_pix;
                sobel_x <= sobel_x + 1;
                sobel_valid_cnt <= sobel_valid_cnt + 1;
            end

            if (dut.otsu_vsync && !otsu_vs_d) begin
                otsu_frame_idx <= otsu_frame_idx + 1;
                otsu_x <= 0;
                otsu_y <= 0;
            end
            if (dut.otsu_hsync && !otsu_hs_d) begin
                otsu_x <= 0;
            end
            if (!dut.otsu_hsync && otsu_hs_d) begin
                otsu_y <= otsu_y + 1;
                otsu_x <= 0;
            end
            if ((otsu_frame_idx == TARGET_FRAME_IDX) && dut.otsu_de && (otsu_y < img_h_i) && (otsu_x < img_w_i)) begin
                otsu_mem[otsu_y * img_w_i + otsu_x] <= dut.otsu_bin ? 8'hff : 8'h00;
                otsu_x <= otsu_x + 1;
                otsu_valid_cnt <= otsu_valid_cnt + 1;
            end

            if (dut.sobel_close_vsync && !close_vs_d) begin
                close_frame_idx <= close_frame_idx + 1;
                close_x <= 0;
                close_y <= 0;
            end
            if (dut.sobel_close_hsync && !close_hs_d) begin
                close_x <= 0;
            end
            if (!dut.sobel_close_hsync && close_hs_d) begin
                close_y <= close_y + 1;
                close_x <= 0;
            end
            if ((close_frame_idx == TARGET_FRAME_IDX) && dut.sobel_close_de && (close_y < img_h_i) && (close_x < img_w_i)) begin
                close_mem[close_y * img_w_i + close_x] <= dut.sobel_close_bin ? 8'hff : 8'h00;
                close_x <= close_x + 1;
                close_valid_cnt <= close_valid_cnt + 1;
            end
        end
    end

    task dump_u8_mem;
        input [8*MAX_PATH_LEN-1:0] out_path;
        input integer stage_id;
        begin
            fd = $fopen(out_path, "w");
            if (fd == 0) begin
                $display("[tb_steps] ERROR: failed to open output file: %s", out_path);
                $finish;
            end

            for (idx = 0; idx < pix_total; idx = idx + 1) begin
                case (stage_id)
                    0: $fdisplay(fd, "%02x", gray_mem[idx]);
                    1: $fdisplay(fd, "%02x", gauss_mem[idx]);
                    2: $fdisplay(fd, "%02x", hsv_mem[idx]);
                    3: $fdisplay(fd, "%02x", sobel_mem[idx]);
                    4: $fdisplay(fd, "%02x", otsu_mem[idx]);
                    default: $fdisplay(fd, "%02x", close_mem[idx]);
                endcase
            end

            $fclose(fd);
        end
    endtask

    initial begin
        rst_n = 1'b0;
        in_vsync = 1'b0;
        in_hsync = 1'b0;
        in_de = 1'b0;
        in_r = 8'd0;
        in_g = 8'd0;
        in_b = 8'd0;

        gray_valid_cnt = 0;
        gauss_valid_cnt = 0;
        hsv_valid_cnt = 0;
        sobel_valid_cnt = 0;
        otsu_valid_cnt = 0;
        close_valid_cnt = 0;

        gray_x = 0;
        gray_y = 0;
        gauss_x = 0;
        gauss_y = 0;
        hsv_x = 0;
        hsv_y = 0;
        sobel_x = 0;
        sobel_y = 0;
        otsu_x = 0;
        otsu_y = 0;
        close_x = 0;
        close_y = 0;

        gray_hs_d = 1'b0;
        gauss_hs_d = 1'b0;
        hsv_hs_d = 1'b0;
        sobel_hs_d = 1'b0;
        otsu_hs_d = 1'b0;
        close_hs_d = 1'b0;
        gray_vs_d = 1'b0;
        gauss_vs_d = 1'b0;
        hsv_vs_d = 1'b0;
        sobel_vs_d = 1'b0;
        otsu_vs_d = 1'b0;
        close_vs_d = 1'b0;

        gray_frame_idx = 0;
        gauss_frame_idx = 0;
        hsv_frame_idx = 0;
        sobel_frame_idx = 0;
        otsu_frame_idx = 0;
        close_frame_idx = 0;

        if (!$value$plusargs("IMG_W=%d", img_w_i)) begin
            $display("[tb_steps] ERROR: missing +IMG_W");
            $finish;
        end
        if (!$value$plusargs("IMG_H=%d", img_h_i)) begin
            $display("[tb_steps] ERROR: missing +IMG_H");
            $finish;
        end
        if (!$value$plusargs("IN_MEM_FILE=%s", in_mem_file)) begin
            $display("[tb_steps] ERROR: missing +IN_MEM_FILE");
            $finish;
        end
        if (!$value$plusargs("OUT_GRAY_MEM_FILE=%s", out_gray_mem_file)) begin
            $display("[tb_steps] ERROR: missing +OUT_GRAY_MEM_FILE");
            $finish;
        end
        if (!$value$plusargs("OUT_GAUSSIAN_MEM_FILE=%s", out_gaussian_mem_file)) begin
            $display("[tb_steps] ERROR: missing +OUT_GAUSSIAN_MEM_FILE");
            $finish;
        end
        if (!$value$plusargs("OUT_HSV_MEM_FILE=%s", out_hsv_mem_file)) begin
            $display("[tb_steps] ERROR: missing +OUT_HSV_MEM_FILE");
            $finish;
        end
        if (!$value$plusargs("OUT_SOBEL_MEM_FILE=%s", out_sobel_mem_file)) begin
            $display("[tb_steps] ERROR: missing +OUT_SOBEL_MEM_FILE");
            $finish;
        end
        if (!$value$plusargs("OUT_OTSU_MEM_FILE=%s", out_otsu_mem_file)) begin
            $display("[tb_steps] ERROR: missing +OUT_OTSU_MEM_FILE");
            $finish;
        end
        if (!$value$plusargs("OUT_CLOSE_MEM_FILE=%s", out_close_mem_file)) begin
            $display("[tb_steps] ERROR: missing +OUT_CLOSE_MEM_FILE");
            $finish;
        end

        pix_total = img_w_i * img_h_i;
        if (pix_total > MAX_PIX) begin
            $display("[tb_steps] ERROR: pix_total exceeds MAX_PIX");
            $finish;
        end

        for (idx = 0; idx < pix_total; idx = idx + 1) begin
            gray_mem[idx] = 8'd0;
            gauss_mem[idx] = 8'd0;
            hsv_mem[idx] = 8'd0;
            sobel_mem[idx] = 8'd0;
            otsu_mem[idx] = 8'd0;
            close_mem[idx] = 8'd0;
        end

        $display("[tb_steps] W/H: %0d x %0d", img_w_i, img_h_i);
        $display("[tb_steps] IN : %s", in_mem_file);

        $readmemh(in_mem_file, in_mem, 0, pix_total - 1);

        repeat (20) @(posedge clk);
        rst_n <= 1'b1;
        repeat (8) @(posedge clk);

        for (f = 0; f < 2; f = f + 1) begin
            idx = 0;
            in_vsync <= 1'b1;
            @(posedge clk);
            in_vsync <= 1'b0;

            for (y = 0; y < img_h_i; y = y + 1) begin
                in_hsync <= 1'b1;
                for (x = 0; x < img_w_i; x = x + 1) begin
                    in_de <= 1'b1;
                    in_r <= {in_mem[idx][15:11], 3'b000};
                    in_g <= {in_mem[idx][10:5], 2'b00};
                    in_b <= {in_mem[idx][4:0], 3'b000};
                    idx = idx + 1;
                    @(posedge clk);
                end

                in_de <= 1'b0;
                in_r <= 8'd0;
                in_g <= 8'd0;
                in_b <= 8'd0;
                repeat (8) @(posedge clk);
                in_hsync <= 1'b0;
                @(posedge clk);
            end

            in_de <= 1'b0;
            in_hsync <= 1'b0;
            in_r <= 8'd0;
            in_g <= 8'd0;
            in_b <= 8'd0;
            repeat (64) @(posedge clk);
        end

        in_de <= 1'b0;
        in_hsync <= 1'b0;
        in_r <= 8'd0;
        in_g <= 8'd0;
        in_b <= 8'd0;

        guard_cnt = 0;
        while (guard_cnt < (pix_total + 60000)) begin
            guard_cnt = guard_cnt + 1;
            @(posedge clk);
        end

        dump_u8_mem(out_gray_mem_file, 0);
        dump_u8_mem(out_gaussian_mem_file, 1);
        dump_u8_mem(out_hsv_mem_file, 2);
        dump_u8_mem(out_sobel_mem_file, 3);
        dump_u8_mem(out_otsu_mem_file, 4);
        dump_u8_mem(out_close_mem_file, 5);

        $display("[tb_steps] DONE. valid gray=%0d gauss=%0d hsv=%0d sobel=%0d otsu=%0d close=%0d", gray_valid_cnt, gauss_valid_cnt, hsv_valid_cnt, sobel_valid_cnt, otsu_valid_cnt, close_valid_cnt);
        repeat (10) @(posedge clk);
        $finish;
    end

endmodule
