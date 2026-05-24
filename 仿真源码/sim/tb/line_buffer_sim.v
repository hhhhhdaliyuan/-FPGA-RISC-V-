module line_buffer (
    input  wire [7:0]  wr_data,
    input  wire [10:0] wr_addr,
    input  wire        wr_en,
    input  wire        wr_clk,
    input  wire        wr_clk_en,
    input  wire        wr_rst,
    output reg  [7:0]  rd_data,
    input  wire [10:0] rd_addr,
    input  wire        rd_clk,
    input  wire        rd_clk_en,
    input  wire        rd_rst
);

reg [7:0] mem [0:2047];
integer i;

always @(posedge wr_clk or posedge wr_rst) begin
    if (wr_rst) begin
        for (i = 0; i < 2048; i = i + 1) begin
            mem[i] <= 8'd0;
        end
    end else if (wr_clk_en && wr_en) begin
        mem[wr_addr] <= wr_data;
    end
end

always @(posedge rd_clk or posedge rd_rst) begin
    if (rd_rst) begin
        rd_data <= 8'd0;
    end else if (rd_clk_en) begin
        rd_data <= mem[rd_addr];
    end
end

endmodule
